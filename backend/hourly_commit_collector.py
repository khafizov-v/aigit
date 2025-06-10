import requests
import pandas as pd
import datetime
import time
import os
from dotenv import load_dotenv
import argparse
from pathlib import Path

# ----------------------
# Step 1: Load Environment Variables
# ----------------------
def load_environment():
    """Load environment variables from .env file in the same directory."""
    env_path = Path(__file__).parent / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        github_token = os.getenv('GITHUB_TOKEN')
        github_org = os.getenv('GITHUB_ORG')
        
        if not github_token:
            raise ValueError("GITHUB_TOKEN not found in .env file.")
        if not github_org:
            raise ValueError("GITHUB_ORG not found in .env file.")
            
        return github_token, github_org
    else:
        raise FileNotFoundError(f".env file not found at: {env_path}. Please create one with GITHUB_TOKEN and GITHUB_ORG")

# ----------------------
# Step 2: GitHub API Functions
# ----------------------

def safe_get(url, headers=None, params=None):
    """
    Makes a GET request and checks for rate limit issues.
    If the rate limit is exceeded, it sleeps until the reset time.
    """
    while True:
        response = requests.get(url, headers=headers, params=params)
        
        # Check for rate limit
        if response.status_code == 403:
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = int(response.headers['X-RateLimit-Remaining'])
                if remaining == 0:
                    reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
                    sleep_time = max(reset_time - time.time(), 0) + 5
                    print(f"Rate limit reached. Sleeping for {sleep_time:.0f} seconds.")
                    time.sleep(sleep_time)
                    continue
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        return response

def get_org_members(org, token):
    """Fetch all members for the given organization."""
    members = set()
    url = f"https://api.github.com/orgs/{org}/members?per_page=100"
    headers = {"Authorization": f"token {token}"}
    
    while url:
        response = safe_get(url, headers=headers)
        data = response.json()
        
        for member in data:
            members.add(member.get("login"))
        
        # Handle pagination
        if 'Link' in response.headers:
            links = response.headers['Link']
            next_url = None
            for link in links.split(','):
                if 'rel="next"' in link:
                    next_url = link[link.find("<")+1:link.find(">")]
                    break
            url = next_url
        else:
            url = None
    
    return members

def fetch_repositories(org, token):
    """Fetch all repositories for the given organization."""
    repos = []
    url = f"https://api.github.com/orgs/{org}/repos?per_page=100"
    headers = {"Authorization": f"token {token}"}
    
    while url:
        response = safe_get(url, headers=headers)
        data = response.json()
        
        for repo in data:
            repos.append(repo["name"])
        
        # Handle pagination
        if 'Link' in response.headers:
            links = response.headers['Link']
            next_url = None
            for link in links.split(','):
                if 'rel="next"' in link:
                    next_url = link[link.find("<")+1:link.find(">")]
                    break
            url = next_url
        else:
            url = None
    
    return repos

def fetch_branches(org, repo, token):
    """Fetch the list of branches for a given repository."""
    branches = []
    url = f"https://api.github.com/repos/{org}/{repo}/branches?per_page=100"
    headers = {"Authorization": f"token {token}"}
    
    try:
        response = safe_get(url, headers=headers)
        data = response.json()
        
        for branch in data:
            branches.append(branch["name"])
    except Exception as e:
        print(f"Error fetching branches for {repo}: {e}")
    
    return branches

def fetch_commit_details(org, repo, sha, token):
    """Fetch detailed commit information including diff."""
    url = f"https://api.github.com/repos/{org}/{repo}/commits/{sha}"
    headers = {"Authorization": f"token {token}"}
    
    try:
        response = safe_get(url, headers=headers)
        data = response.json()
        
        stats = data.get("stats", {})
        files = data.get("files", [])
        
        # Prepare file changes info
        file_changes = []
        for file_info in files:
            file_changes.append({
                "filename": file_info.get("filename", ""),
                "status": file_info.get("status", ""),  # added, modified, deleted
                "additions": file_info.get("additions", 0),
                "deletions": file_info.get("deletions", 0),
                "changes": file_info.get("changes", 0),
                "patch": file_info.get("patch", "")  # actual diff
            })
        
        return {
            "stats": {
                "total_additions": stats.get("additions", 0),
                "total_deletions": stats.get("deletions", 0),
                "total_changes": stats.get("total", 0)
            },
            "files": file_changes,
            "files_changed": len(files)
        }
        
    except Exception as e:
        print(f"Error fetching details for commit {sha}: {e}")
        return None

