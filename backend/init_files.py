# app/__init__.py
"""
AI GitHub Explainer - Transform GitHub commits into engaging social media posts
"""

__version__ = "1.0.0"
__author__ = "AI GitHub Explainer Team"
__email__ = "team@github-explainer.com"

# app/core/__init__.py
"""
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

# app/models/__init__.py
"""
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

# app/utils/__init__.py
"""
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