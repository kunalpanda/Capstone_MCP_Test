# backend/event_emitter.py
"""
Event Emitter for Orchestrator Dashboard Integration.
Sends structured events to WebSocket server without blocking orchestrator execution.
"""

import httpx
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import time

# Use relative import when running from backend directory
try:
    from backend.event_schemas import (
        create_iteration_start,
        create_claude_response,
        create_tool_call,
        create_tool_result,
        create_state_update,
        create_workflow_start,
        create_workflow_complete,
        create_error,
        create_log,
        LogLevel
    )
except ModuleNotFoundError:
    from event_schemas import (
        create_iteration_start,
        create_claude_response,
        create_tool_call,
        create_tool_result,
        create_state_update,
        create_workflow_start,
        create_workflow_complete,
        create_error,
        create_log,
        LogLevel
    )

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    Non-blocking event emitter that sends structured events to WebSocket server.
    Designed to fail gracefully - won't crash orchestrator if server is down.
    """
    
    def __init__(self, websocket_server_url: str = "http://localhost:8000"):
        """
        Initialize event emitter.
        
        Args:
            websocket_server_url: Base URL of the WebSocket server
        """
        self.server_url = websocket_server_url.rstrip('/')
        self.events_endpoint = f"{self.server_url}/api/events"
        self.enabled = True
        self.total_sent = 0
        self.total_failed = 0
        
        logger.info(f"EventEmitter initialized - target: {self.events_endpoint}")
    
    def enable(self):
        """Enable event emission."""
        self.enabled = True
        logger.info("Event emission enabled")
    
    def disable(self):
        """Disable event emission (useful for testing without dashboard)."""
        self.enabled = False
        logger.info("Event emission disabled")
    
    async def _send_event(self, event: Dict[str, Any]) -> bool:
        """
        Internal method to send event to WebSocket server.
        
        Args:
            event: Fully formatted event dictionary
            
        Returns:
            True if successfully sent, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Use asyncio to send without blocking
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(
                    self.events_endpoint,
                    json=event
                )
                
                if response.status_code == 200:
                    self.total_sent += 1
                    logger.debug(f"Event sent: {event.get('type')}")
                    return True
                else:
                    self.total_failed += 1
                    logger.warning(f"Failed to send event: {response.status_code}")
                    return False
                    
        except httpx.ConnectError:
            # WebSocket server not running - fail silently
            self.total_failed += 1
            logger.debug(f"WebSocket server not available - event {event.get('type')} not sent")
            return False
            
        except Exception as e:
            self.total_failed += 1
            logger.error(f"Error sending event: {e}")
            return False
    
    # ========================================================================
    # Structured Event Methods (Using Schemas)
    # ========================================================================
    
    async def emit_workflow_start(
        self,
        repo_owner: str,
        repo_name: str,
        branch: str,
        max_iterations: int
    ) -> bool:
        """Emit workflow start event."""
        event = create_workflow_start(repo_owner, repo_name, branch, max_iterations)
        return await self._send_event(event)
    
    async def emit_iteration_start(
        self,
        iteration: int,
        max_iterations: int
    ) -> bool:
        """Emit iteration start event."""
        event = create_iteration_start(iteration, max_iterations)
        return await self._send_event(event)
    
    async def emit_claude_response(
        self,
        iteration: int,
        stop_reason: str,
        content: List[Dict[str, Any]]
    ) -> bool:
        """
        Emit Claude response event.
        
        Args:
            iteration: Current iteration number
            stop_reason: Claude's stop reason
            content: Full response content blocks
        """
        event = create_claude_response(iteration, stop_reason, content)
        return await self._send_event(event)
    
    async def emit_tool_call(
        self,
        iteration: int,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: str
    ) -> bool:
        """Emit tool call event."""
        event = create_tool_call(iteration, tool_name, tool_input, tool_use_id)
        return await self._send_event(event)
    
    async def emit_tool_result(
        self,
        iteration: int,
        tool_name: str,
        tool_use_id: str,
        success: bool,
        result: Any,
        error: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> bool:
        """Emit tool execution result event."""
        event = create_tool_result(
            iteration=iteration,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            success=success,
            result=result,
            error=error,
            execution_time_ms=execution_time_ms
        )
        return await self._send_event(event)
    
    async def emit_state_update(self, state_dict: Dict[str, Any]) -> bool:
        """
        Emit workflow state update.
        
        Args:
            state_dict: State dictionary from state.summary()
        """
        event = create_state_update(state_dict)
        return await self._send_event(event)
    
    async def emit_workflow_complete(
        self,
        total_iterations: int,
        success: bool,
        reason: Optional[str] = None
    ) -> bool:
        """Emit workflow completion event."""
        event = create_workflow_complete(total_iterations, success, reason)
        return await self._send_event(event)
    
    async def emit_error(
        self,
        error_type: str,
        error_message: str,
        iteration: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit error event."""
        event = create_error(error_type, error_message, iteration, context)
        return await self._send_event(event)
    
    async def emit_log(
        self,
        level: str,
        message: str,
        iteration: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit log event."""
        log_level = LogLevel(level.lower()) if isinstance(level, str) else level
        event = create_log(log_level, message, iteration, context)
        return await self._send_event(event)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get emission statistics."""
        return {
            "enabled": self.enabled,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "success_rate": (
                f"{(self.total_sent / (self.total_sent + self.total_failed) * 100):.1f}%"
                if (self.total_sent + self.total_failed) > 0
                else "N/A"
            )
        }
    
    def __repr__(self):
        return f"EventEmitter(url={self.server_url}, enabled={self.enabled})"


# ============================================================================
# Global Singleton Instance (Optional)
# ============================================================================

# Create a global emitter instance that can be imported
# Usage: from backend.event_emitter import emitter
emitter = EventEmitter()


# ============================================================================
# Testing Functions
# ============================================================================

async def test_emitter():
    """Test function to verify emitter works with structured events."""
    print("Testing EventEmitter with Structured Events...")
    print("=" * 60)
    
    test_emitter = EventEmitter()
    
    # Test workflow start
    print("\n1. Testing workflow_start event...")
    await test_emitter.emit_workflow_start(
        repo_owner="kunalpanda",
        repo_name="test_banking_app",
        branch="main",
        max_iterations=100
    )
    
    # Test iteration start
    print("2. Testing iteration_start event...")
    await test_emitter.emit_iteration_start(1, 100)
    
    # Test Claude response
    print("3. Testing claude_response event...")
    await test_emitter.emit_claude_response(
        iteration=1,
        stop_reason="tool_use",
        content=[
            {"type": "text", "text": "I'll analyze the failing tests and create fixes."},
            {"type": "tool_use", "id": "test_123", "name": "get_file_content", "input": {}}
        ]
    )
    
    # Test tool call
    print("4. Testing tool_call event...")
    await test_emitter.emit_tool_call(
        iteration=1,
        tool_name="get_file_content",
        tool_input={"owner": "kunalpanda", "repo": "test_banking_app", "path": "web/tests/AccountServiceTest.java"},
        tool_use_id="test_123"
    )
    
    # Test tool result
    print("5. Testing tool_result event...")
    start = time.time()
    await asyncio.sleep(0.1)  # Simulate execution time
    execution_time = int((time.time() - start) * 1000)
    
    await test_emitter.emit_tool_result(
        iteration=1,
        tool_name="get_file_content",
        tool_use_id="test_123",
        success=True,
        result={"content": "public class AccountServiceTest { ... }"},
        execution_time_ms=execution_time
    )
    
    # Test state update
    print("6. Testing state_update event...")
    await test_emitter.emit_state_update({
        "branch": "fix/test-failures",
        "active_branch": "fix/test-failures",
        "iteration": 1,
        "failed_tests": 6,
        "phase": "fixing_tests"
    })
    
    # Test log
    print("7. Testing log event...")
    await test_emitter.emit_log(
        level="info",
        message="Started fixing AccountServiceTest.java",
        iteration=1
    )
    
    # Test error
    print("8. Testing error event...")
    await test_emitter.emit_error(
        error_type="ToolExecutionError",
        error_message="Failed to connect to Jenkins",
        iteration=1,
        context={"tool": "trigger_build", "job_name": "test_banking_app"}
    )
    
    # Test workflow complete
    print("9. Testing workflow_complete event...")
    await test_emitter.emit_workflow_complete(
        total_iterations=1,
        success=True,
        reason="All tests passing"
    )
    
    print("\n" + "=" * 60)
    print("Emitter Statistics:")
    print(json.dumps(test_emitter.get_stats(), indent=2))
    print("=" * 60)
    print("\n✅ Test complete!")
    print("\nCheck your WebSocket server terminal to see the events!")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_emitter())