def fetch_commits_for_branch(org, repo, branch, token, since=None, until=None, org_members=None, include_details=True):
    """Fetch commit data for a given branch within the date range."""
    commits = []
    url = f"https://api.github.com/repos/{org}/{repo}/commits"
    headers = {"Authorization": f"token {token}"}
    params = {"sha": branch, "per_page": 100}
    
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    while url:
        try:
            response = safe_get(url, headers=headers, params=params)
            data = response.json()
            
            if not isinstance(data, list):
                break
            
            for commit in data:
                author_obj = commit.get("author")
                
                # Filter by org members if specified
                if org_members is not None:
                    if not author_obj or author_obj.get("login") not in org_members:
                        continue
                
                sha = commit.get("sha")
                commit_data = commit.get("commit", {})
                author_data = commit_data.get("author", {})
                
                commit_info = {
                    "repo": repo,
                    "branch": branch,
                    "sha": sha,
                    "message": commit_data.get("message", ""),
                    "author": author_data.get("name", "Unknown"),
                    "author_login": author_obj.get("login") if author_obj else "Unknown",
                    "date": author_data.get("date"),
                    "commit_link": f"https://github.com/{org}/{repo}/commit/{sha}"
                }
                
                # Fetch detailed information if requested
                if include_details:
                    print(f"      Fetching details for commit {sha[:8]}...")
                    details = fetch_commit_details(org, repo, sha, token)
                    if details:
                        commit_info.update(details)
                
                commits.append(commit_info)
            
            # Handle pagination
            if 'Link' in response.headers:
                links = response.headers['Link']
                next_url = None
                for link in links.split(','):
                    if 'rel="next"' in link:
                        next_url = link[link.find("<")+1:link.find(">")]
                        break
                url = next_url
                params = {}
            else:
                break
                
        except Exception as e:
            print(f"Error fetching commits for {repo}/{branch}: {e}")
            break
    
    return commits

def fetch_all_commits(org, token, since=None, until=None, include_all_users=False, include_details=True):
    """Fetch commits for all repositories in the organization."""
    unique_commits_dict = {}
    commit_branches = {}

    # Get organization members
    org_members = None
    if not include_all_users:
        org_members = get_org_members(org, token)
        print(f"Organization members found: {len(org_members)}")

    # Get repositories
    repos = fetch_repositories(org, token)
    print(f"Found {len(repos)} repositories: {repos}")

    for repo in repos:
        print(f"\nProcessing repository: {repo}")
        branches = fetch_branches(org, repo, token)
        print(f"  Found {len(branches)} branches: {branches}")

        for branch in branches:
            print(f"    Processing branch: {branch}")
            branch_commits = fetch_commits_for_branch(
                org, repo, branch, token, since, until, org_members, include_details
            )
            print(f"      Found {len(branch_commits)} commits")

            # Process commits and track unique ones
            for commit in branch_commits:
                sha = commit["sha"]

                # Track branches for each commit
                if sha not in commit_branches:
                    commit_branches[sha] = []
                commit_branches[sha].append(branch)

                # Only add if we haven't seen this commit before
                if sha not in unique_commits_dict:
                    unique_commits_dict[sha] = commit

    # Add branch information to commits
    all_unique_commits = list(unique_commits_dict.values())
    for commit in all_unique_commits:
        commit["appears_in_branches"] = ", ".join(commit_branches[commit["sha"]])

    print(f"\nTotal unique commits: {len(all_unique_commits)}")
    print(f"Commits in multiple branches: {sum(1 for sha, branches in commit_branches.items() if len(branches) > 1)}")

    return all_unique_commits

# ----------------------
# Step 3: Report Generation
# ----------------------

def generate_summary(df, org, start_time, end_time):
    """Generate a Markdown summary of the commit data."""
    if df.empty:
        return f"No commits found for {org} in the last hour ({start_time} - {end_time})."
    
    total_commits = len(df)
    summary_lines = [f"# Hourly GitHub Activity Report for {org}"]
    summary_lines.append(f"**Time Range:** {start_time} - {end_time}")
    summary_lines.append(f"**Total Commits:** {total_commits} (unique)")
    summary_lines.append("")
    
    # Group by repository and author
    grouped = df.groupby(["repo", "author"])
    
    current_repo = None
    for (repo, author), group_df in grouped:
        if repo != current_repo:
            summary_lines.append(f"## Repository: [{repo}](https://github.com/{org}/{repo})")
            current_repo = repo
        
        commit_count = len(group_df)
        commit_links = group_df["commit_link"].unique().tolist()
        
        # Create numbered links (limit to 5)
        commit_links_md = ", ".join([f"[{i+1}]({link})" for i, link in enumerate(commit_links[:5])])
        if len(commit_links) > 5:
            commit_links_md += f", ... (+{len(commit_links) - 5} more)"
        
        summary_lines.append(f"- **{author}**: {commit_count} commits ({commit_links_md})")
    
    return "\n".join(summary_lines)

