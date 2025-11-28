@echo off
echo Starting services...
echo.

REM Start GitHub MCP Server
echo Starting GitHub MCP Server on port 8010...
start "GitHub MCP Server" cmd /k "uvicorn mcp_servers.github_server.server:app --port 8010"

REM Start Jenkins MCP Server
echo Starting Jenkins MCP Server on port 8020...
start "Jenkins MCP Server" cmd /k "uvicorn mcp_servers.jenkins_server.server:app --port 8020"

REM Start WebSocket Server
echo Starting WebSocket Server...
start "WebSocket Server" cmd /k "python backend\websocket_server.py"

REM Start Frontend
echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm start"

echo.
echo All background services started.
echo.

REM Ask for user approval before starting orchestrator
set /p CONFIRM="Do you want to start the orchestrator? (Y/N): "
if /i "%CONFIRM%"=="Y" (
    echo Starting Orchestrator...
    start "Orchestrator" cmd /k "python -m orchestrator.orchestrator"
    echo Orchestrator started.
) else (
    echo Orchestrator startup cancelled.
)

echo.
echo All requested services have been processed.
pause