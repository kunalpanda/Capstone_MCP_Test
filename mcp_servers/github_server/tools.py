import os
import httpx
import base64
from config import GITHUB_API_URL


def enforce_branch(kwargs: dict) -> dict:
    """Defaults missing branch/ref/from_branch to ACTIVE_BRANCH env var or 'main'."""
    import os
    active_branch = os.getenv("ACTIVE_BRANCH", "main")

    if "branch" in kwargs and not kwargs["branch"]:
        kwargs["branch"] = active_branch
    if "ref" in kwargs and not kwargs["ref"]:
        kwargs["ref"] = active_branch
    if "from_branch" in kwargs and not kwargs["from_branch"]:
        kwargs["from_branch"] = active_branch
    return kwargs


async def list_user_repos(user: str, github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    url = f"{GITHUB_API_URL}/users/{user}/repos?per_page=100"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

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


async def get_repo_info(owner: str, repo: str, github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

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


async def get_pr_details(owner: str, repo: str, pr_number: int, github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

        pr = res.json()
        return {
            "number": pr["number"],
            "title": pr["title"],
            "body": pr.get("body", ""),
            "author": pr["user"]["login"],
            "state": pr["state"],
            "merged": pr["merged"],
            "head_branch": pr["head"]["ref"],
            "base_branch": pr["base"]["ref"],
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"],
            "url": pr["html_url"],
        }


async def get_pr_diff(owner: str, repo: str, pr_number: int, github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = headers | {"Accept": "application/vnd.github.v3.diff"}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

        return {"pr_number": pr_number, "diff": res.text[:8000]}


async def get_file_tree(owner: str, repo: str, ref: str = "main", github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    kwargs = enforce_branch(locals())
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

        data = res.json()
        files = [f["path"]
                 for f in data.get("tree", []) if f["type"] == "blob"]
        return {"ref": ref, "count": len(files), "files": files[:2000]}


async def get_commit_diff(owner: str, repo: str, base: str, head: str, github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/compare/{base}...{head}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

        comp = res.json()
        changed_files = [
            {"filename": f["filename"], "status": f["status"],
                "changes": f["changes"]}
            for f in comp.get("files", [])
        ]
        return {
            "base": base,
            "head": head,
            "total_commits": comp["total_commits"],
            "changed_files": changed_files,
        }


async def get_file_content(owner: str, repo: str, path: str, ref: str = "main", github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    kwargs = enforce_branch(locals())
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {res.status_code}: {res.text}")

        data = res.json()

        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode(
                "utf-8", errors="ignore")
        else:
            content = data.get("content", "")

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


async def create_branch(owner: str, repo: str, branch_name: str, from_branch: str = "main", github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    kwargs = enforce_branch(locals())
    ref_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/ref/heads/{from_branch}"
    async with httpx.AsyncClient() as client:
        ref_res = await client.get(ref_url, headers=headers)
        if ref_res.status_code != 200:
            raise RuntimeError(
                f"Failed to get source branch: {ref_res.status_code}: {ref_res.text}")

        source_sha = ref_res.json()["object"]["sha"]

        create_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": source_sha
        }

        create_res = await client.post(create_url, headers=headers, json=payload)
        if create_res.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to create branch: {create_res.status_code}: {create_res.text}")

        data = create_res.json()
        return {
            "branch_name": branch_name,
            "from_branch": from_branch,
            "sha": data["object"]["sha"],
            "url": data["url"]
        }


async def create_or_update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str = "main", github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    if not message.startswith('[skip ci]'):
        message = f"[skip ci] {message}"
    kwargs = enforce_branch(locals())
    file_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": branch}

    async with httpx.AsyncClient() as client:
        get_res = await client.get(file_url, headers=headers, params=params)

        import base64
        encoded_content = base64.b64encode(
            content.encode("utf-8")).decode("utf-8")

        payload = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }

        if get_res.status_code == 200:
            existing_file = get_res.json()
            payload["sha"] = existing_file["sha"]
            operation = "updated"
        else:
            operation = "created"

        put_res = await client.put(file_url, headers=headers, json=payload)
        if put_res.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to {operation} file: {put_res.status_code}: {put_res.text}")

        data = put_res.json()
        return {
            "operation": operation,
            "path": path,
            "branch": branch,
            "commit_sha": data["commit"]["sha"],
            "file_sha": data["content"]["sha"],
            "url": data["content"]["html_url"]
        }


async def create_pull_request(owner: str, repo: str, title: str, body: str, head: str, base: str = "main", github_token: str = None):
    headers = {"Authorization": f"token {github_token}"}
    if not title.startswith('[Automated]'):
        title = f"[Automated] {title}"

    body = f"""[skip ci] {body}"""

    kwargs = enforce_branch(locals())
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": base
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, json=payload)
        if res.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to create PR: {res.status_code}: {res.text}")

        pr = res.json()
        return {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "head_branch": pr["head"]["ref"],
            "base_branch": pr["base"]["ref"],
            "author": pr["user"]["login"],
            "url": pr["html_url"],
            "created_at": pr["created_at"]
        }


async def list_tools():
    return {
        "tools": [
            {
                "name": "list_user_repos",
                "description": "List all repositories for a user or organization",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user": {"type": "string", "description": "GitHub username or organization name"}
                    },
                    "required": ["user"]
                }
            },
            {
                "name": "get_repo_info",
                "description": "Get detailed metadata for a specific GitHub repository including stars, forks, description, and default branch.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner (username or org name)"},
                        "repo": {"type": "string", "description": "Repository name"}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "get_pr_details",
                "description": "Get pull request metadata including title, author, status, and description",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "pr_number": {"type": "integer", "description": "Pull request number"}
                    },
                    "required": ["owner", "repo", "pr_number"]
                }
            },
            {
                "name": "get_pr_diff",
                "description": "Retrieve patch/diff text for a pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "pr_number": {"type": "integer", "description": "Pull request number"}
                    },
                    "required": ["owner", "repo", "pr_number"]
                }
            },
            {
                "name": "get_file_tree",
                "description": "Recursively list all files in a repository branch. Returns file paths for the entire repository structure.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "ref": {"type": "string", "description": "Git reference (branch name, tag, or commit SHA). Default is 'main'", "default": "main"}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "get_commit_diff",
                "description": "Compare two commits or branches to see what changed",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "base": {"type": "string", "description": "Base commit/branch"},
                        "head": {"type": "string", "description": "Head commit/branch to compare"}
                    },
                    "required": ["owner", "repo", "base", "head"]
                }
            },
            {
                "name": "get_file_content",
                "description": "Read the content of a specific file from a repository. Returns decoded file content as text.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "path": {"type": "string", "description": "File path within the repository (e.g., 'src/main.py')"},
                        "ref": {"type": "string", "description": "Git reference (branch, tag, or commit). Default is 'main'", "default": "main"}
                    },
                    "required": ["owner", "repo", "path"]
                }
            },
            {
                "name": "create_branch",
                "description": "Create a new branch from an existing branch.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "branch_name": {"type": "string", "description": "Name for the new branch"},
                        "from_branch": {"type": "string", "description": "Source branch to create from (default: main)", "default": "main"}
                    },
                    "required": ["owner", "repo", "branch_name"]
                }
            },
            {
                "name": "create_or_update_file",
                "description": "Create a new file or update an existing file in the repository.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "path": {"type": "string", "description": "File path (e.g., 'web/tests/new_test.py')"},
                        "content": {"type": "string", "description": "Complete file content"},
                        "message": {"type": "string", "description": "Commit message"},
                        "branch": {"type": "string", "description": "Branch name (default: main)", "default": "main"}
                    },
                    "required": ["owner", "repo", "path", "content", "message"]
                }
            },
            {
                "name": "create_pull_request",
                "description": "Create a pull request to merge one branch into another.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "PR title"},
                        "body": {"type": "string", "description": "PR description"},
                        "head": {"type": "string", "description": "Source branch"},
                        "base": {"type": "string", "description": "Target branch (default: main)", "default": "main"}
                    },
                    "required": ["owner", "repo", "title", "body", "head"]
                }
            }
        ]
    }
