# webhook_handler/app.py
"""
Stateless webhook handler that receives GitHub webhooks,
publishes to Pub/Sub, and returns immediately (no blocking).

Does NOT touch Firestore - that's the orchestrator's job.
"""
from fastapi import FastAPI, Request, HTTPException
from google.cloud import pubsub_v1
import json
import hashlib
import os
from datetime import datetime

app = FastAPI(title="Webhook Handler")

# Configuration from environment variables
PROJECT_ID = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
TOPIC_NAME = os.getenv('PUBSUB_TOPIC_COMMANDS', 'workflow-commands')

print(f"🚀 Webhook Handler starting...")
print(f"   Project: {PROJECT_ID}")
print(f"   Topic: {TOPIC_NAME}")

# Initialize Pub/Sub client only (no Firestore!)
if os.getenv('PUBSUB_EMULATOR_HOST'):
    print(f"🔧 Using Pub/Sub EMULATOR: {os.getenv('PUBSUB_EMULATOR_HOST')}")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)


def generate_workflow_id(repo: str, branch: str, commit_sha: str) -> str:
    """
    Generate deterministic workflow ID for idempotency.

    Same algorithm as orchestrator to ensure consistency.

    Args:
        repo: Repository full name (e.g., "kunalpanda/test_banking_app")
        branch: Branch name
        commit_sha: Commit SHA

    Returns:
        16-character hexadecimal ID
    """
    unique_string = f"{repo}:{branch}:{commit_sha}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:16]


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """
    Receive GitHub webhook, validate, publish to Pub/Sub, return immediately.

    Flow:
    1. Parse webhook payload
    2. Generate workflow ID
    3. Publish to Pub/Sub
    4. Return 202 Accepted immediately

    The orchestrator will handle:
    - Duplicate checking
    - Firestore creation
    - Actual workflow execution

    Returns:
        202 Accepted with workflow ID
    """
    try:
        # Parse webhook payload
        payload = await request.json()

        # Extract repository info
        if 'repository' not in payload:
            raise HTTPException(
                status_code=400, detail="Invalid webhook payload: missing repository")

        repo = payload['repository']['full_name']

        # Extract branch from ref (e.g., "refs/heads/main" -> "main")
        ref = payload.get('ref', 'refs/heads/main')
        branch = ref.split('/')[-1] if '/' in ref else ref

        # Extract commit SHA
        commit_sha = payload.get('after', 'unknown')

        print(f"\n📥 Webhook received:")
        print(f"   Repo: {repo}")
        print(f"   Branch: {branch}")
        print(f"   Commit: {commit_sha[:8]}...")

        # Generate workflow ID
        workflow_id = generate_workflow_id(repo, branch, commit_sha)
        print(f"   Workflow ID: {workflow_id}")

        # Create message for Pub/Sub
        message_data = {
            'workflowId': workflow_id,
            'repo': repo,
            'branch': branch,
            'commitSha': commit_sha,
            'payload': payload,  # Include full payload for worker
            'receivedAt': datetime.utcnow().isoformat()
        }

        # Publish to Pub/Sub
        message_bytes = json.dumps(message_data).encode('utf-8')
        future = publisher.publish(topic_path, message_bytes)
        message_id = future.result()  # Wait for publish confirmation

        print(f"📤 Published to Pub/Sub: {message_id}")
        print(f"✅ Webhook processed in <1s\n")

        # Return immediately (no blocking!)
        return {
            "status": "queued",
            "workflowId": workflow_id,
            "messageId": message_id,
            "message": "Workflow queued for processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Webhook processing error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/health")
def health_check():
    """
    Health check endpoint for Cloud Run.

    Cloud Run uses this to determine if the service is healthy.
    """
    return {
        "status": "healthy",
        "service": "webhook-handler",
        "project": PROJECT_ID,
        "topic": TOPIC_NAME
    }


@app.get("/")
def root():
    """
    Root endpoint with service info.
    """
    return {
        "service": "Webhook Handler",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook/github",
            "health": "/health"
        },
        "configuration": {
            "project": PROJECT_ID,
            "topic": TOPIC_NAME
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Run on port 8080 (Cloud Run default)
    port = int(os.getenv('PORT', '8080'))

    print(f"\n{'='*60}")
    print(f"🚀 Starting Webhook Handler on port {port}")
    print(f"{'='*60}\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
