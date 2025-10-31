import os
import httpx
import base64
from .config import GITHUB_TOKEN, GITHUB_API_URL

# Shared HTTP headers
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}


# =========================================================
# 1️⃣  list_user_repos  →  List all repos for a user/org
# =========================================================
async def list_user_repos(user: str):
    url = f"{GITHUB_API_URL}/users/{user}/repos?per_page=100"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        repos = [
            {
                "name": r["name"],
                "private": r["private"],
                "language": r["language"],
                "stars": r["stargazers_count"],
                "url": r["html_url"],
            }
            for r in res.json()
        ]
        return {"user": user, "count": len(repos), "repos": repos}


# =========================================================
# 2️⃣  get_repo_info  →  Retrieve metadata for a repo
# =========================================================
async def get_repo_info(owner: str, repo: str):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        data = res.json()
        return {
            "name": data["name"],
            "owner": data["owner"]["login"],
            "description": data["description"],
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"],
            "default_branch": data["default_branch"],
            "updated_at": data["updated_at"],
            "url": data["html_url"],
        }


# =========================================================
# 3️⃣  get_pr_details  →  Title, author, status, etc.
# =========================================================
async def get_pr_details(owner: str, repo: str, pr_number: int):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        pr = res.json()
        return {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "state": pr["state"],
            "merged": pr["merged"],
            "head_branch": pr["head"]["ref"],
            "base_branch": pr["base"]["ref"],
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"],
            "url": pr["html_url"],
        }


# =========================================================
# 4️⃣  get_pr_diff  →  Retrieve patch/diff text for a PR
# =========================================================
async def get_pr_diff(owner: str, repo: str, pr_number: int):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = HEADERS | {"Accept": "application/vnd.github.v3.diff"}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        return {"pr_number": pr_number, "diff": res.text[:8000]}  # truncate for LLM safety


# =========================================================
# 5️⃣  get_file_tree  →  Recursively list files in a branch
# =========================================================
async def get_file_tree(owner: str, repo: str, ref: str = "main"):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        data = res.json()
        files = [f["path"] for f in data.get("tree", []) if f["type"] == "blob"]
        return {"ref": ref, "count": len(files), "files": files[:2000]}  # cap for safety


# =========================================================
# 6️⃣  get_commit_diff  →  Compare two commits or branches
# =========================================================
async def get_commit_diff(owner: str, repo: str, base: str, head: str):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/compare/{base}...{head}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        comp = res.json()
        changed_files = [
            {"filename": f["filename"], "status": f["status"], "changes": f["changes"]}
            for f in comp.get("files", [])
        ]
        return {
            "base": base,
            "head": head,
            "total_commits": comp["total_commits"],
            "changed_files": changed_files,
        }
    
# =========================================================
# 7️⃣  get_file_content  →  Retrieve and decode file content
# =========================================================
async def get_file_content(owner: str, repo: str, path: str, ref: str = "main"):
    """
    Returns the decoded source code for a given file path and branch/ref.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"GitHub returned {res.status_code}: {res.text}")

        data = res.json()

        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        else:
            content = data.get("content", "")

        # For safety: truncate overly large files
        truncated = len(content) > 12000
        if truncated:
            content = content[:12000] + "\n\n# [Truncated for length]\n"

        return {
            "path": path,
            "ref": ref,
            "size": data.get("size"),
            "truncated": truncated,
            "content": content
        }

# =========================================================
# MCP tool list
# =========================================================
async def list_tools():
    return {
        "tools": [
            {"name": "list_user_repos", "description": "List all repos for a user/org"},
            {"name": "get_repo_info", "description": "Get metadata for a repository"},
            {"name": "get_pr_details", "description": "Get pull request metadata"},
            {"name": "get_pr_diff", "description": "Get patch diff of a pull request"},
            {"name": "get_file_tree", "description": "List files in a branch recursively"},
            {"name": "get_commit_diff", "description": "Compare two commits/branches"},
            {"name": "get_file_content", "description": "Retrieve and decode file content"},
        ]
    }
