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
    
    def prepare_data_for_claude(self, issues_data: Dict[str, Any], commits_data: List[Dict[str, str]]) -> str:
        formatted_data = "# GitHub Data for Post Generation\n\n"
        
        formatted_data += "## GitHub Issues Data:\n"
        formatted_data += f"```json\n{json.dumps(issues_data, indent=2, ensure_ascii=False)}\n```\n\n"
        
        formatted_data += "## Commits Data:\n\n"
        for commit in commits_data:
            formatted_data += f"### File: {commit['filename']}\n"
            formatted_data += f"```markdown\n{commit['content']}\n```\n\n"
        
        return formatted_data
    
    def generate_post_with_claude(self, data: str) -> str:
        prompt = f"""
RETURN ONLY HTML CODE. NO COMMENTS.

Create posts using EXACT same CSS and structure. Copy ALL styles from example without changes.

CRITICAL RULES:
1. Username: ALWAYS "Quantum Fusion" 
2. NO numbers in engagement buttons (just "👍 Like", "💬 Comment", "🔄 Share")
3. Copy CSS exactly - no style modifications
4. Include full visual elements: code diffs, stats, progress bars
5. Make technical content simple for users

Data:
{data}

Return complete HTML document starting with <!DOCTYPE html>
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
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
        
        formatted_data = self.prepare_data_for_claude(issues_data, commits_data)
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