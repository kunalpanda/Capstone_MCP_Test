# backend/websocket_server.py
"""
Event Gateway: WebSocket server for real-time dashboard updates.

This service:
1. Subscribes to Pub/Sub workflow-events topic
2. Persists events to Firestore
3. Broadcasts events to connected WebSocket clients
4. Serves event history from Firestore
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Set, Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import pubsub_v1, firestore
from contextlib import asynccontextmanager
import uvicorn
import threading

# ======================================
# Configuration
# ======================================
PROJECT_ID = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
EVENTS_TOPIC = os.getenv('PUBSUB_TOPIC_EVENTS', 'workflow-events')
EVENTS_SUBSCRIPTION = os.getenv(
    'PUBSUB_SUBSCRIPTION_EVENTS', 'workflow-events-sub')

print(f"🚀 Event Gateway starting...")
print(f"   Project: {PROJECT_ID}")
print(f"   Events Topic: {EVENTS_TOPIC}")
print(f"   Events Subscription: {EVENTS_SUBSCRIPTION}")

# Check if using emulators
if os.getenv('PUBSUB_EMULATOR_HOST'):
    print(f"🔧 Using Pub/Sub EMULATOR: {os.getenv('PUBSUB_EMULATOR_HOST')}")

if os.getenv('FIRESTORE_EMULATOR_HOST'):
    print(
        f"🔧 Using Firestore EMULATOR: {os.getenv('FIRESTORE_EMULATOR_HOST')}")

# Initialize clients
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    PROJECT_ID, EVENTS_SUBSCRIPTION)
firestore_client = firestore.Client(project=PROJECT_ID)

# Reference to the main asyncio event loop — set during startup,
# used by the Pub/Sub background thread to schedule coroutines safely.
_main_loop: asyncio.AbstractEventLoop = None


# ======================================
# Event Gateway
# ======================================

class EventGateway:
    """Manages WebSocket connections and event broadcasting."""

    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """
        Handle new WebSocket connection.

        Sends recent event history to newly connected client.
        """
        await websocket.accept()
        self.connections.add(websocket)

        print(
            f"✅ WebSocket connected. Total connections: {len(self.connections)}")

        # Send recent event history to new client
        try:
            history = await self.get_event_history(limit=50)
            await websocket.send_json({
                "type": "history",
                "events": history
            })
            print(f"📤 Sent {len(history)} historical events to new client")
        except Exception as e:
            print(f"⚠️  Failed to send history: {e}")

    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket."""
        self.connections.discard(websocket)
        print(
            f"❌ WebSocket disconnected. Total connections: {len(self.connections)}")

    async def broadcast(self, event_data: Dict[str, Any]):
        """
        Broadcast event to all connected clients.

        Args:
            event_data: Event data to broadcast
        """
        if not self.connections:
            return

        disconnected = set()

        for connection in self.connections:
            try:
                await connection.send_json(event_data)
            except Exception as e:
                print(f"⚠️  Failed to send to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.connections.discard(connection)

        if self.connections:
            print(f"📡 Broadcast event to {len(self.connections)} client(s)")

    async def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch recent events from Firestore.

        Args:
            limit: Maximum number of events to fetch

        Returns:
            List of recent events
        """
        try:
            # Query events ordered by timestamp (most recent first)
            events_ref = firestore_client.collection('events')
            query = events_ref.order_by(
                'timestamp', direction=firestore.Query.DESCENDING).limit(limit)

            events = []
            for doc in query.stream():
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)

            # Reverse to get chronological order (oldest first)
            events.reverse()

            return events

        except Exception as e:
            print(f"❌ Failed to fetch event history: {e}")
            return []

    async def save_event_to_firestore(self, event_data: Dict[str, Any]) -> str:
        """
        Persist event to Firestore.

        Args:
            event_data: Event data to persist

        Returns:
            Event document ID
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in event_data:
                event_data['timestamp'] = datetime.utcnow().isoformat()

            # Create event document
            doc_ref = firestore_client.collection('events').document()
            doc_ref.set(event_data)

            print(f"💾 Saved event to Firestore: {doc_ref.id}")
            return doc_ref.id

        except Exception as e:
            print(f"❌ Failed to save event: {e}")
            raise


# Global gateway instance
gateway = EventGateway()


# ======================================
# Pub/Sub Callback (runs in background thread)
# ======================================

def pubsub_callback(message):
    """
    Callback for Pub/Sub messages.

    Persists event to Firestore and broadcasts to WebSocket clients.

    IMPORTANT: This runs in a Pub/Sub background thread, NOT on the
    main asyncio event loop. We use asyncio.run_coroutine_threadsafe()
    to safely schedule async work (Firestore save + WebSocket broadcast)
    on the main loop where the WebSocket connections live.
    """
    global _main_loop

    try:
        # Parse event data
        event_data = json.loads(message.data.decode('utf-8'))
        print(f"📥 Received event: {event_data.get('type', 'unknown')}")

        if _main_loop is None or _main_loop.is_closed():
            print("⚠️  Main event loop not available — saving to Firestore only")
            # Fallback: save synchronously without broadcast
            try:
                if 'timestamp' not in event_data:
                    event_data['timestamp'] = datetime.utcnow().isoformat()
                doc_ref = firestore_client.collection('events').document()
                doc_ref.set(event_data)
                print(f"💾 Saved event to Firestore (fallback): {doc_ref.id}")
            except Exception as e:
                print(f"❌ Fallback Firestore save failed: {e}")
            message.ack()
            return

        # Schedule the async save + broadcast on the MAIN event loop.
        # This avoids the "bound to a different event loop" error.
        future = asyncio.run_coroutine_threadsafe(
            _process_event(event_data), _main_loop
        )

        # Wait for completion (with timeout) so we can ack/nack properly
        future.result(timeout=30)

        message.ack()

    except Exception as e:
        print(f"❌ Error processing event: {e}")
        message.nack()


async def _process_event(event_data: Dict[str, Any]):
    """
    Save event to Firestore and broadcast to WebSocket clients.

    Runs on the main asyncio event loop (scheduled by pubsub_callback).
    """
    try:
        event_id = await gateway.save_event_to_firestore(event_data)
        await gateway.broadcast(event_data)
        print(f"✅ Event processed: {event_id}")
    except Exception as e:
        print(f"❌ Error in _process_event: {e}")
        raise


def start_pubsub_subscriber():
    """
    Start Pub/Sub subscriber in background thread.
    """
    try:
        print(f"\n{'='*60}")
        print(f"👂 Starting Pub/Sub subscriber...")
        print(f"   Subscription: {subscription_path}")
        print(f"{'='*60}\n")

        # Configure flow control
        flow_control = pubsub_v1.types.FlowControl(max_messages=10)

        # Start streaming pull
        streaming_pull_future = subscriber.subscribe(
            subscription_path,
            callback=pubsub_callback,
            flow_control=flow_control
        )

        print(f"✅ Event subscriber started\n")

        # Block until cancelled
        streaming_pull_future.result()

    except Exception as e:
        print(f"❌ Subscriber error: {e}")


# ======================================
# Lifespan (replaces deprecated @app.on_event)
# ======================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown."""
    global _main_loop

    # Capture the main event loop BEFORE starting the subscriber thread.
    _main_loop = asyncio.get_running_loop()
    print(f"🔄 Main event loop captured: {_main_loop}")

    # Start Pub/Sub subscriber in a daemon thread
    subscriber_thread = threading.Thread(
        target=start_pubsub_subscriber, daemon=True)
    subscriber_thread.start()
    print("🚀 Background event subscriber started")

    yield  # App runs here

    # Shutdown
    print("🛑 Shutting down...")
    _main_loop = None


# ======================================
# FastAPI App
# ======================================

app = FastAPI(title="Event Gateway", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard connections.
    """
    await gateway.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()

            # Echo back for debugging
            await websocket.send_json({
                "type": "echo",
                "message": f"Received: {data}"
            })

    except WebSocketDisconnect:
        gateway.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        gateway.disconnect(websocket)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "event-gateway",
        "connections": len(gateway.connections)
    }


@app.get("/events/recent")
async def get_recent_events(limit: int = 50):
    """
    REST endpoint to get recent events.

    Args:
        limit: Maximum number of events (default 50, max 100)
    """
    limit = min(limit, 100)  # Cap at 100
    events = await gateway.get_event_history(limit=limit)

    return {
        "events": events,
        "count": len(events)
    }


@app.get("/")
def root():
    """Root endpoint with service info."""
    return {
        "service": "Event Gateway",
        "version": "2.1.0",
        "description": "Real-time event broadcasting with Firestore persistence",
        "websocket": "/ws",
        "endpoints": {
            "health": "/health",
            "recent_events": "/events/recent?limit=50"
        },
        "active_connections": len(gateway.connections)
    }


if __name__ == "__main__":
    port = int(os.getenv('PORT', '8000'))

    print(f"\n{'='*60}")
    print(f"🚀 Starting Event Gateway on port {port}")
    print(f"{'='*60}\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
