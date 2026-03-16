"""
Integration tests for backend.event_schemas and backend.event_emitter.

Tests verify event dataclass serialization, helper function outputs,
and that EventEmitter publishes correctly shaped messages to Pub/Sub.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from backend.event_schemas import (
    EventType,
    LogLevel,
    IterationStartEvent,
    IterationEndEvent,
    ClaudeResponseEvent,
    ToolCallEvent,
    ToolResultEvent,
    StateUpdateEvent,
    WorkflowStartEvent,
    WorkflowCompleteEvent,
    ErrorEvent,
    LogEvent,
    create_iteration_start,
    create_claude_response,
    create_tool_call,
    create_tool_result,
    create_state_update,
    create_workflow_start,
    create_workflow_complete,
    create_error,
    create_log,
)


# =========================================================================
# EventType enum
# =========================================================================
class TestEventTypeEnum:
    def test_all_event_types_are_strings(self):
        for et in EventType:
            assert isinstance(et.value, str)

    def test_expected_types_exist(self):
        names = [et.value for et in EventType]
        assert "iteration_start" in names
        assert "workflow_complete" in names
        assert "tool_call" in names
        assert "error" in names


# =========================================================================
# Dataclass .to_dict() serialization
# =========================================================================
class TestIterationStartEvent:
    def test_to_dict_structure(self):
        evt = IterationStartEvent(iteration=3, max_iterations=50)
        d = evt.to_dict()
        assert d["type"] == EventType.ITERATION_START
        assert d["data"]["iteration"] == 3
        assert d["data"]["max_iterations"] == 50
        assert "progress_percent" in d["data"]
        assert "timestamp" in d

    def test_progress_percent_calculation(self):
        evt = IterationStartEvent(iteration=25, max_iterations=50)
        d = evt.to_dict()
        assert d["data"]["progress_percent"] == 50.0


class TestIterationEndEvent:
    def test_to_dict_includes_stop_reason(self):
        evt = IterationEndEvent(iteration=5, stop_reason="end_turn", duration_seconds=1.2)
        d = evt.to_dict()
        assert d["data"]["stop_reason"] == "end_turn"
        assert d["data"]["duration_seconds"] == 1.2


class TestClaudeResponseEvent:
    def test_to_dict_with_tool_use(self):
        evt = ClaudeResponseEvent(
            iteration=1,
            stop_reason="tool_use",
            text_content="Checking...",
            has_tool_use=True,
            tool_count=2,
        )
        d = evt.to_dict()
        assert d["data"]["has_tool_use"] is True
        assert d["data"]["tool_count"] == 2

    def test_message_preview_auto_generated(self):
        long_text = "A" * 1000
        evt = ClaudeResponseEvent(iteration=1, stop_reason="end_turn", text_content=long_text)
        d = evt.to_dict()
        assert len(d["data"]["message_preview"]) == 500


class TestToolCallEvent:
    def test_to_dict_includes_input_preview(self):
        evt = ToolCallEvent(
            iteration=2,
            tool_name="get_file_tree",
            tool_input={"owner": "o", "repo": "r"},
            tool_use_id="t1",
        )
        d = evt.to_dict()
        assert d["data"]["tool_name"] == "get_file_tree"
        assert "input_preview" in d["data"]


class TestToolResultEvent:
    def test_success_result(self):
        evt = ToolResultEvent(
            iteration=2,
            tool_name="get_file_tree",
            tool_use_id="t1",
            success=True,
            result_summary="5 files found",
        )
        d = evt.to_dict()
        assert d["data"]["success"] is True
        assert d["data"]["error_message"] is None

    def test_error_result(self):
        evt = ToolResultEvent(
            iteration=2,
            tool_name="trigger_build",
            tool_use_id="t2",
            success=False,
            error_message="Jenkins unreachable",
        )
        d = evt.to_dict()
        assert d["data"]["success"] is False
        assert "Jenkins" in d["data"]["error_message"]


class TestStateUpdateEvent:
    def test_to_dict_with_coverage(self):
        evt = StateUpdateEvent(
            branch="fix-123",
            iteration=5,
            phase="generating",
            current_coverage={"line": 72.0, "branch": 60.0},
            target_coverage={"line": 75, "branch": 70},
        )
        d = evt.to_dict()
        assert d["data"]["branch"] == "fix-123"
        assert d["data"]["current_coverage"]["line"] == 72.0


class TestWorkflowStartEvent:
    def test_to_dict(self):
        evt = WorkflowStartEvent(
            repo_owner="kunalpanda",
            repo_name="test_banking_app",
            branch="main",
            max_iterations=50,
        )
        d = evt.to_dict()
        assert d["type"] == EventType.WORKFLOW_START
        assert d["data"]["repo_owner"] == "kunalpanda"


class TestWorkflowCompleteEvent:
    def test_success(self):
        evt = WorkflowCompleteEvent(total_iterations=12, success=True, reason="workflow_complete")
        d = evt.to_dict()
        assert d["data"]["success"] is True
        assert d["data"]["total_iterations"] == 12

    def test_failure(self):
        evt = WorkflowCompleteEvent(total_iterations=50, success=False, reason="max_iterations_reached")
        d = evt.to_dict()
        assert d["data"]["success"] is False


class TestErrorEvent:
    def test_to_dict(self):
        evt = ErrorEvent(
            error_type="RuntimeError",
            error_message="Something broke",
            iteration=7,
            context={"function": "run_workflow"},
        )
        d = evt.to_dict()
        assert d["data"]["error_type"] == "RuntimeError"
        assert d["data"]["iteration"] == 7


class TestLogEvent:
    def test_to_dict(self):
        evt = LogEvent(level=LogLevel.WARNING, message="Slow response", iteration=3)
        d = evt.to_dict()
        assert d["data"]["level"] == "warning"


# =========================================================================
# Helper functions
# =========================================================================
class TestHelperFunctions:
    def test_create_iteration_start(self):
        d = create_iteration_start(1, 50)
        assert d["type"] == EventType.ITERATION_START
        assert d["data"]["iteration"] == 1

    def test_create_claude_response_text_only(self):
        content = [{"type": "text", "text": "Analysis complete."}]
        d = create_claude_response(iteration=1, stop_reason="end_turn", content=content)
        assert d["data"]["has_tool_use"] is False
        assert d["data"]["tool_count"] == 0

    def test_create_claude_response_with_tools(self):
        content = [
            {"type": "text", "text": "Checking..."},
            {"type": "tool_use", "id": "t1", "name": "get_file_tree", "input": {}},
            {"type": "tool_use", "id": "t2", "name": "trigger_build", "input": {}},
        ]
        d = create_claude_response(iteration=2, stop_reason="tool_use", content=content)
        assert d["data"]["has_tool_use"] is True
        assert d["data"]["tool_count"] == 2

    def test_create_tool_call(self):
        d = create_tool_call(3, "trigger_build", {"job_name": "app"}, "t1")
        assert d["data"]["tool_name"] == "trigger_build"

    def test_create_tool_result_success(self):
        d = create_tool_result(3, "trigger_build", "t1", True, {"status": "triggered"})
        assert d["data"]["success"] is True
        assert d["data"]["result_summary"] is not None

    def test_create_tool_result_failure(self):
        d = create_tool_result(3, "trigger_build", "t1", False, None, error="timeout")
        assert d["data"]["success"] is False
        assert d["data"]["error_message"] == "timeout"

    def test_create_state_update(self):
        state_dict = {
            "branch": "fix-1",
            "active_branch": "fix-1",
            "commit": "abc",
            "iteration": 5,
            "phase": "testing",
            "current_coverage": {"line": 70},
            "target_coverage": {"line": 75},
        }
        d = create_state_update(state_dict)
        assert d["data"]["branch"] == "fix-1"

    def test_create_workflow_start(self):
        d = create_workflow_start("kunalpanda", "test_banking_app", "main", 50)
        assert d["data"]["repo_name"] == "test_banking_app"

    def test_create_workflow_complete(self):
        d = create_workflow_complete(12, True, "workflow_complete")
        assert d["data"]["success"] is True

    def test_create_error(self):
        d = create_error("ValueError", "Bad input", iteration=2)
        assert d["data"]["error_type"] == "ValueError"

    def test_create_log(self):
        d = create_log(LogLevel.INFO, "Starting phase 2", iteration=5)
        assert d["data"]["level"] == "info"


# =========================================================================
# EventEmitter (backend.event_emitter)
# =========================================================================
class TestEventEmitter:
    @pytest.fixture
    def mock_publisher(self):
        pub = MagicMock()
        pub.topic_path.return_value = "projects/test/topics/workflow-events"
        future = MagicMock()
        future.result.return_value = "msg-id"
        pub.publish.return_value = future
        return pub

    @pytest.fixture
    def emitter(self, mock_publisher):
        with patch("backend.event_emitter.pubsub_v1.PublisherClient", return_value=mock_publisher):
            from backend.event_emitter import EventEmitter
            e = EventEmitter()
            e.publisher = mock_publisher
            return e

    @pytest.mark.asyncio
    async def test_emit_workflow_start(self, emitter, mock_publisher):
        await emitter.emit_workflow_start(repo_owner="o", repo_name="r", branch="main", max_iterations=50)
        mock_publisher.publish.assert_called_once()
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "workflow_start"
        assert msg["data"]["repo_owner"] == "o"

    @pytest.mark.asyncio
    async def test_emit_iteration_start(self, emitter, mock_publisher):
        await emitter.emit_iteration_start(iteration=3, max_iterations=50)
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "iteration_start"
        assert msg["data"]["iteration"] == 3

    @pytest.mark.asyncio
    async def test_emit_tool_call(self, emitter, mock_publisher):
        await emitter.emit_tool_call(
            iteration=2,
            tool_name="get_file_tree",
            tool_input={"owner": "o"},
            tool_use_id="t1",
        )
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "tool_call"

    @pytest.mark.asyncio
    async def test_emit_error(self, emitter, mock_publisher):
        await emitter.emit_error(
            error_type="RuntimeError",
            error_message="fail",
            context={"fn": "test"},
        )
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "error"

    @pytest.mark.asyncio
    async def test_emit_handles_publish_failure(self, emitter, mock_publisher):
        mock_publisher.publish.side_effect = Exception("PubSub down")
        # Should not raise – just logs
        await emitter.emit_workflow_start(repo_owner="o", repo_name="r", branch="main", max_iterations=50)

    @pytest.mark.asyncio
    async def test_emit_workflow_complete(self, emitter, mock_publisher):
        await emitter.emit_workflow_complete(total_iterations=10, success=True, reason="done")
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "workflow_complete"
        assert msg["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_emit_state_update(self, emitter, mock_publisher):
        await emitter.emit_state_update({"phase": "testing", "branch": "fix-1"})
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "state_update"

    @pytest.mark.asyncio
    async def test_emit_pr_summary(self, emitter, mock_publisher):
        await emitter.emit_pr_summary(
            pr_number=7, pr_url="url", title="Fix tests",
            body="Summary", branch="fix-1", iteration=5
        )
        msg = json.loads(mock_publisher.publish.call_args[0][1])
        assert msg["type"] == "pr_summary"
