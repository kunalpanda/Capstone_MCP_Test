# orchestrator_worker/app.py
import os
import json
import base64
import traceback
from fastapi import FastAPI, Request, HTTPException
from google.cloud import firestore
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="Orchestrator Worker")

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "capstone-cicd-ai")
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL")
JENKINS_MCP_URL = os.getenv("JENKINS_MCP_URL")

print("============================================================")
print("🚀 Orchestrator Worker starting...")
print(f"   Project: {PROJECT_ID}")
print(f"   GitHub MCP: {GITHUB_MCP_URL}")
print(f"   Jenkins MCP: {JENKINS_MCP_URL}")
print("============================================================")
print()


def is_workflow_already_running(repo: str) -> bool:
    """
    Check Firestore for any workflow with status 'running' for the given repo.

    Returns True if a workflow is already in progress — the caller should
    drop the new request to prevent concurrent runs.
    """
    try:
        db = firestore.Client(project=PROJECT_ID)
        running = (
            db.collection('workflows')
            .where('status', '==', 'running')
            .where('repo', '==', repo)
            .limit(1)
            .stream()
        )
        for doc in running:
            print(f"🔒 Active workflow found: {doc.id} (repo={repo})")
            return True
        return False
    except Exception as e:
        print(f"⚠️  Error checking running workflows: {e}")
        # Fail open — allow the workflow rather than silently dropping it
        return False


