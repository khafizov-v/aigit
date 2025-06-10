import json
import os
import glob
from pathlib import Path
import anthropic
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitHubPostsGenerator:
    def __init__(self):
        self.api_key = os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
        self.issues_file = os.getenv('ISSUES_FILE_PATH', 'issues/github_cases.json')
        self.commits_folder = os.getenv('COMMITS_FOLDER_PATH', 'commits')
        self.output_folder = os.getenv('OUTPUT_FOLDER_PATH', 'generated_posts')
        
    def load_github_issues(self) -> Dict[str, Any]:
        try:
            with open(self.issues_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Error loading issues: {e}")
            return {}
    
    def load_commit_files(self) -> List[Dict[str, str]]:
        commits_data = []
        md_files = glob.glob(os.path.join(self.commits_folder, '*.md'))
        
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    commits_data.append({
                        'filename': os.path.basename(file_path),
                        'content': content
                    })
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        return commits_data
    
    def get_html_template(self) -> str:
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QF Network Social Posts</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f2f5;
            color: #1c1e21;
        }

        .post {
            background: white;
            max-width: 520px;
            margin: 30px auto;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.2);
            overflow: hidden;
            border: 1px solid #dadde1;
        }

        .post-header {
            padding: 12px 16px;
            border-bottom: 1px solid #dadde1;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .profile-pic {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }

        .post-info {
            flex: 1;
        }

        .username {
            font-weight: 600;
            font-size: 15px;
        }

        .timestamp {
            color: #65676b;
            font-size: 13px;
        }

        .platform-badge {
            background: #e4e6ea;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            color: #65676b;
        }

        .post-content {
            padding: 16px;
        }

        .post-text {
            line-height: 1.34;
            margin-bottom: 12px;
        }

        .post-image-container {
            margin: 12px 0;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .post-image-container:hover {
            transform: scale(1.02);
        }

        .code-diff {
            background: #0d1117;
            color: #e6edf3;
            border-radius: 8px;
            padding: 16px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            line-height: 1.4;
            position: relative;
            overflow-x: auto;
        }

        .diff-header {
            color: #7d8590;
            margin-bottom: 8px;
            font-size: 11px;
        }

        .diff-removed {
            background: #490202;
            color: #f85149;
            display: block;
            padding: 2px 4px;
            margin: 1px 0;
        }

        .diff-added {
            background: #0f5132;
            color: #56d364;
            display: block;
            padding: 2px 4px;
            margin: 1px 0;
        }

        .file-tree {
            background: #f6f8fa;
            border: 1px solid #d1d9e0;
            border-radius: 8px;
            padding: 16px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 13px;
            line-height: 1.6;
        }

        .folder {
            color: #0969da;
            font-weight: 600;
        }

        .file {
            color: #656d76;
            margin-left: 16px;
        }

        .file.modified {
            color: #bf8700;
        }

        .file.added {
            color: #1a7f37;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin: 12px 0;
        }

        .stat-box {
            background: #f0f2f5;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-number {
            font-size: 20px;
            font-weight: bold;
            color: #1877f2;
            margin: 0;
        }

        .stat-label {
            font-size: 11px;
            color: #65676b;
            margin: 4px 0 0 0;
        }

        .commit-visual {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            position: relative;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .commit-hash {
            font-family: monospace;
            background: rgba(255,255,255,0.2);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-bottom: 8px;
            display: inline-block;
        }

        .commit-title {
            font-size: 18px;
            font-weight: bold;
            margin: 8px 0;
        }

        .interactive-buttons {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #1877f2;
            color: white;
        }

        .btn-secondary {
            background: #e4e6ea;
            color: #1c1e21;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .engagement-bar {
            display: flex;
            justify-content: space-between;
            padding: 8px 16px;
            border-top: 1px solid #dadde1;
            background: #f7f8fa;
        }

        .engagement-btn {
            background: none;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            color: #65676b;
            transition: background 0.2s;
        }

        .engagement-btn:hover {
            background: #e4e6ea;
        }

        .hashtag {
            color: #1877f2;
            font-weight: 500;
        }

        .architecture-diagram {
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 12px 0;
        }

        .component {
            display: inline-block;
            background: white;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 4px;
            font-weight: 600;
            color: #007bff;
            min-width: 100px;
        }

        .arrow {
            font-size: 24px;
            color: #007bff;
            margin: 0 8px;
        }

        .progress-visual {
            background: linear-gradient(90deg, #e9ecef 0%, #e9ecef 60%, #28a745 60%, #28a745 100%);
            height: 8px;
            border-radius: 4px;
            margin: 8px 0;
            position: relative;
        }

        .progress-text {
            position: absolute;
            top: -20px;
            right: 0;
            font-size: 12px;
            font-weight: bold;
            color: #28a745;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .post {
            animation: slideIn 0.5s ease-out;
        }

        .clickable {
            cursor: pointer;
            transition: all 0.2s;
        }

        .clickable:hover {
            background: #f0f2f5;
        }
    </style>
</head>
<body>

{POSTS_CONTENT}

    <script>
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', function() {
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 100);
            });
        });

        document.querySelectorAll('.post-image-container').forEach(container => {
            container.addEventListener('click', function() {
                this.style.transform = 'scale(1.05)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 200);
            });
        });
    </script>
</body>
</html>'''
    
    def generate_post_with_claude(self, data: str) -> str:
        prompt = f"""
Create 3-4 posts in this exact HTML format. Just return the post divs, I will insert them into the template.

Each post must follow this EXACT structure:

<div class="post">
    <div class="post-header">
        <div class="profile-pic">QF</div>
        <div class="post-info">
            <div class="username">Quantum Fusion</div>
            <div class="timestamp">2 hours ago</div>
        </div>
        <div class="platform-badge">Twitter/X</div>
    </div>
    
    <div class="post-content">
        <div class="post-text">
            🎉 <strong>MAJOR: Your title here!</strong><br><br>
            Description with emojis and <code>commit hash</code>
        </div>
        
        <div class="post-image-container">
            <div class="commit-visual" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="commit-hash">commit_hash</div>
                <div class="commit-title">Commit title</div>
                <div style="font-size: 14px; opacity: 0.9;">
                    📁 X files changed • +XX -XX lines
                </div>
            </div>
        </div>

        <div class="code-diff">
            <div class="diff-header">file_path</div>
            <span class="diff-added">+ added line</span>
            <span class="diff-removed">- removed line</span>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">+5</div>
                <p class="stat-label">Features</p>
            </div>
            <div class="stat-box">
                <div class="stat-number">100%</div>
                <p class="stat-label">Working</p>
            </div>
            <div class="stat-box">
                <div class="stat-number">0</div>
                <p class="stat-label">Bugs</p>
            </div>
        </div>

        <div class="interactive-buttons">
            <button class="btn btn-primary">View Commit</button>
            <button class="btn btn-secondary">Case Status</button>
        </div>

        <div style="margin-top: 12px;">
            <span class="hashtag">#Tag1</span> <span class="hashtag">#Tag2</span>
        </div>
    </div>
    
    <div class="engagement-bar">
        <button class="engagement-btn">👍 Like</button>
        <button class="engagement-btn">💬 Comment</button>
        <button class="engagement-btn">🔄 Share</button>
    </div>
</div>

Use the GitHub data below to create engaging posts. Explain technical changes simply. Use real commit hashes and file names from the data.

Data:
{data}

Return ONLY the post divs, no other text.
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            posts_content = response.content[0].text
            html_template = self.get_html_template()
            return html_template.replace('{POSTS_CONTENT}', posts_content)
        except Exception as e:
            logger.error(f"Error generating post with Claude: {e}")
            return f"Error generating post: {e}"
    
    def save_generated_post(self, content: str, filename: str = None) -> str:
        os.makedirs(self.output_folder, exist_ok=True)
        
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_post_{timestamp}.html"
        
        if not filename.endswith('.html'):
            filename += '.html'
        
        file_path = os.path.join(self.output_folder, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Post saved to: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving post to {file_path}: {e}")
            return ""
    
    def generate_posts(self) -> List[str]:
        logger.info("Starting post generation process...")
        
        issues_data = self.load_github_issues()
        commits_data = self.load_commit_files()
        
        if not issues_data and not commits_data:
            logger.warning("No data loaded, cannot generate posts")
            return []
        
        formatted_data = f"Issues: {json.dumps(issues_data, indent=2)}\n\nCommits: {json.dumps(commits_data, indent=2)}"
        generated_content = self.generate_post_with_claude(formatted_data)
        saved_file = self.save_generated_post(generated_content)
        
        if saved_file:
            logger.info("Post generation completed successfully")
            return [saved_file]
        else:
            logger.error("Failed to save generated post")
            return []

def main():
    try:
        generator = GitHubPostsGenerator()
        generated_files = generator.generate_posts()
        
        if generated_files:
            print("Generated posts:")
            for file_path in generated_files:
                print(f"  - {file_path}")
        else:
            print("No posts were generated")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()