# backend/websocket_server.py
"""
WebSocket server for real-time dashboard updates.
Receives events from orchestrator via HTTP POST and broadcasts to connected dashboard clients.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Orchestrator Dashboard WebSocket Server")

# Configure CORS to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections and broadcasts events to all clients."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 1000  # Keep last 1000 events
        
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection and send event history."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Total clients: {len(self.active_connections)}")
        
        # Send event history to newly connected client
        if self.event_history:
            try:
                await websocket.send_json({
                    "type": "history",
                    "events": self.event_history
                })
                logger.info(f"Sent {len(self.event_history)} historical events to new client")
            except Exception as e:
                logger.error(f"Error sending history: {e}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.active_connections)}")
    
    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast event to all connected clients."""
        # Add to history
        self.event_history.append(event)
        
        # Trim history if too large
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Broadcast to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(event)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
        
        logger.info(f"Broadcasted event type '{event.get('type')}' to {len(self.active_connections)} clients")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            "active_connections": len(self.active_connections),
            "total_events": len(self.event_history),
            "max_history": self.max_history
        }


# Initialize connection manager
manager = ConnectionManager()


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard clients.
    Accepts connections and streams events in real-time.
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and listen for client messages (if any)
            data = await websocket.receive_text()
            
            # Handle client messages (ping/pong, etc.)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from client: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# HTTP Endpoints
# ============================================================================

@app.post("/api/events")
async def receive_event(event: Dict[str, Any]):
    """
    Receive events from orchestrator and broadcast to all connected clients.
    
    Expected event format:
    {
        "type": "iteration_start" | "claude_response" | "tool_result" | "state_update",
        "timestamp": "ISO-8601 timestamp",
        "data": { ... event-specific data ... }
    }
    """
    try:
        # Validate event structure
        if "type" not in event:
            raise HTTPException(status_code=400, detail="Event must have 'type' field")
        
        # Add server timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()
        
        # Broadcast to all connected clients
        await manager.broadcast(event)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Event broadcasted",
                "clients_notified": len(manager.active_connections)
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get server status and statistics."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "running",
            "stats": manager.get_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.get("/api/events/history")
async def get_event_history(limit: int = 100):
    """Get recent event history."""
    events = manager.event_history[-limit:] if limit > 0 else manager.event_history
    return JSONResponse(
        status_code=200,
        content={
            "events": events,
            "total": len(manager.event_history),
            "returned": len(events)
        }
    )


@app.delete("/api/events/history")
async def clear_event_history():
    """Clear event history (useful for testing)."""
    count = len(manager.event_history)
    manager.event_history.clear()
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Cleared {count} events from history"
        }
    )


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "service": "Orchestrator Dashboard WebSocket Server",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws",
            "post_event": "/api/events",
            "get_status": "/api/status",
            "get_history": "/api/events/history",
            "clear_history": "/api/events/history (DELETE)"
        },
        "active_connections": len(manager.active_connections)
    }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("=" * 60)
    logger.info("WebSocket Server Starting")
    logger.info("=" * 60)
    logger.info("WebSocket endpoint: ws://localhost:8000/ws")
    logger.info("Event POST endpoint: http://localhost:8000/api/events")
    logger.info("Status endpoint: http://localhost:8000/api/status")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down WebSocket server...")
    
    # Close all active connections
    for connection in manager.active_connections[:]:
        try:
            await connection.close()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    logger.info("WebSocket server shutdown complete")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "websocket_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )
