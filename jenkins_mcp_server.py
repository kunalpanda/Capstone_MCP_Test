import os
import json
import asyncio
import httpx
import websockets
import sys
from typing import Any, Optional
import inspect
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================
JENKINS_URL = os.getenv("JENKINS_URL", "http://localhost:8080").rstrip('/')
JENKINS_USER = os.getenv("JENKINS_USER", "admin")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN", "")
MCP_PORT = 4001 

# --- DEBUG PRINT FOR AUTHENTICATION ---
print("-" * 50)
print(f"DEBUG: Jenkins URL used: {JENKINS_URL}")
print(f"DEBUG: Jenkins User used: {JENKINS_USER}")
print(f"DEBUG: Jenkins Token loaded: {'***' if JENKINS_TOKEN else 'NOT SET'}")
print("-" * 50)
# ------------------------------------

if not JENKINS_TOKEN:
    print("⚠️ WARNING: JENKINS_TOKEN not found. Tools requiring authentication will fail with 401.")

# ============================================================
# JENKINS CLIENT (HTTPx Wrapper)
# ============================================================

class JenkinsClient:
    """Client for interacting with Jenkins API, managing authentication and errors."""
    
    def __init__(self, url: str, user: str, token: str):
        self.url = url
        self.auth = (user, token)
        
    async def _get_crumb(self, client: httpx.AsyncClient) -> dict:
        """Get Jenkins CSRF crumb if CSRF protection is enabled."""
        try:
            response = await client.get(
                f"{self.url}/crumbIssuer/api/json",
                auth=self.auth
            )
            if response.status_code == 200:
                data = response.json()
                return {data['crumbRequestField']: data['crumb']}
        except Exception:
            pass
        return {}
    
    async def jenkins_request(self, endpoint: str, method: str = "GET", params: Optional[dict] = None, data: Optional[dict] = None, content: Optional[str] = None, headers: Optional[dict] = None) -> dict:
        """Generic helper to call the Jenkins API and handle errors."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            auth_headers = await self._get_crumb(client)
            if headers:
                auth_headers.update(headers)

            try:
                response = await client.request(
                    method,
                    f"{self.url}{endpoint}",
                    auth=self.auth,
                    headers=auth_headers,
                    params=params,
                    data=data,
                    content=content
                )
                
                # Success cases
                if response.status_code in [200]:
                    # Handle raw text endpoints (logs, config XML)
                    if endpoint.endswith("/consoleText") or endpoint.endswith("/config.xml"):
                        return {"text": response.text}
                    return response.json() if response.text else {"message": "Operation successful."}
                
                # Specific Trigger Build Success (201 Created/Queued)
                if response.status_code == 201 and method == "POST" and ("/build" in endpoint or "/buildWithParameters" in endpoint):
                    return {
                        "status": "triggered",
                        "queue_url": response.headers.get("Location", "")
                    }
                
                # Failure case (e.g., 404, 401, 500)
                # Return the 401 Unauthorized details captured in your previous output
                return {
                    "error": f"Jenkins API failed for {endpoint}",
                    "status_code": response.status_code,
                    "details": response.text.strip()
                }

            except httpx.RequestError as e:
                return {
                    "error": "Network or request failure",
                    "details": str(e)
                }

    # --- Tool Implementations (Client Methods) ---
    
    async def list_jobs(self) -> dict:
        """List all jobs in Jenkins."""
        return await self.jenkins_request("/api/json?tree=jobs[name,color,url]")
    
    async def get_job_info(self, job_name: str) -> dict:
        """Get information about a specific job."""
        return await self.jenkins_request(f"/job/{job_name}/api/json")
    
    async def get_build_info(self, job_name: str, build_number: int) -> dict:
        """Get information about a specific build."""
        return await self.jenkins_request(f"/job/{job_name}/{build_number}/api/json")

    async def get_console_output(self, job_name: str, build_number: int) -> dict:
        """Get console output for a specific build."""
        return await self.jenkins_request(f"/job/{job_name}/{build_number}/consoleText")

    async def trigger_build(self, job_name: str, parameters: Optional[dict] = None) -> dict:
        """Trigger a new build for a job."""
        if parameters:
            return await self.jenkins_request(f"/job/{job_name}/buildWithParameters", "POST", data=parameters)
        else:
            return await self.jenkins_request(f"/job/{job_name}/build", "POST")
    
    async def get_queue_info(self) -> dict:
        """Get information about the build queue."""
        return await self.jenkins_request("/queue/api/json")

    async def get_job_config(self, job_name: str) -> dict:
        """Get the XML configuration of a job."""
        return await self.jenkins_request(f"/job/{job_name}/config.xml")
    
    async def update_job_config(self, job_name: str, config_xml: str) -> dict:
        """Update the XML configuration of a job."""
        return await self.jenkins_request(
            f"/job/{job_name}/config.xml", 
            "POST", 
            content=config_xml,
            headers={"Content-Type": "application/xml"}
        )

# Initialize Jenkins client
jenkins = JenkinsClient(JENKINS_URL, JENKINS_USER, JENKINS_TOKEN)

# ============================================================
# MANUAL TOOL MAPPING AND DEFINITIONS
# ============================================================

TOOL_HANDLERS = {
    "list_jobs": jenkins.list_jobs,
    "get_job_info": jenkins.get_job_info,
    "get_build_info": jenkins.get_build_info,
    "get_console_output": jenkins.get_console_output,
    "trigger_build": jenkins.trigger_build,
    "get_queue_info": jenkins.get_queue_info,
    "get_job_config": jenkins.get_job_config,
    "update_job_config": jenkins.update_job_config,
}

TOOL_DEFINITIONS = [
    # ... (Tool definitions remain the same as the last version)
    {
        "name": "list_jobs",
        "description": "List all Jenkins jobs with their status. Returns job names, URLs, and colors (status).",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_job_info",
        "description": "Get detailed information about a specific Jenkins job (e.g., last build numbers, health report).",
        "inputSchema": {"type": "object", "properties": {"job_name": {"type": "string", "description": "Name of the Jenkins job"}}, "required": ["job_name"]}
    },
    {
        "name": "get_build_info",
        "description": "Get detailed information about a specific build.",
        "inputSchema": {"type": "object", "properties": {"job_name": {"type": "string"}, "build_number": {"type": "integer"}}, "required": ["job_name", "build_number"]}
    },
    {
        "name": "get_console_output",
        "description": "Get the raw console output/logs for a specific build.",
        "inputSchema": {"type": "object", "properties": {"job_name": {"type": "string"}, "build_number": {"type": "integer"}}, "required": ["job_name", "build_number"]}
    },
    {
        "name": "trigger_build",
        "description": "Trigger a new build for a Jenkins job. Returns the queue URL.",
        "inputSchema": {"type": "object", "properties": {"job_name": {"type": "string"}, "parameters": {"type": "object", "description": "Optional build parameters as key-value pairs"}}, "required": ["job_name"]}
    },
    {
        "name": "get_queue_info",
        "description": "Get information about jobs currently waiting in the build queue.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_job_config",
        "description": "Get the raw XML configuration of a Jenkins job.",
        "inputSchema": {"type": "object", "properties": {"job_name": {"type": "string"}}, "required": ["job_name"]}
    },
    {
        "name": "update_job_config",
        "description": "Update the XML configuration of a Jenkins job. Requires admin token.",
        "inputSchema": {"type": "object", "properties": {"job_name": {"type": "string"}, "config_xml": {"type": "string"}}, "required": ["job_name", "config_xml"]}
    },
]

# ============================================================
# MANUAL WEBSOCKET/JSON-RPC HANDLING
# ============================================================

async def handle_tool_call(tool_name: str, args: dict) -> dict:
    """Executes the mapped Jenkins tool handler."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool '{tool_name}'"}
    
    try:
        sig = inspect.signature(handler)
        handler_args = {name: args[name] for name in sig.parameters if name in args}
        
        tool_result = await handler(**handler_args)

    except Exception as e:
        return {"error": "Tool call execution failed", "details": str(e)}

    return tool_result


async def handle_connection(ws):
    """Handler for incoming WebSocket connections."""
    print("🟢 Jenkins Client connected (JSON-RPC Handler)")
    try:
        async for message in ws:
            data = json.loads(message)
            request_id = data.get("id")
            method = data.get("method")
            params = data.get("params", {})
            
            if method == "tools/list":
                # --- CORRECT JSON-RPC METHOD HANDLING ---
                result = {"tools": TOOL_DEFINITIONS}
                await ws.send(json.dumps({"id": request_id, "result": result}))

            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                
                tool_result = await handle_tool_call(tool_name, args)
                await ws.send(json.dumps({"id": request_id, "result": tool_result}))
            
            else:
                 await ws.send(json.dumps({"id": request_id, "error": f"Unknown method '{method}'"}))

    except websockets.ConnectionClosed:
        print("🔴 Jenkins Client disconnected")
    except Exception as e:
        print(f"❌ Error during connection handling: {e}")

async def main():
    """Starts the WebSocket server."""
    print(f"🚀 Starting Jenkins MCP Server on ws://localhost:{MCP_PORT}")
    print("---")
    
    async with websockets.serve(handle_connection, "localhost", MCP_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())