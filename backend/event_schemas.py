from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(str, Enum):
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    CLAUDE_RESPONSE = "claude_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    STATE_UPDATE = "state_update"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    ERROR = "error"
    LOG = "log"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class IterationStartEvent:
    iteration: int
    max_iterations: int
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.ITERATION_START,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "iteration": self.iteration,
                "max_iterations": self.max_iterations,
                "progress_percent": round((self.iteration / self.max_iterations) * 100, 1)
            }
        }


@dataclass
class IterationEndEvent:
    iteration: int
    stop_reason: str
    duration_seconds: Optional[float] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.ITERATION_END,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "iteration": self.iteration,
                "stop_reason": self.stop_reason,
                "duration_seconds": self.duration_seconds
            }
        }


@dataclass
class ClaudeResponseEvent:
    iteration: int
    stop_reason: str
    text_content: Optional[str] = None
    has_tool_use: bool = False
    tool_count: int = 0
    message_preview: Optional[str] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.CLAUDE_RESPONSE,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "iteration": self.iteration,
                "stop_reason": self.stop_reason,
                "text_content": self.text_content,
                "has_tool_use": self.has_tool_use,
                "tool_count": self.tool_count,
                "message_preview": self.message_preview or (
                    self.text_content[:500] if self.text_content else None
                )
            }
        }


@dataclass
class ToolCallEvent:
    iteration: int
    tool_name: str
    tool_input: Dict[str, Any]
    tool_use_id: str
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.TOOL_CALL,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "iteration": self.iteration,
                "tool_name": self.tool_name,
                "tool_input": self.tool_input,
                "tool_use_id": self.tool_use_id,
                "input_preview": str(self.tool_input)[:200]
            }
        }


@dataclass
class ToolResultEvent:
    iteration: int
    tool_name: str
    tool_use_id: str
    success: bool
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.TOOL_RESULT,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "iteration": self.iteration,
                "tool_name": self.tool_name,
                "tool_use_id": self.tool_use_id,
                "success": self.success,
                "result_summary": self.result_summary,
                "error_message": self.error_message,
                "execution_time_ms": self.execution_time_ms
            }
        }


@dataclass
class StateUpdateEvent:
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    iteration: Optional[int] = None
    phase: Optional[str] = None
    current_coverage: Optional[Dict[str, float]] = None
    target_coverage: Optional[Dict[str, int]] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.STATE_UPDATE,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "branch": self.branch,
                "commit_sha": self.commit_sha,
                "iteration": self.iteration,
                "phase": self.phase,
                "current_coverage": self.current_coverage,
                "target_coverage": self.target_coverage
            }
        }

@dataclass
class WorkflowStartEvent:
    repo_owner: str
    repo_name: str
    branch: str
    max_iterations: int
    workflow_type: str = "test_repair_and_generation"
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.WORKFLOW_START,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "repo_owner": self.repo_owner,
                "repo_name": self.repo_name,
                "branch": self.branch,
                "max_iterations": self.max_iterations,
                "workflow_type": self.workflow_type
            }
        }


@dataclass
class WorkflowCompleteEvent:
    total_iterations: int
    success: bool
    reason: Optional[str] = None
    tests_fixed: Optional[int] = None
    tests_generated: Optional[int] = None
    files_modified: Optional[int] = None
    duration_seconds: Optional[float] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.WORKFLOW_COMPLETE,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "total_iterations": self.total_iterations,
                "success": self.success,
                "reason": self.reason,
                "summary": {
                    "tests_fixed": self.tests_fixed,
                    "tests_generated": self.tests_generated,
                    "files_modified": self.files_modified
                },
                "duration_seconds": self.duration_seconds
            }
        }


@dataclass
class ErrorEvent:
    error_type: str
    error_message: str
    iteration: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.ERROR,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "error_type": self.error_type,
                "error_message": self.error_message,
                "iteration": self.iteration,
                "context": self.context,
                "stack_trace": self.stack_trace
            }
        }


@dataclass
class LogEvent:
    level: LogLevel
    message: str
    iteration: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": EventType.LOG,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "data": {
                "level": self.level.value,
                "message": self.message,
                "iteration": self.iteration,
                "context": self.context
            }
        }


def create_iteration_start(iteration: int, max_iterations: int) -> Dict[str, Any]:
    event = IterationStartEvent(iteration=iteration, max_iterations=max_iterations)
    return event.to_dict()


def create_claude_response(
    iteration: int,
    stop_reason: str,
    content: List[Dict[str, Any]]
) -> Dict[str, Any]:
    text_content = None
    has_tool_use = False
    tool_count = 0

    for block in content:
        if block.get("type") == "text":
            text_content = block.get("text", "")
        elif block.get("type") == "tool_use":
            has_tool_use = True
            tool_count += 1

    event = ClaudeResponseEvent(
        iteration=iteration,
        stop_reason=stop_reason,
        text_content=text_content,
        has_tool_use=has_tool_use,
        tool_count=tool_count
    )
    return event.to_dict()


def create_tool_call(
    iteration: int,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_use_id: str
) -> Dict[str, Any]:
    event = ToolCallEvent(
        iteration=iteration,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=tool_use_id
    )
    return event.to_dict()


def create_tool_result(
    iteration: int,
    tool_name: str,
    tool_use_id: str,
    success: bool,
    result: Any,
    error: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> Dict[str, Any]:
    result_summary = None
    if success and result:
        result_str = str(result)
        result_summary = result_str[:200] + "..." if len(result_str) > 200 else result_str

    event = ToolResultEvent(
        iteration=iteration,
        tool_name=tool_name,
        tool_use_id=tool_use_id,
        success=success,
        result_summary=result_summary,
        error_message=error,
        execution_time_ms=execution_time_ms
    )
    return event.to_dict()


def create_state_update(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    event = StateUpdateEvent(
        branch=state_dict.get("branch") or state_dict.get("active_branch"),
        commit_sha=state_dict.get("commit"),
        iteration=state_dict.get("iteration"),
        phase=state_dict.get("phase"),
        current_coverage=state_dict.get("current_coverage"),
        target_coverage=state_dict.get("target_coverage")
    )
    return event.to_dict()

def create_workflow_start(
    repo_owner: str,
    repo_name: str,
    branch: str,
    max_iterations: int
) -> Dict[str, Any]:
    event = WorkflowStartEvent(
        repo_owner=repo_owner,
        repo_name=repo_name,
        branch=branch,
        max_iterations=max_iterations
    )
    return event.to_dict()


def create_workflow_complete(
    total_iterations: int,
    success: bool,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    event = WorkflowCompleteEvent(
        total_iterations=total_iterations,
        success=success,
        reason=reason
    )
    return event.to_dict()


def create_error(
    error_type: str,
    error_message: str,
    iteration: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    event = ErrorEvent(
        error_type=error_type,
        error_message=error_message,
        iteration=iteration,
        context=context
    )
    return event.to_dict()


def create_log(
    level: LogLevel,
    message: str,
    iteration: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    event = LogEvent(
        level=level,
        message=message,
        iteration=iteration,
        context=context
    )
    return event.to_dict()
