# Capstone MCP — Deploy Reference

All commands run from project root: `Capstone_MCP_Test\`

---

## 1. GitHub MCP

```cmd
cd mcp_servers\github_server
gcloud builds submit --tag gcr.io/capstone-cicd-ai/github-mcp .
gcloud run deploy github-mcp --image gcr.io/capstone-cicd-ai/github-mcp --region us-central1 --no-allow-unauthenticated
cd ..\..
```

---

## 2. Jenkins MCP

```cmd
cd mcp_servers\jenkins_server
gcloud builds submit --tag gcr.io/capstone-cicd-ai/jenkins-mcp .
gcloud run deploy jenkins-mcp --image gcr.io/capstone-cicd-ai/jenkins-mcp --region us-central1 --no-allow-unauthenticated --set-env-vars JENKINS_URL=http://34.59.25.142:8080,JENKINS_USER=tan1409,JENKINS_TOKEN=11630af681615af33d83e04c37733cf1fb
cd ..\..
```

---

## 3. Webhook Handler

```cmd
cd webhook_handler
gcloud builds submit --tag gcr.io/capstone-cicd-ai/webhook-handler .
gcloud run deploy webhook-handler --image gcr.io/capstone-cicd-ai/webhook-handler --region us-central1 --allow-unauthenticated
cd ..
```

---

## 4. Orchestrator Worker

```cmd
cd orchestrator_worker_deploy
gcloud builds submit --config=cloudbuild.yaml ..
gcloud run deploy orchestrator-worker --image gcr.io/capstone-cicd-ai/orchestrator-worker --region us-central1 --no-allow-unauthenticated --set-env-vars PROJECT_ID=capstone-cicd-ai,PUBSUB_SUBSCRIPTION=workflow-commands-sub,GITHUB_MCP_URL=https://github-mcp-389127668230.us-central1.run.app,JENKINS_MCP_URL=https://jenkins-mcp-389127668230.us-central1.run.app
cd ..
```

---

## 5. Event Gateway (Backend / WebSocket Server)

```cmd
cd backend
gcloud builds submit --tag gcr.io/capstone-cicd-ai/event-gateway .
gcloud run deploy event-gateway --image gcr.io/capstone-cicd-ai/event-gateway --region us-central1 --allow-unauthenticated --set-env-vars PROJECT_ID=capstone-cicd-ai,PUBSUB_TOPIC_EVENTS=workflow-events,PUBSUB_SUBSCRIPTION_EVENTS=workflow-events-sub
cd ..
```

---

## 6. Frontend

```cmd
cd frontend
npm run build
gcloud builds submit --tag gcr.io/capstone-cicd-ai/frontend .
gcloud run deploy frontend --image gcr.io/capstone-cicd-ai/frontend --region us-central1 --allow-unauthenticated
cd ..
```

---

## Trigger a Workflow (Test)

```cmd
curl -X POST https://webhook-handler-389127668230.us-central1.run.app/webhook/github ^
  -H "Content-Type: application/json" ^
  -d "{\"repository\":{\"full_name\":\"kunalpanda/test_banking_app\"},\"ref\":\"refs/heads/main\",\"after\":\"TEST-001\",\"head_commit\":{\"message\":\"Manual trigger\"}}"
```

---

## Service URLs

| Service             | URL                                                          |
| ------------------- | ------------------------------------------------------------ |
| Webhook Handler     | https://webhook-handler-389127668230.us-central1.run.app     |
| Orchestrator Worker | https://orchestrator-worker-389127668230.us-central1.run.app |
| GitHub MCP          | https://github-mcp-389127668230.us-central1.run.app          |
| Jenkins MCP         | https://jenkins-mcp-389127668230.us-central1.run.app         |
| Frontend            | https://frontend-389127668230.us-central1.run.app            |

---

## Notes

- **Orchestrator Worker** builds from project root (the `cloudbuild.yaml` inside `orchestrator_worker_deploy/` uses `..` as context)
- **GitHub & Jenkins MCP** use `--no-allow-unauthenticated` — only the orchestrator worker can call them via GCP identity tokens
- **Webhook Handler & Frontend** use `--allow-unauthenticated` — they are public-facing
- **Jenkins token** in the Jenkins MCP deploy env var may need updating if the token rotates
