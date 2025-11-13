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
    
    async def emit_pr_summary(
        self,
        pr_number: int,
        pr_url: str,
        title: str,
        body: str,
        branch: Optional[str] = None,
        iteration: Optional[int] = None
    ) -> bool:
        """
        Emit PR summary event.
        
        Args:
            pr_number: GitHub PR number
            pr_url: Full URL to PR
            title: PR title
            body: PR description (Claude's summary)
            branch: Branch name
            iteration: Current iteration number
        """
        event = {
            "type": "pr_summary",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "pr_number": pr_number,
                "pr_url": pr_url,
                "title": title,
                "body": body,
                "branch": branch or "unknown",
                "iteration": iteration or 0,
                "body_preview": body[:500] if len(body) > 500 else body
            }
        }
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
# Global Singleton Instance
# ============================================================================

# Create a global emitter instance that can be imported
# Usage: from backend.event_emitter import emitter
emitter = EventEmitter()