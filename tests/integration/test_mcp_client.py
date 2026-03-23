"""
Integration tests for orchestrator.mcp_client.

Tests verify JSON-RPC payload construction, header merging,
GCP identity token fallback, and error propagation.
"""
import json
import uuid
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from orchestrator.mcp_client import call_mcp_tool, get_gcp_identity_token


# ---------------------------------------------------------------------------
# get_gcp_identity_token
# ---------------------------------------------------------------------------
class TestGCPIdentityToken:
    """Token fetching from GCP metadata server."""

    @pytest.mark.asyncio
    async def test_returns_token_on_success(self):
        mock_response = MagicMock()
        mock_response.text = "eyJhbGciOi.token.sig"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            token = await get_gcp_identity_token("http://example.com")
            assert token == "eyJhbGciOi.token.sig"

    @pytest.mark.asyncio
    async def test_raises_on_metadata_failure(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("no metadata"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.ConnectError):
                await get_gcp_identity_token("http://example.com")


# ---------------------------------------------------------------------------
# call_mcp_tool
# ---------------------------------------------------------------------------
class TestCallMCPTool:
    """Verify JSON-RPC envelope and response parsing."""

    @pytest.mark.asyncio
    async def test_payload_structure_tools_list(self):
        """tools/list should produce a valid JSON-RPC request with no name/params."""
        captured = {}

        async def fake_post(url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"jsonrpc": "2.0", "result": {"tools": []}, "id": "1"}
            return resp

        mock_client = AsyncMock()
        mock_client.post = fake_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            with patch("orchestrator.mcp_client.get_gcp_identity_token", side_effect=Exception("local")):
                result = await call_mcp_tool(
                    server_url="http://localhost:8010",
                    method="tools/list"
                )

        assert captured["json"]["method"] == "tools/list"
        assert captured["json"]["jsonrpc"] == "2.0"
        assert "id" in captured["json"]
        assert result["result"]["tools"] == []

    @pytest.mark.asyncio
    async def test_payload_includes_name_and_params(self):
        """tools/call should embed name + params in the envelope."""
        captured = {}

        async def fake_post(url, json=None, headers=None):
            captured["json"] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"jsonrpc": "2.0", "result": {"ok": True}, "id": "1"}
            return resp

        mock_client = AsyncMock()
        mock_client.post = fake_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            with patch("orchestrator.mcp_client.get_gcp_identity_token", side_effect=Exception("local")):
                await call_mcp_tool(
                    server_url="http://localhost:8010",
                    method="tools/call",
                    name="get_file_tree",
                    params={"owner": "kunalpanda", "repo": "test_banking_app"},
                )

        payload = captured["json"]
        assert payload["params"]["name"] == "get_file_tree"
        assert payload["params"]["params"]["owner"] == "kunalpanda"

    @pytest.mark.asyncio
    async def test_custom_headers_merged(self):
        """Extra headers (e.g. X-GitHub-Token) should be sent alongside auth."""
        captured_headers = {}

        async def fake_post(url, json=None, headers=None):
            captured_headers.update(headers or {})
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"jsonrpc": "2.0", "result": {}, "id": "1"}
            return resp

        mock_client = AsyncMock()
        mock_client.post = fake_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            with patch("orchestrator.mcp_client.get_gcp_identity_token", side_effect=Exception("local")):
                await call_mcp_tool(
                    server_url="http://localhost:8010",
                    method="tools/call",
                    name="trigger_build",
                    headers={"X-Jenkins-Token": "tok123", "X-Jenkins-URL": "http://j:8080"},
                )

        assert captured_headers.get("X-Jenkins-Token") == "tok123"
        assert captured_headers.get("X-Jenkins-URL") == "http://j:8080"

    @pytest.mark.asyncio
    async def test_gcp_token_added_when_available(self):
        """When GCP metadata is reachable, Authorization header is added."""
        captured_headers = {}

        async def fake_post(url, json=None, headers=None):
            captured_headers.update(headers or {})
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"jsonrpc": "2.0", "result": {}, "id": "1"}
            return resp

        mock_client = AsyncMock()
        mock_client.post = fake_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            with patch(
                "orchestrator.mcp_client.get_gcp_identity_token",
                return_value="my-gcp-token",
            ):
                await call_mcp_tool(
                    server_url="http://localhost:8010",
                    method="tools/list"
                )

        assert captured_headers.get("Authorization") == "Bearer my-gcp-token"

    @pytest.mark.asyncio
    async def test_http_error_propagates(self):
        """Non-200 responses from the MCP server should raise."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_resp
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.mcp_client.httpx.AsyncClient", return_value=mock_client):
            with patch("orchestrator.mcp_client.get_gcp_identity_token", side_effect=Exception("local")):
                with pytest.raises(httpx.HTTPStatusError):
                    await call_mcp_tool(
                        server_url="http://localhost:8010",
                        method="tools/list"
                    )