def save_commit_details(commit, org, output_dir="reports"):
    """Save individual commit details to a separate file."""
    if not commit.get("files"):
        return None
    
    # Create commits subdirectory
    commits_dir = os.path.join(output_dir, "commits")
    os.makedirs(commits_dir, exist_ok=True)
    
    # Create filename: repo_sha_date.md
    date_str = pd.to_datetime(commit["date"]).strftime("%Y%m%d_%H%M%S")
    filename = f"{commit['repo']}_{commit['sha'][:8]}_{date_str}.md"
    filepath = os.path.join(commits_dir, filename)
    
    # Generate commit report
    content = []
    content.append(f"# Commit Details: {commit['sha'][:8]}")
    content.append(f"")
    content.append(f"**Repository:** [{commit['repo']}](https://github.com/{org}/{commit['repo']})")
    content.append(f"**Author:** {commit['author']} ({commit['author_login']})")
    content.append(f"**Date:** {commit['date']}")
    content.append(f"**Branch(es):** {commit['appears_in_branches']}")
    content.append(f"**Commit Link:** [View on GitHub]({commit['commit_link']})")
    content.append(f"")
    content.append(f"## Commit Message")
    content.append(f"```")
    content.append(commit['message'])
    content.append(f"```")
    content.append(f"")
    
    # Add statistics if available
    if commit.get("stats"):
        stats = commit["stats"]
        content.append(f"## Statistics")
        content.append(f"- **Files changed:** {commit.get('files_changed', 0)}")
        content.append(f"- **Lines added:** {stats['total_additions']}")
        content.append(f"- **Lines deleted:** {stats['total_deletions']}")
        content.append(f"- **Total changes:** {stats['total_changes']}")
        content.append(f"")
    
    # Add file changes
    if commit.get("files"):
        content.append(f"## File Changes")
        content.append(f"")
        
        for file_info in commit["files"]:
            status_emoji = {
                "added": "🆕",
                "modified": "✏️", 
                "deleted": "🗑️",
                "renamed": "🔄"
            }
            
            emoji = status_emoji.get(file_info["status"], "📝")
            content.append(f"### {emoji} {file_info['filename']} ({file_info['status']})")
            
            if file_info["additions"] or file_info["deletions"]:
                content.append(f"**Changes:** +{file_info['additions']} -{file_info['deletions']}")
            
            if file_info.get("patch"):
                content.append(f"")
                content.append(f"```diff")
                content.append(file_info["patch"])
                content.append(f"```")
            
            content.append(f"")
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    return filepath

def get_hourly_output_dir(base_dir="hourly_reports"):
    """Create and return hourly output directory with timestamp."""
    now = datetime.datetime.now()
    hour_dir = now.strftime("%Y%m%d_%H")  # Format: 20231215_14 for 2023-12-15 14:00
    output_dir = os.path.join(base_dir, hour_dir)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_hourly_report(df, summary, org, start_time, end_time, output_dir, save_individual_commits=True):
    """Save the hourly report to files."""
    timestamp = datetime.datetime.now().strftime("%H%M")  # Just hour and minute for hourly reports
    
    # Save CSV
    csv_path = os.path.join(output_dir, f"{org}_commits_{timestamp}.csv")
    
    # Create a clean DataFrame for CSV (remove complex nested data)
    csv_df = df.copy()
    if 'files' in csv_df.columns:
        csv_df = csv_df.drop(['files'], axis=1)
    if 'stats' in csv_df.columns:
        # Flatten stats into separate columns
        if not csv_df.empty and csv_df.iloc[0].get('stats'):
            csv_df['total_additions'] = csv_df['stats'].apply(lambda x: x.get('total_additions', 0) if x else 0)
            csv_df['total_deletions'] = csv_df['stats'].apply(lambda x: x.get('total_deletions', 0) if x else 0)
            csv_df['total_changes'] = csv_df['stats'].apply(lambda x: x.get('total_changes', 0) if x else 0)
            csv_df['files_changed'] = csv_df['files_changed'] if 'files_changed' in csv_df.columns else 0
        csv_df = csv_df.drop(['stats'], axis=1)
    
    csv_df.to_csv(csv_path, index=False)
    
    # Save Markdown summary
    md_path = os.path.join(output_dir, f"{org}_summary_{timestamp}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    # Save individual commit files
    individual_files = []
    if save_individual_commits and not df.empty:
        print(f"\nSaving individual commit files...")
        for _, commit in df.iterrows():
            commit_dict = commit.to_dict()
            if commit_dict.get("files"):  # Only save if there are file changes
                filepath = save_commit_details(commit_dict, org, output_dir)
                if filepath:
                    individual_files.append(filepath)
    
    # Save metadata file
    metadata_path = os.path.join(output_dir, "metadata.txt")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"GitHub Hourly Commit Collection\n")
        f.write(f"Organization: {org}\n")
        f.write(f"Start Time: {start_time}\n")
        f.write(f"End Time: {end_time}\n")
        f.write(f"Total Commits: {len(df)}\n")
        f.write(f"Collection Time: {datetime.datetime.now().isoformat()}\n")
    
    print(f"\nHourly reports saved to: {output_dir}")
    print(f"  CSV: {os.path.basename(csv_path)}")
    print(f"  Markdown: {os.path.basename(md_path)}")
    print(f"  Metadata: metadata.txt")
    if individual_files:
        print(f"  Individual commits: {len(individual_files)} files in commits/")
    
    return csv_path, md_path, individual_files

