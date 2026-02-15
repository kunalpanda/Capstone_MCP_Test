# orchestrator/firestore_client.py
"""
Firestore client for workflow state management.
"""
from google.cloud import firestore
from datetime import datetime
from typing import Optional, Dict, Any
import os


class FirestoreClient:
    """
    Manages workflow state in Firestore.
    
    Collections:
        - workflows: Main workflow documents
        - events: Event history for dashboard
        - contexts: Claude message history
    """
    
    def __init__(self, project_id: str = None):
        """
        Initialize Firestore client.
        
        Args:
            project_id: GCP project ID (auto-detected if not provided)
        """
        # Check if running in emulator mode
        if os.getenv('FIRESTORE_EMULATOR_HOST'):
            print("🔧 Using Firestore EMULATOR")
            self.db = firestore.Client(project=project_id or 'test-project')
        else:
            print("☁️  Using Firestore PRODUCTION")
            self.db = firestore.Client(project=project_id)
    
    # =====================================================================
    # WORKFLOW OPERATIONS
    # =====================================================================
    
    async def create_workflow(self, workflow_id: str, data: Dict[str, Any]) -> None:
        """
        Create a new workflow document.
        
        Args:
            workflow_id: Unique workflow identifier
            data: Initial workflow data
        """
        workflow_data = {
            **data,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        self.db.collection('workflows').document(workflow_id).set(workflow_data)
        print(f"📝 Created workflow: {workflow_id}")
    
    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow document by ID.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow data or None if not found
        """
        doc = self.db.collection('workflows').document(workflow_id).get()
        
        if doc.exists:
            return doc.to_dict()
        return None
    
    async def update_workflow(self, workflow_id: str, data: Dict[str, Any]) -> None:
        """
        Update workflow document.
        
        Args:
            workflow_id: Workflow identifier
            data: Fields to update
        """
        update_data = {
            **data,
            'updatedAt': datetime.utcnow()
        }
        
        self.db.collection('workflows').document(workflow_id).update(update_data)
        print(f"🔄 Updated workflow: {workflow_id}")
    
    async def workflow_exists(self, workflow_id: str) -> bool:
        """
        Check if workflow exists (for idempotency).
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if workflow exists
        """
        doc = self.db.collection('workflows').document(workflow_id).get()
        return doc.exists
    
    # =====================================================================
    # EVENT OPERATIONS
    # =====================================================================
    
    async def add_event(self, event_data: Dict[str, Any]) -> str:
        """
        Add event to history.
        
        Args:
            event_data: Event data
            
        Returns:
            Event document ID
        """
        event_with_timestamp = {
            **event_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        doc_ref = self.db.collection('events').add(event_with_timestamp)
        return doc_ref[1].id
    
    async def get_recent_events(self, limit: int = 100) -> list:
        """
        Get recent events for dashboard.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        events = (
            self.db.collection('events')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        
        return [event.to_dict() for event in events]
    
    # =====================================================================
    # MODEL CONTEXT OPERATIONS (using Firestore as key-value store)
    # =====================================================================
    
    async def save_context(self, workflow_id: str, messages: list) -> None:
        """
        Save Claude message context for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            messages: List of Claude messages
        """
        context_data = {
            'workflowId': workflow_id,
            'messages': messages,
            'lastUpdated': datetime.utcnow(),
            'messageCount': len(messages)
        }
        
        self.db.collection('contexts').document(workflow_id).set(context_data)
        print(f"💾 Saved context: {workflow_id} ({len(messages)} messages)")
    
    async def load_context(self, workflow_id: str) -> Optional[list]:
        """
        Load Claude message context for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            List of messages or None
        """
        doc = self.db.collection('contexts').document(workflow_id).get()
        
        if doc.exists:
            data = doc.to_dict()
            print(f"📂 Loaded context: {workflow_id} ({data.get('messageCount', 0)} messages)")
            return data.get('messages', [])
        
        return None


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def generate_workflow_id(repo: str, branch: str, commit_sha: str) -> str:
    """
    Generate deterministic workflow ID for idempotency.
    
    Args:
        repo: Repository full name (e.g., "kunalpanda/test_banking_app")
        branch: Branch name
        commit_sha: Commit SHA
        
    Returns:
        16-character hexadecimal ID
    """
    import hashlib
    
    unique_string = f"{repo}:{branch}:{commit_sha}"
    hash_object = hashlib.sha256(unique_string.encode())
    return hash_object.hexdigest()[:16]


# Global client instance (lazy initialization)
_firestore_client = None

def get_firestore_client(project_id: str = None) -> FirestoreClient:
    """Get or create global Firestore client."""
    global _firestore_client
    
    if _firestore_client is None:
        _firestore_client = FirestoreClient(project_id=project_id)
    
    return _firestore_client