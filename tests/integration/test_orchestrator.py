"""
Integration tests for orchestrator.orchestrator module.

Tests cover: call_claude retry logic, truncate_tool_results,
summarize_old_messages, fetch_all_tools, enforce_branch,
and the main conversation loop with mocked dependencies.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.orchestrator import (
    truncate_tool_results,
    enforce_branch,
)


# =========================================================================
# truncate_tool_results
# =========================================================================
class TestTruncateToolResults:
    def test_short_results_unchanged(self):
        msgs = [
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
            ]}
        ]
        result = truncate_tool_results(msgs)
        assert result[0]["content"][0]["content"] == "ok"

    def test_long_results_truncated(self):
        long_content = "x" * 60_000
        msgs = [
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": long_content}
            ]}
        ]
        result = truncate_tool_results(msgs)
        content = result[0]["content"][0]["content"]
        assert len(content) < 60_000
        assert "[... truncated for length]" in content

    def test_non_tool_result_blocks_preserved(self):
        msgs = [
            {"role": "user", "content": [
                {"type": "text", "text": "hello"},
                {"type": "tool_result", "tool_use_id": "t1", "content": "short"},
            ]}
        ]
        result = truncate_tool_results(msgs)
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["content"] == "short"

    def test_assistant_messages_pass_through(self):
        msgs = [
            {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}
        ]
        result = truncate_tool_results(msgs)
        assert result == msgs

    def test_string_content_in_user_message(self):
        msgs = [{"role": "user", "content": "plain text"}]
        result = truncate_tool_results(msgs)
        assert result == msgs

    def test_custom_max_length(self):
        content = "a" * 200
        msgs = [
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": content}
            ]}
        ]
        result = truncate_tool_results(msgs, max_result_length=100)
        assert len(result[0]["content"][0]["content"]) < 200


# =========================================================================
# enforce_branch
# =========================================================================
class TestEnforceBranch:
    def test_injects_branch_when_empty(self, fresh_state):
        fresh_state.set_branch("fix-123")
        with patch("orchestrator.orchestrator.state", fresh_state):
            params = {"branch": ""}
            result = enforce_branch(params)
            assert result["branch"] == "fix-123"

    def test_injects_ref_when_empty(self, fresh_state):
        fresh_state.set_branch("fix-123")
        with patch("orchestrator.orchestrator.state", fresh_state):
            params = {"ref": ""}
            result = enforce_branch(params)
            assert result["ref"] == "fix-123"

    def test_preserves_explicit_branch(self, fresh_state):
        fresh_state.set_branch("fix-123")
        with patch("orchestrator.orchestrator.state", fresh_state):
            params = {"branch": "custom-branch"}
            result = enforce_branch(params)
            assert result["branch"] == "custom-branch"

    def test_injects_jenkins_branch_parameter(self, fresh_state):
        fresh_state.set_branch("fix-456")
        with patch("orchestrator.orchestrator.state", fresh_state):
            params = {"parameters": {}}
            result = enforce_branch(params)
            assert result["parameters"]["BRANCH"] == "fix-456"

    def test_non_dict_returns_as_is(self):
        assert enforce_branch("not a dict") == "not a dict"
        assert enforce_branch(None) is None


# =========================================================================
# summarize_old_messages
# =========================================================================
class TestSummarizeOldMessages:
    @pytest.mark.asyncio
    async def test_short_conversation_unchanged(self):
        from orchestrator.orchestrator import summarize_old_messages
        msgs = [{"role": "user", "content": f"msg-{i}"} for i in range(5)]
        result = await summarize_old_messages(msgs, keep_recent=3)
        assert len(result) == 5  # Too short to summarize

    @pytest.mark.asyncio
    async def test_long_conversation_is_summarized(self):
        from orchestrator.orchestrator import summarize_old_messages
        msgs = [{"role": "user", "content": f"msg-{i}"} for i in range(20)]
        result = await summarize_old_messages(msgs, keep_recent=3)
        assert len(result) < 20
        # First message preserved
        assert result[0]["content"] == "msg-0"
        # Summary message inserted
        assert "WORKFLOW STATE SUMMARY" in result[1]["content"]


# =========================================================================
# call_claude retry logic
# =========================================================================
class TestCallClaudeRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        from orchestrator.orchestrator import call_claude
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.orchestrator.httpx.AsyncClient", return_value=mock_client):
            result = await call_claude([{"role": "user", "content": "hi"}])
            assert result["stop_reason"] == "end_turn"

    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        from orchestrator.orchestrator import call_claude

        rate_resp = MagicMock()
        rate_resp.status_code = 429
        rate_resp.headers = {"retry-after": "0"}  # No wait for test speed

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"content": [], "stop_reason": "end_turn"}

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return rate_resp if call_count == 1 else ok_resp

        mock_client = AsyncMock()
        mock_client.post = side_effect
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.orchestrator.httpx.AsyncClient", return_value=mock_client):
            with patch("orchestrator.orchestrator.asyncio.sleep", new_callable=AsyncMock):
                result = await call_claude([{"role": "user", "content": "hi"}], max_retries=3)
                assert result["stop_reason"] == "end_turn"
                assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_529(self):
        from orchestrator.orchestrator import call_claude

        overload_resp = MagicMock()
        overload_resp.status_code = 529

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"content": [], "stop_reason": "end_turn"}

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return overload_resp if call_count <= 2 else ok_resp

        mock_client = AsyncMock()
        mock_client.post = side_effect
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("orchestrator.orchestrator.httpx.AsyncClient", return_value=mock_client):
            with patch("orchestrator.orchestrator.asyncio.sleep", new_callable=AsyncMock):
                result = await call_claude([{"role": "user", "content": "hi"}], max_retries=5)
                assert result["stop_reason"] == "end_turn"


# =========================================================================
# fetch_all_tools
# =========================================================================
class TestFetchAllTools:
    @pytest.mark.asyncio
    async def test_fetches_from_both_servers(self):
        from orchestrator.orchestrator import fetch_all_tools

        github_tools = {
            "result": {
                "tools": [
                    {"name": "get_file_tree", "description": "List files", "input_schema": {"type": "object"}}
                ]
            }
        }
        jenkins_tools = {
            "result": {
                "tools": [
                    {"name": "trigger_build", "description": "Trigger", "input_schema": {"type": "object"}}
                ]
            }
        }

        call_count = 0
        async def mock_call(server_url, method, **kwargs):
            nonlocal call_count
            call_count += 1
            if "8010" in server_url:
                return github_tools
            return jenkins_tools

        with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=mock_call):
            tools, mapping = await fetch_all_tools()

        assert len(tools) == 2
        assert "get_file_tree" in mapping
        assert "trigger_build" in mapping

    @pytest.mark.asyncio
    async def test_handles_server_failure_gracefully(self):
        from orchestrator.orchestrator import fetch_all_tools

        async def mock_call(server_url, method, **kwargs):
            if "8010" in server_url:
                raise ConnectionError("GitHub MCP down")
            return {"result": {"tools": [
                {"name": "trigger_build", "description": "t", "input_schema": {"type": "object"}}
            ]}}

        with patch("orchestrator.orchestrator.call_mcp_tool", side_effect=mock_call):
            tools, mapping = await fetch_all_tools()

        # Should still have Jenkins tools
        assert len(tools) == 1
        assert "trigger_build" in mapping


# =========================================================================
# run_conversation_with_tools – single iteration (end_turn)
# =========================================================================
class TestConversationLoop:
    @pytest.mark.asyncio
    async def test_single_text_response_ends(self):
        from orchestrator.orchestrator import run_conversation_with_tools

        claude_resp = {
            "content": [{"type": "text", "text": "Done."}],
            "stop_reason": "end_turn",
        }

        tools = [{"name": "get_file_tree", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"get_file_tree": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.call_claude", new_callable=AsyncMock, return_value=claude_resp):
            with patch("orchestrator.orchestrator.emitter") as mock_emitter:
                mock_emitter.emit_iteration_start = AsyncMock()
                mock_emitter.emit_claude_response = AsyncMock()
                mock_emitter.emit_workflow_complete = AsyncMock()
                mock_emitter.emit_state_update = AsyncMock()
                mock_emitter.emit_tool_call = AsyncMock()
                mock_emitter.emit_tool_result = AsyncMock()

                msgs = await run_conversation_with_tools(
                    "Test prompt",
                    max_iterations=5,
                    tools=tools,
                    tool_to_server=tool_map,
                )

        # Should have initial user message + assistant response
        assert len(msgs) >= 2
        assert msgs[-1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_tool_use_then_end(self):
        """Claude requests a tool, gets result, then ends."""
        from orchestrator.orchestrator import run_conversation_with_tools

        tool_resp = {
            "content": [
                {"type": "text", "text": "Checking files..."},
                {"type": "tool_use", "id": "t1", "name": "get_file_tree",
                 "input": {"owner": "o", "repo": "r", "ref": "main"}},
            ],
            "stop_reason": "tool_use",
        }
        end_resp = {
            "content": [{"type": "text", "text": "All done."}],
            "stop_reason": "end_turn",
        }

        call_count = 0
        async def mock_claude(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else end_resp

        mcp_result = {"result": {"ref": "main", "count": 5, "files": ["a.py"]}}

        tools = [{"name": "get_file_tree", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"get_file_tree": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.call_claude", side_effect=mock_claude):
            with patch("orchestrator.orchestrator.call_mcp_tool", new_callable=AsyncMock, return_value=mcp_result):
                with patch("orchestrator.orchestrator.emitter") as mock_emitter:
                    mock_emitter.emit_iteration_start = AsyncMock()
                    mock_emitter.emit_claude_response = AsyncMock()
                    mock_emitter.emit_workflow_complete = AsyncMock()
                    mock_emitter.emit_state_update = AsyncMock()
                    mock_emitter.emit_tool_call = AsyncMock()
                    mock_emitter.emit_tool_result = AsyncMock()

                    msgs = await run_conversation_with_tools(
                        "Test",
                        max_iterations=5,
                        tools=tools,
                        tool_to_server=tool_map,
                    )

        assert call_count == 2
        # Tool result was sent back
        tool_result_msgs = [
            m for m in msgs
            if m["role"] == "user" and isinstance(m["content"], list)
        ]
        assert len(tool_result_msgs) >= 1

    @pytest.mark.asyncio
    async def test_emergency_stop_halts_loop(self):
        """When Firestore shows status='stopped', loop exits early."""
        from orchestrator.orchestrator import run_conversation_with_tools

        mock_fc = AsyncMock()
        mock_fc.get_workflow = AsyncMock(return_value={"status": "stopped", "stopReason": "test"})
        mock_fc.update_workflow = AsyncMock()
        mock_fc.save_context = AsyncMock()

        tools = [{"name": "get_file_tree", "description": "t", "input_schema": {"type": "object"}}]
        tool_map = {"get_file_tree": "http://localhost:8010"}

        with patch("orchestrator.orchestrator.emitter") as mock_emitter:
            mock_emitter.emit_iteration_start = AsyncMock()
            mock_emitter.emit_workflow_complete = AsyncMock()
            mock_emitter.emit_state_update = AsyncMock()

            result = await run_conversation_with_tools(
                "Test",
                max_iterations=50,
                tools=tools,
                tool_to_server=tool_map,
                workflow_id="wf-stop",
                firestore_client=mock_fc,
            )

        assert isinstance(result, dict)
        assert result["status"] == "stopped"
