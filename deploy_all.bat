@echo off
echo Deploying all Cloud Run services...
@REM These are old commands. The MCP servers used these in single-tenant workflow. The multi tenant uses the commands in GCP_UPDATE_COMMANDS
echo.
echo [1/5] Deploying GitHub MCP...
cd "C:\Users\Tanish\Desktop\Tanish Singla\YEAR 4\Sem1\Capstone I\Capstone_MCP_Test\mcp_servers\github_server"
gcloud run deploy github-mcp --source . --region us-central1 --no-allow-unauthenticated --set-secrets GITHUB_TOKEN=github-token:latest --max-instances 5 --timeout 60

echo.
echo [2/5] Deploying Jenkins MCP...
cd "C:\Users\Tanish\Desktop\Tanish Singla\YEAR 4\Sem1\Capstone I\Capstone_MCP_Test\mcp_servers\jenkins_server"
gcloud run deploy jenkins-mcp --source . --region us-central1 --no-allow-unauthenticated --set-secrets JENKINS_TOKEN=jenkins-token:latest --set-env-vars JENKINS_URL=http://34.122.221.100:8080 --max-instances 5 --timeout 60

echo.
echo [3/5] Deploying Webhook Handler...
cd "C:\Users\Tanish\Desktop\Tanish Singla\YEAR 4\Sem1\Capstone I\Capstone_MCP_Test\webhook_handler"
gcloud run deploy webhook-handler --source . --region us-central1 --allow-unauthenticated --set-env-vars PROJECT_ID=capstone-cicd-ai,PUBSUB_TOPIC_COMMANDS=workflow-commands --max-instances 10 --timeout 60

echo.
echo [4/5] Deploying Orchestrator Worker...
cd "C:\Users\Tanish\Desktop\Tanish Singla\YEAR 4\Sem1\Capstone I\Capstone_MCP_Test"
gcloud run deploy orchestrator-worker --source . --region us-central1 --no-allow-unauthenticated --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest,GITHUB_TOKEN=github-token:latest,JENKINS_TOKEN=jenkins-token:latest --set-env-vars PROJECT_ID=capstone-cicd-ai,PUBSUB_SUBSCRIPTION=workflow-commands-sub,GITHUB_MCP_URL=https://github-mcp-389127668230.us-central1.run.app,JENKINS_MCP_URL=https://jenkins-mcp-389127668230.us-central1.run.app --max-instances 5 --timeout 3600 --memory 1Gi --cpu 2

echo.
echo [5/5] Deploying Event Gateway...
cd "C:\Users\Tanish\Desktop\Tanish Singla\YEAR 4\Sem1\Capstone I\Capstone_MCP_Test\backend"
gcloud run deploy event-gateway --source . --region us-central1 --allow-unauthenticated --set-env-vars PROJECT_ID=capstone-cicd-ai,PUBSUB_TOPIC_EVENTS=workflow-events,PUBSUB_SUBSCRIPTION_EVENTS=workflow-events-sub --max-instances 10 --timeout 60

echo.
echo ============================================================
echo All services deployed successfully!
echo ============================================================