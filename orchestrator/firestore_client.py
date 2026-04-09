from google.cloud import firestore
from datetime import datetime
from typing import Optional, Dict, Any
import os


class FirestoreClient:
    """Collections: workflows, events, contexts"""

    def __init__(self, project_id: str = None):
        if os.getenv('FIRESTORE_EMULATOR_HOST'):
            print("🔧 Using Firestore EMULATOR")
            self.db = firestore.Client(project=project_id or 'test-project')
        else:
            print("☁️  Using Firestore PRODUCTION")
            self.db = firestore.Client(project=project_id)

    async def create_workflow(self, workflow_id: str, data: Dict[str, Any]) -> None:
        workflow_data = {
            **data,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

        self.db.collection('workflows').document(workflow_id).set(workflow_data)
        print(f"📝 Created workflow: {workflow_id}")

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection('workflows').document(workflow_id).get()

        if doc.exists:
            return doc.to_dict()
        return None

    async def update_workflow(self, workflow_id: str, data: Dict[str, Any]) -> None:
        update_data = {
            **data,
            'updatedAt': datetime.utcnow()
        }

        self.db.collection('workflows').document(workflow_id).update(update_data)
        print(f"🔄 Updated workflow: {workflow_id}")

    async def workflow_exists(self, workflow_id: str) -> bool:
        doc = self.db.collection('workflows').document(workflow_id).get()
        return doc.exists

    async def add_event(self, event_data: Dict[str, Any]) -> str:
        event_with_timestamp = {
            **event_data,
            'timestamp': datetime.utcnow().isoformat()
        }

        doc_ref = self.db.collection('events').add(event_with_timestamp)
        return doc_ref[1].id

    async def get_recent_events(self, limit: int = 100) -> list:
        events = (
            self.db.collection('events')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )

        return [event.to_dict() for event in events]

    async def save_context(self, workflow_id: str, messages: list) -> None:
        context_data = {
            'workflowId': workflow_id,
            'messages': messages,
            'lastUpdated': datetime.utcnow(),
            'messageCount': len(messages)
        }

        self.db.collection('contexts').document(workflow_id).set(context_data)
        print(f"💾 Saved context: {workflow_id} ({len(messages)} messages)")

    async def load_context(self, workflow_id: str) -> Optional[list]:
        doc = self.db.collection('contexts').document(workflow_id).get()

        if doc.exists:
            data = doc.to_dict()
            print(f"📂 Loaded context: {workflow_id} ({data.get('messageCount', 0)} messages)")
            return data.get('messages', [])

        return None


def generate_workflow_id(repo: str, branch: str, commit_sha: str) -> str:
    """Deterministic 16-char hex ID for idempotency."""
    import hashlib

    unique_string = f"{repo}:{branch}:{commit_sha}"
    hash_object = hashlib.sha256(unique_string.encode())
    return hash_object.hexdigest()[:16]


_firestore_client = None

def get_firestore_client(project_id: str = None) -> FirestoreClient:
    global _firestore_client

    if _firestore_client is None:
        _firestore_client = FirestoreClient(project_id=project_id)

    return _firestore_client
