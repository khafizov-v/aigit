import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.config import settings
from .core.github_collector import GitHubCollector
from .core.claude_client import ClaudeClient
from .core.post_generator import PostGenerator
from .models.post import PostGenerationRequest, PostGenerationResponse, PostTemplate
from .models.commit import CommitCollection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered GitHub repository changes explainer",
    version="1.0.0",
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists(settings.static_files_dir):
    app.mount("/static", StaticFiles(directory=settings.static_files_dir), name="static")

# Initialize core components
github_collector = GitHubCollector()
claude_client = ClaudeClient()
post_generator = PostGenerator()

# Request/Response models
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: dict

class GeneratePostsRequest(BaseModel):
    repositories: Optional[List[str]] = None
    time_periods: List[str] = ["2h", "24h"]
    force_template: Optional[PostTemplate] = None
    target_audience: str = "general"

class CommitCollectionResponse(BaseModel):
    repository: str
    time_period: str
    commits_count: int
    start_time: datetime
    end_time: datetime
    file_path: Optional[str] = None

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    
    # Test connections
    try:
        # Test GitHub API
        rate_limit = github_collector.check_rate_limit()
        logger.info(f"GitHub API rate limit: {rate_limit}")
        
        # Test Claude API
        claude_connected = claude_client.test_connection()
        logger.info(f"Claude API connected: {claude_connected}")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health of the application and its dependencies"""
    
    services = {}
    
    # Check GitHub API
    try:
        rate_limit = github_collector.check_rate_limit()
        services["github"] = {
            "status": "healthy",
            "rate_limit_remaining": rate_limit.get("core", {}).get("remaining", 0)
        }
    except Exception as e:
        services["github"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Claude API
    try:
        claude_connected = claude_client.test_connection()
        services["claude"] = {"status": "healthy" if claude_connected else "unhealthy"}
    except Exception as e:
        services["claude"] = {"status": "unhealthy", "error": str(e)}
    
    return HealthResponse(
        status="healthy" if all(s.get("status") == "healthy" for s in services.values()) else "degraded",
        timestamp=datetime.now(),
        version="1.0.0",
        services=services
    )

# Collect commits endpoints
@app.post("/collect-commits/{repository}", response_model=CommitCollectionResponse)
async def collect_commits(
    repository: str,
    hours: int = 2,
    save_to_file: bool = True,
    background_tasks: BackgroundTasks = None
):
    """Collect commits from a repository for the specified time period"""
    
    try:
        logger.info(f"Collecting commits from {repository} for last {hours} hours")
        
        # Collect commits
        commits = github_collector.get_commits_for_period(repository, hours)
        
        response = CommitCollectionResponse(
            repository=repository,
            time_period=f"{hours}h",
            commits_count=len(commits.commits),
            start_time=commits.start_time,
            end_time=commits.end_time
        )
        
        # Save to file if requested
        if save_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{repository.replace('/', '_')}_{hours}h_{timestamp}.json"
            filepath = os.path.join(settings.commit_data_dir, "hourly", filename)
            
            if background_tasks:
                background_tasks.add_task(github_collector.save_commits_to_file, commits, filepath)
            else:
                github_collector.save_commits_to_file(commits, filepath)
            
            response.file_path = filepath
        
        return response
        
    except Exception as e:
        logger.error(f"Error collecting commits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collect-all-repos")
async def collect_all_repos(
    hours: int = 2,
    background_tasks: BackgroundTasks = None
):
    """Collect commits from all configured repositories"""
    
    if not settings.github_repos:
        raise HTTPException(status_code=400, detail="No repositories configured")
    
    results = []
    
    for repo in settings.github_repos:
        try:
            if background_tasks:
                background_tasks.add_task(collect_commits, repo, hours, True)
                results.append({"repository": repo, "status": "queued"})
            else:
                result = await collect_commits(repo, hours, True)
                results.append({"repository": repo, "status": "completed", "commits": result.commits_count})
        except Exception as e:
            logger.error(f"Error collecting from {repo}: {e}")
            results.append({"repository": repo, "status": "error", "error": str(e)})
    
    return {"results": results}

# Generate posts endpoints
@app.post("/generate-post", response_model=PostGenerationResponse)
async def generate_post(request: PostGenerationRequest):
    """Generate a post for a specific repository and time period"""
    
    try:
        logger.info(f"Generating post for {request.repository} ({request.time_period})")
        
        # Parse time period
        if request.time_period.endswith('h'):
            hours = int(request.time_period[:-1])
        else:
            raise HTTPException(status_code=400, detail="Invalid time period format. Use format like '2h' or '24h'")
        
        # Collect commits
        commits = github_collector.get_commits_for_period(request.repository, hours)
        
        if not commits.commits:
            raise HTTPException(status_code=404, detail=f"No commits found for {request.repository} in the last {hours} hours")
        
        # Generate post
        response = post_generator.generate_post(request, commits)
        
        if not response.success:
            raise HTTPException(status_code=500, detail=response.error_message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-posts-batch")
async def generate_posts_batch(
    request: GeneratePostsRequest,
    background_tasks: BackgroundTasks
):
    """Generate posts for multiple repositories and time periods"""
    
    repositories = request.repositories or settings.github_repos
    
    if not repositories:
        raise HTTPException(status_code=400, detail="No repositories specified")
    
    tasks = []
    
    for repo in repositories:
        for time_period in request.time_periods:
            post_request = PostGenerationRequest(
                repository=repo,
                time_period=time_period,
                force_template=request.force_template,
                target_audience=request.target_audience
            )
            
            # Add to background tasks
            background_tasks.add_task(
                generate_post_background, 
                post_request
            )
            
            tasks.append({
                "repository": repo,
                "time_period": time_period,
                "status": "queued"
            })
    
    return {"tasks": tasks, "message": f"Queued {len(tasks)} post generation tasks"}

async def generate_post_background(request: PostGenerationRequest):
    """Background task for generating posts"""
    try:
        result = await generate_post(request)
        logger.info(f"Background post generation completed for {request.repository}")
        return result
    except Exception as e:
        logger.error(f"Background post generation failed for {request.repository}: {e}")

# File serving endpoints
@app.get("/posts/{time_period}/{filename}")
async def get_post_file(time_period: str, filename: str):
    """Serve generated post HTML files"""
    
    file_path = os.path.join(settings.output_dir, time_period, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Post file not found")
    
    return FileResponse(file_path, media_type="text/html")

@app.get("/posts/{time_period}")
async def list_posts(time_period: str):
    """List all posts for a time period"""
    
    posts_dir = os.path.join(settings.output_dir, time_period)
    
    if not os.path.exists(posts_dir):
        return {"posts": []}
    
    posts = []
    for filename in os.listdir(posts_dir):
        if filename.endswith('.html'):
            file_path = os.path.join(posts_dir, filename)
            stat = os.stat(file_path)
            
            posts.append({
                "filename": filename,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "size": stat.st_size,
                "url": f"/posts/{time_period}/{filename}"
            })
    
    # Sort by creation time, newest first
    posts.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"posts": posts}

@app.get("/commits/{filename}")
async def get_commit_file(filename: str):
    """Serve commit data files"""
    
    # Check both hourly and processed directories
    for subdir in ["hourly", "processed"]:
        file_path = os.path.join(settings.commit_data_dir, subdir, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="application/json")
    
    raise HTTPException(status_code=404, detail="Commit file not found")

# Analytics endpoints
@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get summary analytics for all repositories"""
    
    summary = {
        "repositories": len(settings.github_repos),
        "total_posts_generated": 0,
        "posts_by_period": {},
        "recent_activity": []
    }
    
    # Count posts by time period
    for time_period in ["2h", "24h"]:
        posts_dir = os.path.join(settings.output_dir, time_period)
        if os.path.exists(posts_dir):
            post_count = len([f for f in os.listdir(posts_dir) if f.endswith('.html')])
            summary["posts_by_period"][time_period] = post_count
            summary["total_posts_generated"] += post_count
    
    return summary

@app.get("/analytics/repository/{repository}")
async def get_repository_analytics(repository: str):
    """Get analytics for a specific repository"""
    
    # This would be enhanced with actual analytics data
    return {
        "repository": repository,
        "posts_generated": 0,  # Would query actual data
        "avg_commits_per_day": 0,
        "most_active_contributors": [],
        "commit_types_distribution": {}
    }

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation"""
    return """
    <html>
        <head>
            <title>AI GitHub Explainer</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .method { font-weight: bold; color: #0066cc; }
            </style>
        </head>
        <body>
            <h1>AI GitHub Explainer API</h1>
            <p>Transform GitHub commits into engaging social media posts!</p>
            
            <h2>Available Endpoints:</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> /health - Health check
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /collect-commits/{repository} - Collect commits
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /generate-post - Generate a post
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /posts/{time_period} - List posts
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /posts/{time_period}/{filename} - View post
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /docs - Interactive API documentation
            </div>
            
            <p><a href="/docs">View Interactive API Documentation</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )