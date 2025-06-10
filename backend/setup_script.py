#!/usr/bin/env python3
"""
Setup script for AI GitHub Explainer project.
This script organizes downloaded artifacts into the correct folder structure
and validates that everything is ready to run.
"""

import os
import shutil
import sys
from pathlib import Path

# Mapping of artifact names to their correct file paths
FILE_MAPPING = {
    # Root files
    "requirements": "requirements.txt",
    "env_example": ".env.example", 
    "readme": "README.md",
    "scheduler": "scheduler.py",
    "run_app": "run.py",
    
    # App core files
    "simple_config": "app/core/config.py",
    "github_collector": "app/core/github_collector.py", 
    "claude_client": "app/core/claude_client.py",
    "post_generator": "app/core/post_generator.py",
    
    # Models
    "models_commit": "app/models/commit.py",
    "models_post": "app/models/post.py",
    
    # Utils
    "template_selector": "app/utils/template_selector.py",
    "html_generator": "app/utils/html_generator.py",
    "chart_generator": "app/utils/chart_generator.py", 
    "data_processor": "app/utils/data_processor.py",
    
    # Templates
    "template_feature": "app/templates/template_feature.html",
    "template_bugfix": "app/templates/template_bugfix.html",
    "template_security": "app/templates/template_security.html", 
    "template_performance": "app/templates/template_performance.html",
    "template_general": "app/templates/template_general.html",
    
    # Prompts
    "single_prompt": "app/prompts/main_prompt.txt",
    
    # Main app
    "simple_main": "app/main.py",
}

# Required directory structure
REQUIRED_DIRS = [
    "app",
    "app/core", 
    "app/models",
    "app/utils",
    "app/templates", 
    "app/prompts",
    "data",
    "data/commits",
    "data/commits/hourly",
    "data/commits/processed", 
    "data/posts",
    "data/posts/2h",
    "data/posts/24h",
    "logs",
    "static"
]

# __init__.py file contents
INIT_FILES = {
    "app/__init__.py": '''"""
AI GitHub Explainer - Transform GitHub commits into engaging social media posts
"""

__version__ = "1.0.0"
__author__ = "AI GitHub Explainer Team"
''',
    
    "app/core/__init__.py": '''"""
Core business logic and external service integrations
"""

from .config import settings
from .github_collector import GitHubCollector
from .claude_client import ClaudeClient
from .post_generator import PostGenerator

__all__ = [
    "settings",
    "GitHubCollector", 
    "ClaudeClient",
    "PostGenerator"
]
''',
    
    "app/models/__init__.py": '''"""
Data models and schemas
"""

from .commit import (
    Commit,
    CommitCollection,
    CommitType,
    CommitAuthor,
    FileChange
)
from .post import (
    Post,
    PostContent,
    PostMetrics,
    PostGenerationRequest,
    PostGenerationResponse,
    PostType,
    PostTemplate,
    ChartData
)

__all__ = [
    # Commit models
    "Commit",
    "CommitCollection", 
    "CommitType",
    "CommitAuthor",
    "FileChange",
    # Post models
    "Post",
    "PostContent",
    "PostMetrics", 
    "PostGenerationRequest",
    "PostGenerationResponse",
    "PostType",
    "PostTemplate",
    "ChartData"
]
''',
    
    "app/utils/__init__.py": '''"""
Utility functions and helpers
"""

from .template_selector import TemplateSelector
from .html_generator import HTMLGenerator
from .chart_generator import ChartGenerator
from .data_processor import DataProcessor

__all__ = [
    "TemplateSelector",
    "HTMLGenerator",
    "ChartGenerator", 
    "DataProcessor"
]
'''
}

def create_directories():
    """Create all required directories"""
    print("📁 Creating directory structure...")
    
    for directory in REQUIRED_DIRS:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ {directory}")
    
    print(f"✅ Created {len(REQUIRED_DIRS)} directories")

def create_init_files():
    """Create __init__.py files"""
    print("\n📝 Creating __init__.py files...")
    
    for file_path, content in INIT_FILES.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip() + '\n')
        print(f"   ✅ {file_path}")
    
    print(f"✅ Created {len(INIT_FILES)} __init__.py files")

def move_artifacts():
    """Move and rename artifact files to correct locations"""
    print("\n🔄 Moving and renaming artifacts...")
    
    moved_files = 0
    missing_files = []
    
    for artifact_name, target_path in FILE_MAPPING.items():
        # Look for the artifact file (it might have different extensions)
        possible_files = [
            f"{artifact_name}.txt",
            f"{artifact_name}.py", 
            f"{artifact_name}.html",
            f"{artifact_name}.md",
            artifact_name
        ]
        
        source_file = None
        for possible_file in possible_files:
            if os.path.exists(possible_file):
                source_file = possible_file
                break
        
        if source_file:
            # Create target directory if it doesn't exist
            target_dir = os.path.dirname(target_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            
            # Move and rename the file
            shutil.move(source_file, target_path)
            print(f"   ✅ {source_file} → {target_path}")
            moved_files += 1
        else:
            missing_files.append(artifact_name)
            print(f"   ❌ Missing: {artifact_name}")
    
    if missing_files:
        print(f"\n⚠️  Warning: {len(missing_files)} files not found:")
        for missing in missing_files:
            print(f"   - {missing}")
        print("   Make sure you downloaded all artifacts from Claude")
    
    print(f"\n✅ Moved {moved_files} files successfully")
    return len(missing_files) == 0

def validate_structure():
    """Validate that all required files exist"""
    print("\n🔍 Validating project structure...")
    
    required_files = [
        "requirements.txt",
        ".env.example",
        "README.md", 
        "scheduler.py",
        "run.py",
        "app/main.py",
        "app/__init__.py",
        "app/core/__init__.py",
        "app/core/config.py",
        "app/core/github_collector.py",
        "app/core/claude_client.py", 
        "app/core/post_generator.py",
        "app/models/__init__.py",
        "app/models/commit.py",
        "app/models/post.py",
        "app/utils/__init__.py", 
        "app/utils/template_selector.py",
        "app/utils/html_generator.py",
        "app/utils/chart_generator.py",
        "app/utils/data_processor.py",
        "app/templates/template_feature.html",
        "app/templates/template_bugfix.html", 
        "app/templates/template_security.html",
        "app/templates/template_performance.html",
        "app/templates/template_general.html",
        "app/prompts/main_prompt.txt"
    ]
    
    missing_files = []
    existing_files = 0
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
            existing_files += 1
        else:
            print(f"   ❌ {file_path}")
            missing_files.append(file_path)
    
    print(f"\n📊 Validation Results:")
    print(f"   ✅ Found: {existing_files}/{len(required_files)} files")
    print(f"   ❌ Missing: {len(missing_files)} files")
    
    if missing_files:
        print(f"\n❌ Missing required files:")
        for missing in missing_files:
            print(f"   - {missing}")
        return False
    
    return True

def check_dependencies():
    """Check if Python and pip are available"""
    print("\n🐍 Checking Python environment...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"   ❌ Python {python_version.major}.{python_version.minor}.{python_version.micro} (requires 3.8+)")
        return False
    
    # Check if pip is available
    try:
        import pip
        print("   ✅ pip is available")
    except ImportError:
        print("   ❌ pip is not available")
        return False
    
    return True

def generate_next_steps():
    """Generate next steps instructions"""
    print("\n" + "="*60)
    print("🎉 PROJECT SETUP COMPLETE!")
    print("="*60)
    print("""
🚀 NEXT STEPS:

1. Configure your environment:
   cp .env.example .env
   # Edit .env and add your API keys:
   # GITHUB_TOKEN=your_github_token_here
   # ANTHROPIC_API_KEY=your_claude_api_key_here
   # GITHUB_REPOS=owner/repo1,owner/repo2

2. Install dependencies:
   pip install -r requirements.txt

3. Run the application:
   python run.py

4. Test it works:
   curl http://localhost:8000/health

5. Generate your first post:
   curl -X POST "http://localhost:8000/generate-post" \\
     -H "Content-Type: application/json" \\
     -d '{"repository": "your-username/your-repo", "time_period": "2h"}'

📖 For more info, see README.md

🌟 Your AI GitHub Explainer is ready to transform commits into engaging posts!
""")

def cleanup_artifacts():
    """Clean up any leftover artifact files"""
    print("\n🧹 Cleaning up artifact files...")
    
    # Look for common artifact patterns that might be left over
    patterns = [
        "project_structure*",
        "docker*", 
        "nginx*",
        "init_sql*",
        "*_prompt.txt",  # Old prompt files
    ]
    
    cleaned = 0
    for pattern in patterns:
        import glob
        for file in glob.glob(pattern):
            if os.path.isfile(file):
                os.remove(file)
                print(f"   🗑️  Removed: {file}")
                cleaned += 1
    
    if cleaned > 0:
        print(f"✅ Cleaned up {cleaned} leftover files")
    else:
        print("✅ No cleanup needed")

def main():
    """Main setup function"""
    print("🤖 AI GitHub Explainer - Project Setup")
    print("="*50)
    
    # Check environment
    if not check_dependencies():
        print("\n❌ Environment check failed. Please install Python 3.8+ and pip.")
        sys.exit(1)
    
    # Create directory structure
    create_directories()
    
    # Move artifact files to correct locations
    if not move_artifacts():
        print("\n⚠️  Some files are missing. The project may not work correctly.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            sys.exit(1)
    
    # Create __init__.py files
    create_init_files()
    
    # Validate final structure
    if not validate_structure():
        print("\n❌ Project structure validation failed!")
        print("Please check that all artifact files were downloaded correctly.")
        sys.exit(1)
    
    # Clean up leftover files
    cleanup_artifacts()
    
    # Show next steps
    generate_next_steps()

if __name__ == "__main__":
    main()
