# mcp_servers/jenkins_server/tools.py
import httpx
from .config import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN

# Jenkins requires basic authentication
AUTH = (JENKINS_USER, JENKINS_TOKEN)


# =========================================================
# 1️⃣ trigger_build → Start a Jenkins job
# =========================================================
async def trigger_build(job_name: str, parameters: dict = None):
    """Triggers a Jenkins job with optional parameters."""
    url = f"{JENKINS_URL}/job/{job_name}/build"
    if parameters:
        url += "WithParameters"
    async with httpx.AsyncClient(auth=AUTH) as client:
        res = await client.post(url, params=parameters or {})
        if res.status_code not in (200, 201, 202):
            raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")
    return {"status": "triggered", "job": job_name}


# =========================================================
# 2️⃣ get_queue_info → Check Jenkins queue
# =========================================================
async def get_queue_info():
    """Fetch current Jenkins queue state."""
    url = f"{JENKINS_URL}/queue/api/json"
    async with httpx.AsyncClient(auth=AUTH) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json()
    return {"queue_length": len(data.get("items", [])), "items": data.get("items", [])[:5]}


# =========================================================
# 3️⃣ get_build_info → Retrieve info for a job's last build
# =========================================================
async def get_build_info(job_name: str):
    """Get details of the latest Jenkins build for a job."""
    url = f"{JENKINS_URL}/job/{job_name}/lastBuild/api/json"
    async with httpx.AsyncClient(auth=AUTH) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")
        data = res.json()
    return {
        "job_name": job_name,
        "build_number": data.get("number"),
        "status": data.get("result"),
        "duration": data.get("duration"),
        "url": data.get("url"),
    }


# =========================================================
# 4️⃣ get_console_output → Retrieve console log of a build
# =========================================================
async def get_console_output(job_name: str, build_number: int):
    """Fetch Jenkins console log for a specific build."""
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/logText/progressiveText"
    async with httpx.AsyncClient(auth=AUTH) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")
    return {"job_name": job_name, "build_number": build_number, "log": res.text[:10000]}  # truncate large logs


# =========================================================
# MCP Tool Manifest
# =========================================================
async def list_tools():
    """Enumerate available Jenkins tools."""
    return {
        "tools": [
            {"name": "trigger_build", "description": "Trigger a Jenkins job build"},
            {"name": "get_queue_info", "description": "Fetch Jenkins queue details"},
            {"name": "get_build_info", "description": "Fetch latest build info for a job"},
            {"name": "get_console_output", "description": "Retrieve console output for a build"},
        ]
    }
