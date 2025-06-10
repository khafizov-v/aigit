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
You must copy EXACTLY this HTML structure and CSS. Do not create your own styles.

Copy this exact CSS from the example:
```css
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 20px;
    background: #f0f2f5;
    color: #1c1e21;
}}

.post {{
    background: white;
    max-width: 520px;
    margin: 30px auto;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    overflow: hidden;
    border: 1px solid #dadde1;
}}

.post-header {{
    padding: 12px 16px;
    border-bottom: 1px solid #dadde1;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.profile-pic {{
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
}}

.post-info {{
    flex: 1;
}}

.username {{
    font-weight: 600;
    font-size: 15px;
}}

.timestamp {{
    color: #65676b;
    font-size: 13px;
}}

.platform-badge {{
    background: #e4e6ea;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 11px;
    color: #65676b;
}}

.post-content {{
    padding: 16px;
}}

.post-text {{
    line-height: 1.34;
    margin-bottom: 12px;
}}

.commit-visual {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    text-align: center;
    position: relative;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}

.commit-hash {{
    font-family: monospace;
    background: rgba(255,255,255,0.2);
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-bottom: 8px;
    display: inline-block;
}}

.commit-title {{
    font-size: 18px;
    font-weight: bold;
    margin: 8px 0;
}}

.code-diff {{
    background: #0d1117;
    color: #e6edf3;
    border-radius: 8px;
    padding: 16px;
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 12px;
    line-height: 1.4;
    position: relative;
    overflow-x: auto;
}}

.diff-added {{
    background: #0f5132;
    color: #56d364;
    display: block;
    padding: 2px 4px;
    margin: 1px 0;
}}

.diff-removed {{
    background: #490202;
    color: #f85149;
    display: block;
    padding: 2px 4px;
    margin: 1px 0;
}}

.stats-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin: 12px 0;
}}

.stat-box {{
    background: #f0f2f5;
    padding: 12px;
    border-radius: 8px;
    text-align: center;
}}

.stat-number {{
    font-size: 20px;
    font-weight: bold;
    color: #1877f2;
    margin: 0;
}}

.stat-label {{
    font-size: 11px;
    color: #65676b;
    margin: 4px 0 0 0;
}}

.interactive-buttons {{
    display: flex;
    gap: 8px;
    margin-top: 12px;
}}

.btn {{
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    transition: all 0.2s;
}}

.btn-primary {{
    background: #1877f2;
    color: white;
}}

.btn-secondary {{
    background: #e4e6ea;
    color: #1c1e21;
}}

.engagement-bar {{
    display: flex;
    justify-content: space-between;
    padding: 8px 16px;
    border-top: 1px solid #dadde1;
    background: #f7f8fa;
}}

.engagement-btn {{
    background: none;
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    color: #65676b;
    transition: background 0.2s;
}}

.hashtag {{
    color: #1877f2;
    font-weight: 500;
}}
```

Use EXACTLY this HTML structure:
```html
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
            🎉 <strong>MAJOR: Enhanced Smart Contract Host Functions!</strong><br><br>
            We just shipped commit <code>44761c3b</code> - enabling the <code>print</code> host function in PolkaVM with proper memory management! 🔥
        </div>
        
        <div class="commit-visual">
            <div class="commit-hash">44761c3b</div>
            <div class="commit-title">Enable `print` host function in PVM</div>
            <div style="font-size: 14px; opacity: 0.9;">
                📁 8 files changed • +129 -78 lines
            </div>
        </div>

        <div class="code-diff">
            <span class="diff-added">+ linker.define_typed("print", |caller: Caller&lt;T&gt;, msg_pointer: u32, len: u32| -> u64 {{</span>
            <span class="diff-removed">- linker.define_typed("print", |caller: Caller&lt;T&gt;| -> u64 {{</span>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">+5</div>
                <p class="stat-label">Host Functions</p>
            </div>
            <div class="stat-box">
                <div class="stat-number">100%</div>
                <p class="stat-label">Memory Safe</p>
            </div>
            <div class="stat-box">
                <div class="stat-number">0</div>
                <p class="stat-label">Buffer Overflows</p>
            </div>
        </div>

        <div class="interactive-buttons">
            <button class="btn btn-primary">View Commit</button>
            <button class="btn btn-secondary">Case Status</button>
        </div>

        <div style="margin-top: 12px;">
            <span class="hashtag">#SmartContracts</span> <span class="hashtag">#PolkaVM</span>
        </div>
    </div>
    
    <div class="engagement-bar">
        <button class="engagement-btn">👍 Like</button>
        <button class="engagement-btn">💬 Comment</button>
        <button class="engagement-btn">🔄 Share</button>
    </div>
</div>
```

Create 3-4 posts based on the GitHub data. Return ONLY the complete HTML starting with <!DOCTYPE html>. NO COMMENTS OR EXPLANATIONS.

Data:
{data}
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