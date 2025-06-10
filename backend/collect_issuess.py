import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ORG = os.getenv("GITHUB_ORG")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def get_all_repos(org):
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}"
        res = requests.get(url, headers=HEADERS)
        data = res.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos

def get_repo_issues(owner, repo):
    issues = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues?per_page=100&page={page}&state=all"
        res = requests.get(url, headers=HEADERS)
        data = res.json()
        if not data or "message" in data:
            break
        for issue in data:
            if 'pull_request' not in issue:
                issue_data = {
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "author": issue["user"]["login"] if issue.get("user") else None,
                    "labels": [label["name"] for label in issue.get("labels", [])],
                    "created_at": issue["created_at"],
                    "updated_at": issue["updated_at"],
                    "closed_at": issue["closed_at"],
                    "body": issue["body"],
                    "url": issue["html_url"],
                    "comments": []
                }

                # Комментарии к issue
                comments_url = issue["comments_url"]
                comments_res = requests.get(comments_url, headers=HEADERS)
                comments_data = comments_res.json()
                for comment in comments_data:
                    issue_data["comments"].append({
                        "author": comment["user"]["login"],
                        "created_at": comment["created_at"],
                        "body": comment["body"]
                    })

                issues.append(issue_data)
        page += 1
    return issues

def main():
    print(f"📥 Собираем данные из GitHub: {GITHUB_ORG}")
    repos = get_all_repos(GITHUB_ORG)
    all_data = []

    for repo in repos:
        print(f"🔍 Репозиторий: {repo['name']}")
        repo_data = {
            "name": repo["name"],
            "url": repo["html_url"],
            "issues": get_repo_issues(GITHUB_ORG, repo["name"])
        }
        all_data.append(repo_data)

    with open("github_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print("✅ Данные сохранены в github_data.json")

if __name__ == "__main__":
    main()
