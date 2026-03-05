# webhook_handler/app.py
"""
Stateless webhook handler that receives GitHub webhooks,
publishes to Pub/Sub, and returns immediately (no blocking).

Does NOT touch Firestore - that's the orchestrator's job.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import pubsub_v1
import json
import hashlib
import os
from datetime import datetime

app = FastAPI(title="Webhook Handler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://frontend-389127668230.us-central1.run.app"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

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
    2. **Filter non-main branches** ← NEW
    3. **Detect [skip ci] tags** ← NEW
    4. Generate workflow ID
    5. Publish to Pub/Sub
    6. Return 202 Accepted immediately

    The orchestrator will handle:
    - Duplicate checking
    - Firestore creation
    - Actual workflow execution

    Returns:
        202 Accepted with workflow ID, or 200 Ignored if filtered
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

        # ============================================
        # FILTER 1: Only 'main' branch triggers
        # ============================================
        if branch != 'main':
            print(
                f"⏭️  Ignoring push to branch '{branch}' (only 'main' triggers workflows)")
            return {
                "status": "ignored",
                "reason": f"Only pushes to 'main' branch trigger workflows. Received: {branch}",
                "branch": branch
            }

        # ============================================
        # FILTER 2: Skip CI detection
        # ============================================
        head_commit = payload.get('head_commit', {})
        if head_commit:
            commit_message = head_commit.get('message', '').lower()
            committer_name = head_commit.get(
                'committer', {}).get('name', '').lower()

            # Check for skip patterns
            skip_patterns = [
                '[skip ci]',
                '[ci skip]',
                '[skip-ci]',
                'fix-tests-',  # Our automated branch names in commit message
            ]

            if any(pattern in commit_message for pattern in skip_patterns):
                print(f"⏭️  Skip CI flag detected in commit message")
                return {
                    "status": "ignored",
                    "reason": "Commit contains [skip ci] flag",
                    "commit_message": head_commit.get('message', '')[:100]
                }

            # Check if it's a GitHub merge commit of our automated PR
            is_github_merge = 'github' in committer_name or 'web-flow' in committer_name
            is_automated_merge = 'automated' in commit_message or 'fix-tests-' in commit_message

            if is_github_merge and is_automated_merge:
                print(f"⏭️  Automated PR merge detected - skipping to prevent loop")
                return {
                    "status": "ignored",
                    "reason": "Merge of automated PR detected",
                    "committer": committer_name
                }

        # ============================================
        # ALL FILTERS PASSED - QUEUE WORKFLOW
        # ============================================

        # Generate workflow ID
        workflow_id = generate_workflow_id(repo, branch, commit_sha)
        print(f"   Workflow ID: {workflow_id}")

        # Extract client_id from header, default for backward compat
        client_id = request.headers.get('X-Client-ID', 'default')

        message_data = {
            'workflowId': workflow_id,
            'repo': repo,
            'branch': branch,
            'commitSha': commit_sha,
            'clientId': client_id,
            'payload': payload,
            'receivedAt': datetime.utcnow().isoformat()
        }

        # Publish to Pub/Sub
        message_bytes = json.dumps(message_data).encode('utf-8')
        future = publisher.publish(topic_path, message_bytes)
        message_id = future.result()  # Wait for publish confirmation

        print(f"📤 Published to Pub/Sub: {message_id}")
        print(f"✅ Workflow queued successfully\n")

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


@app.post("/register")
async def register_client(request: Request):
    """Register a new client and provision their secrets in Secret Manager."""
    import uuid
    from google.cloud import secretmanager

    try:
        body = await request.json()
        github_token = body.get("github_token")
        jenkins_token = body.get("jenkins_token")
        jenkins_url = body.get("jenkins_url")
        jenkins_user = body.get("jenkins_user")

        if not all([github_token, jenkins_token, jenkins_url, jenkins_user]):
            raise HTTPException(
                status_code=400, detail="Missing required fields: github_token, jenkins_token, jenkins_url, jenkins_user")

        client_id = str(uuid.uuid4())[:8]

        sm_client = secretmanager.SecretManagerServiceClient()
        project_path = f"projects/{PROJECT_ID}"

        secrets_to_create = {
            f"client-{client_id}-github-token":  github_token,
            f"client-{client_id}-jenkins-token": jenkins_token,
            f"client-{client_id}-jenkins-url":   jenkins_url,
            f"client-{client_id}-jenkins-user":  jenkins_user,
        }

        for secret_id, value in secrets_to_create.items():
            sm_client.create_secret(request={
                "parent": project_path,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}}
            })
            sm_client.add_secret_version(request={
                "parent": f"{project_path}/secrets/{secret_id}",
                "payload": {"data": value.encode("utf-8")}
            })

        print(f"✅ Registered new client: {client_id}")
        return {
            "client_id": client_id,
            "message": "Client registered. Use X-Client-ID header in webhook calls.",
            "example": f"curl -H 'X-Client-ID: {client_id}' .../webhook/github"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emergency-stop")
async def emergency_stop(request: Request):
    """
    Emergency stop - stops ALL running workflows.

    Sets status='stopped' for every workflow with status='running'.
    """
    try:
        from google.cloud import firestore

        data = await request.json()
        db = firestore.Client(project=PROJECT_ID)

        print(f"\n🛑 EMERGENCY STOP - Stopping ALL running workflows")

        # Get ALL running workflows (no limit)
        try:
            running_workflows = db.collection('workflows')\
                .where('status', '==', 'running')\
                .stream()

            stopped_count = 0
            stopped_ids = []

            # Stop each one
            for workflow_doc in running_workflows:
                workflow_id = workflow_doc.id

                # Set status to stopped
                db.collection('workflows').document(workflow_id).set({
                    'status': 'stopped',
                    'stoppedAt': firestore.SERVER_TIMESTAMP,
                    'stopReason': data.get('reason', 'Emergency stop - all workflows halted')
                }, merge=True)

                stopped_count += 1
                stopped_ids.append(workflow_id)
                print(f"  ✅ Stopped: {workflow_id}")

            if stopped_count == 0:
                print(f"  ⚠️  No running workflows found")
                return {
                    "status": "success",
                    "message": "No running workflows to stop",
                    "stopped_count": 0
                }

            print(f"\n✅ Stopped {stopped_count} workflow(s)\n")

            return {
                "status": "stopped",
                "stopped_count": stopped_count,
                "workflow_ids": stopped_ids,
                "message": f"Emergency stop flag set for {stopped_count} workflow(s). They will halt at next iteration."
            }

        except Exception as query_error:
            print(f"❌ Error querying workflows: {query_error}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query workflows: {query_error}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Emergency stop error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
