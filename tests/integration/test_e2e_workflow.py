"""
End-to-end integration tests for the full workflow pipeline.

These tests exercise the complete flow: webhook → Pub/Sub → orchestrator worker
→ orchestrator → MCP servers → Claude, all with mocked external dependencies.
"""
import json
import base64
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# =========================================================================
# Webhook → workflow ID generation → Pub/Sub publish
# =========================================================================
class TestWebhookToWorkflowPipeline:
    """Verify the webhook correctly computes workflow ID and publishes."""

    def test_full_webhook_flow(self):
        mock_publisher = MagicMock()
        mock_publisher.topic_path.return_value = "projects/test/topics/wc"
        future = MagicMock()
        future.result.return_value = "msg-001"
        mock_publisher.publish.return_value = future

        with patch("google.cloud.pubsub_v1.PublisherClient", return_value=mock_publisher):
            import importlib
            import webhook_handler.app as mod
            importlib.reload(mod)
            mod.publisher = mock_publisher
            mod.topic_path = "projects/test/topics/wc"

            from fastapi.testclient import TestClient
            client = TestClient(mod.app)

            payload = {
                "ref": "refs/heads/main",
                "after": "deadbeef",
                "repository": {
                    "full_name": "kunalpanda/test_banking_app",
                    "name": "test_banking_app",
                    "owner": {"login": "kunalpanda"},
                },
                "head_commit": {
                    "message": "Add new feature",
                    "committer": {"name": "Dev"},
                },
            }
            resp = client.post("/webhook/github", json=payload)
            assert resp.status_code == 200

            # Verify Pub/Sub was called
            mock_publisher.publish.assert_called_once()
            published_bytes = mock_publisher.publish.call_args[0][1]
            published = json.loads(published_bytes)
            assert published["workflowId"] == resp.json()["workflowId"]
            assert published["repo"] == "kunalpanda/test_banking_app"
            assert published["branch"] == "main"
            assert published["commitSha"] == "deadbeef"


# =========================================================================
# Orchestrator tool routing
# =========================================================================
class TestToolRouting:
    """Verify that tools are routed to the correct MCP server."""

    @pytest.mark.asyncio
    async def test_github_tools_route_to_github_server(self):
        from orchestrator.orchestrator import run_conversation_with_tools

        routed_urls = []

        async def track_mcp_call(server_url, method, name=None, params=None, headers=None):
            routed_urls.append((name, server_url))
            return {"result": {"ref": "main", "files": ["a.py"], "count": 1}}

        tool_resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "get_file_tree",
                 "input": {"owner": "o", "repo": "r", "ref": "main"}},
            ],
            "stop_reason": "tool_use",
        }
        end_resp = {
            "content": [{"type": "text", "text": "Done"}],
            "stop_reason": "end_turn",
        }

        call_count = 0
        async def mock_claude(*a, **kw):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else end_resp

        tools = [{"name": "get_file_tree", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"get_file_tree": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=mock_claude):
            with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=track_mcp_call):
                with patch("orchestrator.orchestrator.emitter") as me:
                    me.emit_iteration_start = AsyncMock()
                    me.emit_claude_response = AsyncMock()
                    me.emit_workflow_complete = AsyncMock()
                    me.emit_state_update = AsyncMock()
                    me.emit_tool_call = AsyncMock()
                    me.emit_tool_result = AsyncMock()

                    await run_conversation_with_tools("Test", max_iterations=3, tools=tools, tool_to_server=tool_map)

        assert any(name == "get_file_tree" and "8010" in url for name, url in routed_urls)

    @pytest.mark.asyncio
    async def test_jenkins_tools_route_to_jenkins_server(self):
        from orchestrator.orchestrator import run_conversation_with_tools

        routed_urls = []

        async def track_mcp_call(server_url, method, name=None, params=None, headers=None):
            routed_urls.append((name, server_url))
            return {"result": {"status": "triggered", "build_number": 1}}

        tool_resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "trigger_build",
                 "input": {"job_name": "test_banking_app"}},
            ],
            "stop_reason": "tool_use",
        }
        end_resp = {
            "content": [{"type": "text", "text": "Done"}],
            "stop_reason": "end_turn",
        }

        call_count = 0
        async def mock_claude(*a, **kw):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else end_resp

        tools = [{"name": "trigger_build", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"trigger_build": "http://localhost:8020"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=mock_claude):
            with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=track_mcp_call):
                with patch("orchestrator.orchestrator.emitter") as me:
                    me.emit_iteration_start = AsyncMock()
                    me.emit_claude_response = AsyncMock()
                    me.emit_workflow_complete = AsyncMock()
                    me.emit_state_update = AsyncMock()
                    me.emit_tool_call = AsyncMock()
                    me.emit_tool_result = AsyncMock()

                    await run_conversation_with_tools("Test", max_iterations=3, tools=tools, tool_to_server=tool_map)

        assert any(name == "trigger_build" and "8020" in url for name, url in routed_urls)


