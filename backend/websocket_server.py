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

PROJECT_ID = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
EVENTS_TOPIC = os.getenv('PUBSUB_TOPIC_EVENTS', 'workflow-events')
EVENTS_SUBSCRIPTION = os.getenv(
    'PUBSUB_SUBSCRIPTION_EVENTS', 'workflow-events-sub')

print(f"🚀 Event Gateway starting...")
print(f"   Project: {PROJECT_ID}")
print(f"   Events Topic: {EVENTS_TOPIC}")
print(f"   Events Subscription: {EVENTS_SUBSCRIPTION}")

if os.getenv('PUBSUB_EMULATOR_HOST'):
    print(f"🔧 Using Pub/Sub EMULATOR: {os.getenv('PUBSUB_EMULATOR_HOST')}")

if os.getenv('FIRESTORE_EMULATOR_HOST'):
    print(
        f"🔧 Using Firestore EMULATOR: {os.getenv('FIRESTORE_EMULATOR_HOST')}")

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    PROJECT_ID, EVENTS_SUBSCRIPTION)
firestore_client = firestore.Client(project=PROJECT_ID)

# Set during startup, used by the Pub/Sub background thread to schedule coroutines safely.
_main_loop: asyncio.AbstractEventLoop = None


class EventGateway:

    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Also sends recent event history to the newly connected client."""
        await websocket.accept()
        self.connections.add(websocket)

        print(
            f"✅ WebSocket connected. Total connections: {len(self.connections)}")

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
        self.connections.discard(websocket)
        print(
            f"❌ WebSocket disconnected. Total connections: {len(self.connections)}")

    async def broadcast(self, event_data: Dict[str, Any]):
        if not self.connections:
            return

        disconnected = set()

        for connection in self.connections:
            try:
                await connection.send_json(event_data)
            except Exception as e:
                print(f"⚠️  Failed to send to client: {e}")
                disconnected.add(connection)

        for connection in disconnected:
            self.connections.discard(connection)

        if self.connections:
            print(f"📡 Broadcast event to {len(self.connections)} client(s)")

    async def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            events_ref = firestore_client.collection('events')
            query = events_ref.order_by(
                'timestamp', direction=firestore.Query.DESCENDING).limit(limit)

            events = []
            for doc in query.stream():
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)

            events.reverse()

            return events

        except Exception as e:
            print(f"❌ Failed to fetch event history: {e}")
            return []

    async def save_event_to_firestore(self, event_data: Dict[str, Any]) -> str:
        try:
            if 'timestamp' not in event_data:
                event_data['timestamp'] = datetime.utcnow().isoformat()

            doc_ref = firestore_client.collection('events').document()
            doc_ref.set(event_data)

            print(f"💾 Saved event to Firestore: {doc_ref.id}")
            return doc_ref.id

        except Exception as e:
            print(f"❌ Failed to save event: {e}")
            raise


gateway = EventGateway()


def pubsub_callback(message):
    """Runs in a Pub/Sub background thread, NOT the main asyncio loop.
    Uses run_coroutine_threadsafe() to schedule Firestore save + WebSocket
    broadcast on the main loop where the connections live."""
    global _main_loop

    try:
        event_data = json.loads(message.data.decode('utf-8'))
        print(f"📥 Received event: {event_data.get('type', 'unknown')}")

        if _main_loop is None or _main_loop.is_closed():
            print("⚠️  Main event loop not available — saving to Firestore only")
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

        future = asyncio.run_coroutine_threadsafe(
            _process_event(event_data), _main_loop
        )

        future.result(timeout=30)

        message.ack()

    except Exception as e:
        print(f"❌ Error processing event: {e}")
        message.nack()


async def _process_event(event_data: Dict[str, Any]):
    """Scheduled on the main event loop by pubsub_callback."""
    try:
        event_id = await gateway.save_event_to_firestore(event_data)
        await gateway.broadcast(event_data)
        print(f"✅ Event processed: {event_id}")
    except Exception as e:
        print(f"❌ Error in _process_event: {e}")
        raise


def start_pubsub_subscriber():
    try:
        print(f"\n{'='*60}")
        print(f"👂 Starting Pub/Sub subscriber...")
        print(f"   Subscription: {subscription_path}")
        print(f"{'='*60}\n")

        flow_control = pubsub_v1.types.FlowControl(max_messages=10)

        streaming_pull_future = subscriber.subscribe(
            subscription_path,
            callback=pubsub_callback,
            flow_control=flow_control
        )

        print(f"✅ Event subscriber started\n")

        streaming_pull_future.result()

    except Exception as e:
        print(f"❌ Subscriber error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop

    _main_loop = asyncio.get_running_loop()
    print(f"🔄 Main event loop captured: {_main_loop}")

    subscriber_thread = threading.Thread(
        target=start_pubsub_subscriber, daemon=True)
    subscriber_thread.start()
    print("🚀 Background event subscriber started")

    yield

    print("🛑 Shutting down...")
    _main_loop = None


app = FastAPI(title="Event Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await gateway.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()

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
    return {
        "status": "healthy",
        "service": "event-gateway",
        "connections": len(gateway.connections)
    }


@app.get("/events/recent")
async def get_recent_events(limit: int = 50):
    limit = min(limit, 100)
    events = await gateway.get_event_history(limit=limit)

    return {
        "events": events,
        "count": len(events)
    }


@app.get("/")
def root():
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