async def run_orchestrator_workflow(workflow_id: str, repo: str, branch: str, commit_sha: str, client_secrets: dict = None):
    """
    Execute the orchestrator workflow for the given parameters.
    Runs SYNCHRONOUSLY - blocks until complete, just like local version.
    """
    # Initialize Firestore FIRST
    firestore_client = firestore.Client(project=PROJECT_ID)

    try:
        # Print INSIDE try block so we can catch early failures
        print()
        print("=" * 60)
        print(f"🚀 Starting workflow: {workflow_id}")
        print(f"   Repo: {repo}")
        print(f"   Branch: {branch}")
        print(f"   Commit: {commit_sha}")
        print(f"   Project: {PROJECT_ID}")
        print("=" * 60)
        print()

        # Use SET with merge=True instead of UPDATE
        # This creates the document if it doesn't exist, updates if it does
        print(f"📝 Setting workflow {workflow_id} to 'running'...")
        firestore_client.collection('workflows').document(workflow_id).set({
            'status': 'running',
            'repo': repo,
            'branch': branch,
            'commitSha': commit_sha,
            'startedAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }, merge=True)
        print(f"✅ Firestore updated successfully")
        print()

        # Import and run the orchestrator
        print(f"🤖 Executing orchestrator for workflow {workflow_id}...")
        print()

        # CRITICAL: Orchestrator uses module-level constants, so we set them here
        import orchestrator.orchestrator as orchestrator_module

        repo_owner = repo.split('/')[0]
        repo_name = repo.split('/')[1]

        orchestrator_module.REPO_OWNER = repo_owner
        orchestrator_module.REPO_NAME = repo_name

        print(f"📝 Configured orchestrator:")
        print(f"   REPO_OWNER: {repo_owner}")
        print(f"   REPO_NAME: {repo_name}")
        print(f"   GITHUB_MCP_URL: {GITHUB_MCP_URL}")
        print(f"   JENKINS_MCP_URL: {JENKINS_MCP_URL}")
        print()

        from orchestrator.orchestrator import run_full_test_repair_and_generation_workflow

        # Build per-client MCP headers from secrets
        github_headers = None
        jenkins_headers = None
        if client_secrets:
            github_headers = {
                "X-GitHub-Token": client_secrets.get("github_token", "")
            }
            jenkins_headers = {
                "X-Jenkins-Token": client_secrets.get("jenkins_token", ""),
                "X-Jenkins-URL":   client_secrets.get("jenkins_url", ""),
                "X-Jenkins-User":  client_secrets.get("jenkins_user", "")
            }
            print(f"🔑 MCP headers configured for client")

        # Run the workflow SYNCHRONOUSLY (blocking) - just like local version
        # This can take 10-120 minutes - everything freezes until complete
        print("⏳ Starting orchestrator execution (this will block)...")
        print(f"   Passing workflow_id: {workflow_id}")
        print(f"   Passing repo: {repo}")
        print(f"   Passing branch: {branch}")
        print(f"   Passing commit_sha: {commit_sha}")
        print()
        result = await run_full_test_repair_and_generation_workflow(
            workflow_id=workflow_id,
            repo=repo,
            branch=branch,
            commit_sha=commit_sha,
            github_headers=github_headers,
            jenkins_headers=jenkins_headers
        )

        # Update status to completed
        print()
        print("📝 Updating Firestore with completion status...")
        firestore_client.collection('workflows').document(workflow_id).set({
            'status': 'completed',
            'completedAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'result': result
        }, merge=True)

        print()
        print("============================================================")
        print(f"✅ Workflow {workflow_id} completed successfully")
        print("============================================================")
        print()

        return result

    except Exception as e:
        error_msg = str(e)
        print()
        print("============================================================")
        print(f"❌ Workflow {workflow_id} failed: {error_msg}")
        print("Full traceback:")
        traceback.print_exc()
        print("============================================================")
        print()

        # Update status to failed
        try:
            firestore_client.collection('workflows').document(workflow_id).set({
                'status': 'failed',
                'error': error_msg,
                'failedAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }, merge=True)
            print(f"📝 Updated Firestore with failure status")
        except Exception as firestore_error:
            print(f"❌ Failed to update Firestore: {firestore_error}")

        raise


@app.post("/pubsub/push")
async def pubsub_push_handler(request: Request):
    """
    Handle Pub/Sub push messages.

    Runs the workflow SYNCHRONOUSLY (blocking) to keep the Cloud Run
    instance alive for the duration of the workflow. Cloud Run timeout
    is 3600s (1 hour).

    ALWAYS returns HTTP 200 to prevent Pub/Sub from redelivering messages.
    On error, the 200 response body contains error details — Pub/Sub only
    cares about the status code, not the body.

    If a workflow is already running for the same repo, the request is
    dropped immediately (returns 200 with status "dropped").
    """
    try:
        # Parse the Pub/Sub message
        envelope = await request.json()

        if 'message' not in envelope:
            # Return 200 even for bad format — don't let Pub/Sub redeliver garbage
            return {"status": "error", "detail": "Invalid Pub/Sub message format"}

        message = envelope['message']

        # Decode the base64-encoded data
        if 'data' not in message:
            return {"status": "error", "detail": "No data in Pub/Sub message"}

        data = base64.b64decode(message['data']).decode('utf-8')
        payload = json.loads(data)

        print()
        print("📥 Received workflow request via Pub/Sub push")
        print(f"   Message ID: {message.get('messageId')}")
        print(f"   Workflow ID: {payload.get('workflowId')}")
        print()

        # Extract workflow parameters
        workflow_id = payload.get('workflowId')
        repo = payload.get('repo')
        branch = payload.get('branch')
        commit_sha = payload.get('commitSha')
        client_id = payload.get('clientId', 'default')

        if not all([workflow_id, repo, branch, commit_sha]):
            return {"status": "error", "detail": "Missing required workflow parameters"}

        # ============================================
        # CONCURRENCY GUARD: Drop if workflow already running
        # ============================================
        if is_workflow_already_running(repo):
            print(f"⏭️  Dropping duplicate — a workflow is already running for {repo}")
            print(f"   Dropped workflow ID: {workflow_id}")
            print()
            return {
                "status": "dropped",
                "reason": f"Workflow already running for {repo}",
                "workflowId": workflow_id
            }

        # Fetch per-client secrets from Secret Manager
        print(f"🔑 Fetching secrets for client_id='{client_id}'...")
        from orchestrator.gcp_config import get_client_secrets
        client_secrets = get_client_secrets(client_id, PROJECT_ID)
        print(f"✅ Secrets fetched for client '{client_id}'")
        print()

        # ============================================
        # RUN WORKFLOW SYNCHRONOUSLY (blocking)
        # ============================================
        # This blocks the HTTP request for the entire workflow duration
        # (10-60+ minutes). Cloud Run keeps the instance alive because
        # the request is still in-flight. Pub/Sub may redeliver after
        # its ack deadline (600s), but the concurrency lock above will
        # drop any duplicates.
        print(f"⏳ Running orchestrator synchronously (blocking)...")
        print(f"   This may take 10-120 minutes...")
        print()

        result = await run_orchestrator_workflow(
            workflow_id, repo, branch, commit_sha, client_secrets
        )

        print(f"✅ Orchestrator completed, returning 200 OK to Pub/Sub")
        print()

        return {
            "status": "completed",
            "workflowId": workflow_id,
            "result": result
        }

    except Exception as e:
        # ============================================
        # ALWAYS return 200 — never let Pub/Sub redeliver
        # ============================================
        # The error is logged above by run_orchestrator_workflow.
        # Returning 500 would cause Pub/Sub to redeliver the message,
        # which is what caused the original cascading trigger disaster.
        print(f"❌ Handler caught exception: {e}")
        traceback.print_exc()
        print(f"⚠️  Returning 200 to prevent Pub/Sub redelivery")
        print()
        return {
            "status": "error",
            "error": str(e),
            "message": "Returning 200 to prevent Pub/Sub redelivery"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "orchestrator-worker",
        "project": PROJECT_ID
    }


@app.get("/test/firestore")
async def test_firestore():
    """Test Firestore connectivity - for debugging."""
    try:
        firestore_client = firestore.Client(project=PROJECT_ID)

        # Create a test document
        test_ref = firestore_client.collection(
            'test').document('connection_test')
        test_ref.set({
            'timestamp': firestore.SERVER_TIMESTAMP,
            'message': 'Connection successful',
            'project': PROJECT_ID
        })

        # Read it back
        doc = test_ref.get()

        return {
            "status": "success",
            "firestore_working": True,
            "project": PROJECT_ID,
            "data": doc.to_dict()
        }
    except Exception as e:
        return {
            "status": "error",
            "firestore_working": False,
            "project": PROJECT_ID,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/test/mcp")
async def test_mcp():
    """Test MCP server connectivity - for debugging."""
    import httpx

    github_url = GITHUB_MCP_URL
    jenkins_url = JENKINS_MCP_URL

    results = {}

    # Test GitHub MCP
    if github_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{github_url}/health")
                results["github_mcp"] = {
                    "url": github_url,
                    "status": resp.status_code,
                    "working": resp.status_code == 200,
                    "response": resp.text[:200] if resp.text else None
                }
        except Exception as e:
            results["github_mcp"] = {
                "url": github_url,
                "error": str(e),
                "working": False
            }
    else:
        results["github_mcp"] = {
            "url": None,
            "error": "GITHUB_MCP_URL not set",
            "working": False
        }

    # Test Jenkins MCP
    if jenkins_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{jenkins_url}/health")
                results["jenkins_mcp"] = {
                    "url": jenkins_url,
                    "status": resp.status_code,
                    "working": resp.status_code == 200,
                    "response": resp.text[:200] if resp.text else None
                }
        except Exception as e:
            results["jenkins_mcp"] = {
                "url": jenkins_url,
                "error": str(e),
                "working": False
            }
    else:
        results["jenkins_mcp"] = {
            "url": None,
            "error": "JENKINS_MCP_URL not set",
            "working": False
        }

    return results


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Orchestrator Worker",
        "status": "running",
        "project": PROJECT_ID,
        "endpoints": {
            "/pubsub/push": "Pub/Sub push endpoint (synchronous, always returns 200)",
            "/health": "Health check",
            "/test/firestore": "Test Firestore connectivity",
            "/test/mcp": "Test MCP server connectivity"
        },
        "config": {
            "github_mcp": GITHUB_MCP_URL,
            "jenkins_mcp": JENKINS_MCP_URL
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8082))
    uvicorn.run(app, host="0.0.0.0", port=port)