# =========================================================================
# Branch tracking through tool responses
# =========================================================================
class TestBranchTrackingE2E:
    """Verify state.branch is updated when create_branch tool succeeds."""

    @pytest.mark.asyncio
    async def test_branch_tracked_after_create(self):
        from orchestrator.orchestrator import run_conversation_with_tools
        from orchestrator import orchestrator as orch_mod

        original_branch = orch_mod.state.branch

        tool_resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "create_branch",
                 "input": {"owner": "o", "repo": "r", "branch_name": "fix-tests-42"}},
            ],
            "stop_reason": "tool_use",
        }
        end_resp = {
            "content": [{"type": "text", "text": "Done"}],
            "stop_reason": "end_turn",
        }

        call_count = 0
        async def mock_claude(*a, **kw):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else end_resp

        async def mock_mcp(server_url, method, name=None, params=None, headers=None):
            return {"result": {"branch_name": "fix-tests-42", "sha": "abc"}}

        tools = [{"name": "create_branch", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"create_branch": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=mock_claude):
            with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=mock_mcp):
                with patch("orchestrator.orchestrator.emitter") as me:
                    me.emit_iteration_start = AsyncMock()
                    me.emit_claude_response = AsyncMock()
                    me.emit_workflow_complete = AsyncMock()
                    me.emit_state_update = AsyncMock()
                    me.emit_tool_call = AsyncMock()
                    me.emit_tool_result = AsyncMock()

                    await run_conversation_with_tools("Test", max_iterations=3, tools=tools, tool_to_server=tool_map)

        assert orch_mod.state.branch == "fix-tests-42"
        # Restore
        orch_mod.state.branch = original_branch


# =========================================================================
# Coverage tracking through tool responses
# =========================================================================
class TestCoverageTrackingE2E:
    """Verify coverage state is updated when get_coverage_report returns data."""

    @pytest.mark.asyncio
    async def test_coverage_updated_from_tool_result(self):
        from orchestrator.orchestrator import run_conversation_with_tools
        from orchestrator import orchestrator as orch_mod

        tool_resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "get_coverage_report",
                 "input": {"job_name": "test_banking_app"}},
            ],
            "stop_reason": "tool_use",
        }
        end_resp = {
            "content": [{"type": "text", "text": "Done"}],
            "stop_reason": "end_turn",
        }

        call_count = 0
        async def mock_claude(*a, **kw):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else end_resp

        async def mock_mcp(server_url, method, name=None, params=None, headers=None):
            return {
                "result": {
                    "coverage_available": True,
                    "coverage": {"line": 82.0, "branch": 71.0, "method": 88.0},
                }
            }

        tools = [{"name": "get_coverage_report", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"get_coverage_report": "http://localhost:8020"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=mock_claude):
            with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=mock_mcp):
                with patch("orchestrator.orchestrator.emitter") as me:
                    me.emit_iteration_start = AsyncMock()
                    me.emit_claude_response = AsyncMock()
                    me.emit_workflow_complete = AsyncMock()
                    me.emit_state_update = AsyncMock()
                    me.emit_tool_call = AsyncMock()
                    me.emit_tool_result = AsyncMock()

                    await run_conversation_with_tools("Test", max_iterations=3, tools=tools, tool_to_server=tool_map)

        assert orch_mod.state.current_coverage["line"] == 82.0
        assert orch_mod.state.current_coverage["branch"] == 71.0


# =========================================================================
# PR tracking
# =========================================================================
class TestPRTrackingE2E:
    @pytest.mark.asyncio
    async def test_pr_number_tracked(self):
        from orchestrator.orchestrator import run_conversation_with_tools
        from orchestrator import orchestrator as orch_mod

        tool_resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "create_pull_request",
                 "input": {"owner": "o", "repo": "r", "title": "Fix", "body": "b", "head": "fix-1"}},
            ],
            "stop_reason": "tool_use",
        }
        end_resp = {
            "content": [{"type": "text", "text": "Done"}],
            "stop_reason": "end_turn",
        }

        call_count = 0
        async def mock_claude(*a, **kw):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else end_resp

        async def mock_mcp(server_url, method, name=None, params=None, headers=None):
            return {"result": {"number": 42, "title": "Fix", "url": "u"}}

        tools = [{"name": "create_pull_request", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"create_pull_request": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=mock_claude):
            with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=mock_mcp):
                with patch("orchestrator.orchestrator.emitter") as me:
                    me.emit_iteration_start = AsyncMock()
                    me.emit_claude_response = AsyncMock()
                    me.emit_workflow_complete = AsyncMock()
                    me.emit_state_update = AsyncMock()
                    me.emit_tool_call = AsyncMock()
                    me.emit_tool_result = AsyncMock()

                    await run_conversation_with_tools("Test", max_iterations=3, tools=tools, tool_to_server=tool_map)

        assert orch_mod.state.pr_number == 42


# =========================================================================
# Max iterations safety
# =========================================================================
class TestMaxIterationsSafety:
    @pytest.mark.asyncio
    async def test_loop_stops_at_max_iterations(self):
        from orchestrator.orchestrator import run_conversation_with_tools

        # Claude always requests more tools – loop should stop at max
        tool_resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "get_file_tree",
                 "input": {"owner": "o", "repo": "r"}},
            ],
            "stop_reason": "tool_use",
        }

        async def always_tool(*a, **kw):
            return tool_resp

        async def mock_mcp(*a, **kw):
            return {"result": {"files": []}}

        tools = [{"name": "get_file_tree", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"get_file_tree": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=always_tool):
            with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=mock_mcp):
                with patch("orchestrator.orchestrator.emitter") as me:
                    me.emit_iteration_start = AsyncMock()
                    me.emit_claude_response = AsyncMock()
                    me.emit_workflow_complete = AsyncMock()
                    me.emit_state_update = AsyncMock()
                    me.emit_tool_call = AsyncMock()
                    me.emit_tool_result = AsyncMock()

                    msgs = await run_conversation_with_tools(
                        "Test", max_iterations=3, tools=tools, tool_to_server=tool_map
                    )

        # Should have run exactly 3 iterations
        assert me.emit_iteration_start.await_count == 3
