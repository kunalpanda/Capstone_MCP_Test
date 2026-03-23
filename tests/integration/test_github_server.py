"""
Integration tests for mcp_servers.github_server (server.py + tools.py).

Uses FastAPI TestClient against the JSON-RPC endpoint with mocked httpx
calls to GitHub API.
"""
import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure the github_server package is importable
GITHUB_SERVER_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "mcp_servers", "github_server"
)
if GITHUB_SERVER_DIR not in sys.path:
    sys.path.insert(0, GITHUB_SERVER_DIR)


@pytest.fixture(autouse=True)
def _set_github_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_fake")


# ---------------------------------------------------------------------------
# Import the FastAPI app AFTER env is set
# ---------------------------------------------------------------------------
@pytest.fixture
def github_client():
    from fastapi.testclient import TestClient
    # Re-import to pick up env
    import importlib
    import config as cfg_mod
    importlib.reload(cfg_mod)
    import server as srv_mod
    importlib.reload(srv_mod)
    return TestClient(srv_mod.app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def jsonrpc_request(method, params=None, req_id="1"):
    return {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": req_id}


# =========================================================================
# GET / (root)
# =========================================================================
class TestGitHubServerRoot:
    def test_root_returns_status(self, github_client):
        resp = github_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "GitHub MCP" in data["message"]


# =========================================================================
# tools/list
# =========================================================================
class TestToolsList:
    def test_returns_all_tools(self, github_client):
        payload = jsonrpc_request("tools/list")
        resp = github_client.post("/", json=payload)
        assert resp.status_code == 200
        result = resp.json()["result"]
        tool_names = [t["name"] for t in result["tools"]]
        expected = [
            "list_user_repos", "get_repo_info", "get_pr_details",
            "get_pr_diff", "get_file_tree", "get_commit_diff",
            "get_file_content", "create_branch",
            "create_or_update_file", "create_pull_request",
        ]
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"

    def test_tools_have_input_schema(self, github_client):
        payload = jsonrpc_request("tools/list")
        resp = github_client.post("/", json=payload)
        for tool in resp.json()["result"]["tools"]:
            assert "input_schema" in tool, f"Tool {tool['name']} missing schema"
            assert tool["input_schema"]["type"] == "object"


# =========================================================================
# tools/call – list_user_repos
# =========================================================================
class TestListUserRepos:
    @pytest.mark.asyncio
    def test_list_user_repos_success(self, github_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "test_banking_app",
                "private": False,
                "language": "Java",
                "stargazers_count": 5,
                "html_url": "https://github.com/kunalpanda/test_banking_app",
            }
        ]

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc_request("tools/call", {
                "name": "list_user_repos",
                "params": {"user": "kunalpanda"},
            })
            resp = github_client.post("/", json=payload)

        assert resp.status_code == 200
        result = resp.json()["result"]
        assert result["count"] == 1
        assert result["repos"][0]["name"] == "test_banking_app"


# =========================================================================
# tools/call – get_file_content
# =========================================================================
class TestGetFileContent:
    def test_decodes_base64_content(self, github_client):
        import base64
        raw = "public class Main { }"
        encoded = base64.b64encode(raw.encode()).decode()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": encoded,
            "encoding": "base64",
            "size": len(raw),
        }

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc_request("tools/call", {
                "name": "get_file_content",
                "params": {"owner": "o", "repo": "r", "path": "Main.java", "ref": "main"},
            })
            resp = github_client.post("/", json=payload)

        result = resp.json()["result"]
        assert "public class Main" in result["content"]
        assert result["truncated"] is False


# =========================================================================
# tools/call – unknown tool
# =========================================================================
class TestUnknownTool:
    def test_unknown_tool_returns_error(self, github_client):
        payload = jsonrpc_request("tools/call", {
            "name": "nonexistent_tool",
            "params": {},
        })
        resp = github_client.post("/", json=payload)
        assert resp.status_code == 200  # JSON-RPC error is still 200
        assert "error" in resp.json()

    def test_unknown_method_returns_error(self, github_client):
        payload = jsonrpc_request("tools/bogus")
        resp = github_client.post("/", json=payload)
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == -32601


# =========================================================================
# tools/call – create_branch
# =========================================================================
class TestCreateBranch:
    def test_create_branch_success(self, github_client):
        ref_resp = MagicMock()
        ref_resp.status_code = 200
        ref_resp.json.return_value = {"object": {"sha": "abc123"}}

        create_resp = MagicMock()
        create_resp.status_code = 201
        create_resp.json.return_value = {
            "ref": "refs/heads/fix-tests-1",
            "object": {"sha": "abc123"},
            "url": "https://api.github.com/repos/o/r/git/refs/heads/fix-tests-1",
        }

        call_count = 0

        async def route_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ref_resp if call_count == 1 else create_resp

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=ref_resp)
            instance.post = AsyncMock(return_value=create_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc_request("tools/call", {
                "name": "create_branch",
                "params": {
                    "owner": "kunalpanda",
                    "repo": "test_banking_app",
                    "branch_name": "fix-tests-1",
                    "from_branch": "main",
                },
            })
            resp = github_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["branch_name"] == "fix-tests-1"
        assert result["sha"] == "abc123"


# =========================================================================
# tools/call – create_or_update_file
# =========================================================================
class TestCreateOrUpdateFile:
    def test_creates_new_file(self, github_client):
        get_resp = MagicMock()
        get_resp.status_code = 404  # File doesn't exist

        put_resp = MagicMock()
        put_resp.status_code = 201
        put_resp.json.return_value = {
            "commit": {"sha": "new-sha"},
            "content": {
                "sha": "file-sha",
                "html_url": "https://github.com/o/r/blob/main/test.py",
            },
        }

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=get_resp)
            instance.put = AsyncMock(return_value=put_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc_request("tools/call", {
                "name": "create_or_update_file",
                "params": {
                    "owner": "o",
                    "repo": "r",
                    "path": "test.py",
                    "content": "print('hello')",
                    "message": "Add test",
                    "branch": "main",
                },
            })
            resp = github_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["operation"] == "created"
        assert result["path"] == "test.py"

    def test_commit_message_gets_skip_ci_prefix(self, github_client):
        get_resp = MagicMock()
        get_resp.status_code = 404

        put_resp = MagicMock()
        put_resp.status_code = 201
        put_resp.json.return_value = {
            "commit": {"sha": "s"},
            "content": {"sha": "f", "html_url": "url"},
        }

        captured_payload = {}

        async def capture_put(url, headers=None, json=None):
            captured_payload.update(json or {})
            return put_resp

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=get_resp)
            instance.put = capture_put
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc_request("tools/call", {
                "name": "create_or_update_file",
                "params": {
                    "owner": "o", "repo": "r", "path": "a.py",
                    "content": "x", "message": "Add file", "branch": "main",
                },
            })
            github_client.post("/", json=payload)

        assert captured_payload["message"].startswith("[skip ci]")