# ----------------------
# Step 4: Main Function
# ----------------------

def main():
    parser = argparse.ArgumentParser(description='Collect GitHub organization commits for the last hour')
    parser.add_argument('--organization', help='GitHub organization name (overrides GITHUB_ORG from .env)')
    parser.add_argument('--hours-back', type=int, default=1, help='Number of hours back to collect (default: 1)')
    parser.add_argument('--include-all-users', action='store_true', 
                       help='Include commits from all users, not just org members')
    parser.add_argument('--output-dir', default='hourly_reports', 
                       help='Base output directory (default: hourly_reports)')
    parser.add_argument('--no-individual-files', action='store_true', 
                       help='Don\'t save individual commit files')
    
    args = parser.parse_args()
    
    try:
        # Load environment variables
        api_key, default_org = load_environment()
        print(f"GitHub token loaded (starts with: {api_key[:5]}...)")
        
        # Use organization from command line or from .env
        organization = args.organization or default_org
        print(f"Using organization: {organization}")
        
        # Calculate time range for the last hour(s)
        now = datetime.datetime.now()
        start_time = now - datetime.timedelta(hours=args.hours_back)
        end_time = now
        
        # Format for GitHub API (ISO 8601 with Z)
        start_dt = start_time.isoformat() + "Z"
        end_dt = end_time.isoformat() + "Z"
        
        # Format for display
        start_display = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_display = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\nCollecting commits for '{organization}' from the last {args.hours_back} hour(s)")
        print(f"Time range: {start_display} to {end_display}")
        print("=" * 80)
        
        # Fetch commits
        commits = fetch_all_commits(
            organization, 
            api_key, 
            since=start_dt, 
            until=end_dt,
            include_all_users=args.include_all_users
        )
        
        # Create hourly output directory
        output_dir = get_hourly_output_dir(args.output_dir)
        
        if not commits:
            print(f"No commits found for the specified time range.")
            # Still create metadata file for tracking
            metadata_path = os.path.join(output_dir, "metadata.txt")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(f"GitHub Hourly Commit Collection\n")
                f.write(f"Organization: {organization}\n")
                f.write(f"Start Time: {start_display}\n")
                f.write(f"End Time: {end_display}\n")
                f.write(f"Total Commits: 0\n")
                f.write(f"Collection Time: {datetime.datetime.now().isoformat()}\n")
            print(f"Metadata saved to: {output_dir}")
            return
        
        # Create DataFrame
        df = pd.DataFrame(commits)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False)
        
        # Generate summary
        summary = generate_summary(df, organization, start_display, end_display)
        
        # Display results
        print("\n" + "=" * 80)
        print("HOURLY SUMMARY:")
        print("=" * 80)
        print(summary)
        
        # Save reports
        save_hourly_report(
            df, summary, organization, start_display, end_display, output_dir,
            save_individual_commits=(not args.no_individual_files)
        )
        
        # Display sample commits
        if len(df) > 0:
            print(f"\n" + "=" * 80)
            print(f"ALL COMMITS ({len(df)} total):")
            print("=" * 80)
            sample_df = df[['date', 'author', 'repo', 'message', 'commit_link']]
            print(sample_df.to_string(index=False, max_colwidth=60))
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())