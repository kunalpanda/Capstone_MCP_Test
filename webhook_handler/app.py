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
    allow_methods=["POST", "GET", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)

PROJECT_ID = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
TOPIC_NAME = os.getenv('PUBSUB_TOPIC_COMMANDS', 'workflow-commands')

print(f"🚀 Webhook Handler starting...")
print(f"   Project: {PROJECT_ID}")
print(f"   Topic: {TOPIC_NAME}")

if os.getenv('PUBSUB_EMULATOR_HOST'):
    print(f"🔧 Using Pub/Sub EMULATOR: {os.getenv('PUBSUB_EMULATOR_HOST')}")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)


def generate_workflow_id(repo: str, branch: str, commit_sha: str) -> str:
    unique_string = f"{repo}:{branch}:{commit_sha}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:16]


@app.post("/webhook/github")
async def github_webhook(request: Request):
    try:
        payload = await request.json()

        if 'repository' not in payload:
            raise HTTPException(
                status_code=400, detail="Invalid webhook payload: missing repository")

        repo = payload['repository']['full_name']
        ref = payload.get('ref', 'refs/heads/main')
        branch = ref.split('/')[-1] if '/' in ref else ref
        commit_sha = payload.get('after', 'unknown')

        print(f"\n📥 Webhook received: {repo} / {branch} / {commit_sha[:8]}")

        if branch != 'main':
            print(f"⏭️  Ignoring push to branch '{branch}'")
            return {"status": "ignored", "reason": f"Only pushes to 'main' branch trigger workflows. Received: {branch}", "branch": branch}

        head_commit = payload.get('head_commit', {})
        if head_commit:
            commit_message = head_commit.get('message', '').lower()
            committer_name = head_commit.get(
                'committer', {}).get('name', '').lower()

            skip_patterns = ['[skip ci]', '[ci skip]',
                             '[skip-ci]', 'fix-tests-']
            if any(pattern in commit_message for pattern in skip_patterns):
                print(f"⏭️  Skip CI flag detected")
                return {"status": "ignored", "reason": "Commit contains [skip ci] flag"}

            is_github_merge = 'github' in committer_name or 'web-flow' in committer_name
            is_automated_merge = 'automated' in commit_message or 'fix-tests-' in commit_message
            if is_github_merge and is_automated_merge:
                print(f"⏭️  Automated PR merge detected - skipping to prevent loop")
                return {"status": "ignored", "reason": "Merge of automated PR detected"}

        workflow_id = generate_workflow_id(repo, branch, commit_sha)
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

        message_bytes = json.dumps(message_data).encode('utf-8')
        future = publisher.publish(topic_path, message_bytes)
        message_id = future.result()

        print(f"✅ Workflow queued: {workflow_id}")
        return {"status": "queued", "workflowId": workflow_id, "messageId": message_id, "message": "Workflow queued for processing"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Webhook processing error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/register")
async def register_client(request: Request):
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
                status_code=400, detail="Missing required fields")

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
            sm_client.create_secret(request={"parent": project_path, "secret_id": secret_id, "secret": {
                                    "replication": {"automatic": {}}}})
            sm_client.add_secret_version(request={
                                         "parent": f"{project_path}/secrets/{secret_id}", "payload": {"data": value.encode("utf-8")}})

        print(f"✅ Registered new client: {client_id}")
        return {"client_id": client_id, "message": "Client registered.", "example": f"curl -H 'X-Client-ID: {client_id}' .../webhook/github"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emergency-stop")
async def emergency_stop(request: Request):
    try:
        from google.cloud import firestore
        data = await request.json()
        db = firestore.Client(project=PROJECT_ID)

        print(f"\n🛑 EMERGENCY STOP")
        running_workflows = db.collection('workflows').where(
            'status', '==', 'running').stream()

        stopped_count = 0
        stopped_ids = []
        for workflow_doc in running_workflows:
            workflow_id = workflow_doc.id
            db.collection('workflows').document(workflow_id).set({
                'status': 'stopped',
                'stoppedAt': firestore.SERVER_TIMESTAMP,
                'stopReason': data.get('reason', 'Emergency stop')
            }, merge=True)
            stopped_count += 1
            stopped_ids.append(workflow_id)
            print(f"  ✅ Stopped: {workflow_id}")

        if stopped_count == 0:
            return {"status": "success", "message": "No running workflows to stop", "stopped_count": 0}

        return {"status": "stopped", "stopped_count": stopped_count, "workflow_ids": stopped_ids}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


CLIENT_ID = "default"


def _sm_client():
    from google.cloud import secretmanager
    return secretmanager.SecretManagerServiceClient()


def _secret_name(key: str) -> str:
    return f"projects/{PROJECT_ID}/secrets/client-{CLIENT_ID}-{key}"


def _secret_version_name(key: str) -> str:
    return f"{_secret_name(key)}/versions/latest"


def _upsert_secret(sm, key: str, value: str) -> None:
    from google.api_core.exceptions import AlreadyExists
    try:
        sm.create_secret(request={
            "parent": f"projects/{PROJECT_ID}",
            "secret_id": f"client-{CLIENT_ID}-{key}",
            "secret": {"replication": {"automatic": {}}}
        })
    except AlreadyExists:
        pass
    sm.add_secret_version(request={
        "parent": _secret_name(key),
        "payload": {"data": value.encode("utf-8")}
    })


@app.get("/config/status")
async def config_status():
    from google.api_core.exceptions import NotFound, PermissionDenied
    try:
        sm = _sm_client()
        sm.access_secret_version(
            request={"name": _secret_version_name("github-token")})
        return {"configured": True}
    except (NotFound, PermissionDenied):
        return {"configured": False}
    except Exception as e:
        print(f"⚠️  config/status error: {e}")
        return {"configured": False}


@app.post("/config")
async def upsert_config(request: Request):
    try:
        body = await request.json()
        github_token = body.get("github_token", "").strip()
        jenkins_token = body.get("jenkins_token", "").strip()
        jenkins_url = body.get("jenkins_url", "").strip()
        jenkins_user = body.get("jenkins_user", "").strip()

        if not all([github_token, jenkins_token, jenkins_url, jenkins_user]):
            raise HTTPException(
                status_code=400, detail="All four fields required: github_token, jenkins_token, jenkins_url, jenkins_user")

        sm = _sm_client()
        _upsert_secret(sm, "github-token",  github_token)
        _upsert_secret(sm, "jenkins-token", jenkins_token)
        _upsert_secret(sm, "jenkins-url",   jenkins_url)
        _upsert_secret(sm, "jenkins-user",  jenkins_user)

        print(f"✅ Config upserted for client '{CLIENT_ID}'")
        return {"status": "ok", "message": "Configuration saved successfully.", "client_id": CLIENT_ID}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Config upsert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "webhook-handler", "project": PROJECT_ID, "topic": TOPIC_NAME}


@app.get("/")
def root():
    return {"service": "Webhook Handler", "version": "1.0.0", "endpoints": {"webhook": "/webhook/github", "health": "/health"}, "configuration": {"project": PROJECT_ID, "topic": TOPIC_NAME}}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', '8080'))
    print(f"\n{'='*60}\n🚀 Starting Webhook Handler on port {port}\n{'='*60}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
