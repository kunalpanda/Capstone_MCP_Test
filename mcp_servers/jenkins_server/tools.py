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

import asyncio
from typing import Optional

# =========================================================
# 5️⃣ wait_for_build_completion → Poll until build finishes
# =========================================================
async def wait_for_build_completion(
    job_name: str,
    build_number: int,
    timeout_seconds: int = 600,
    poll_interval: int = 10
):
    """
    Wait for a Jenkins build to complete by polling its status.
    Returns the final build result or times out.
    """
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/api/json"
    start_time = asyncio.get_event_loop().time()
    
    async with httpx.AsyncClient(auth=AUTH) as client:
        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                return {
                    "status": "timeout",
                    "job_name": job_name,
                    "build_number": build_number,
                    "elapsed_seconds": int(elapsed),
                    "message": f"Build did not complete within {timeout_seconds} seconds"
                }
            
            # Poll build status
            res = await client.get(url)
            if res.status_code != 200:
                raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")
            
            data = res.json()
            building = data.get("building", False)
            result = data.get("result")
            
            # If build is complete
            if not building and result:
                return {
                    "status": "completed",
                    "job_name": job_name,
                    "build_number": build_number,
                    "result": result,
                    "duration": data.get("duration"),
                    "elapsed_seconds": int(elapsed),
                    "url": data.get("url")
                }
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)


# =========================================================
# 6️⃣ get_test_results → Retrieve test results from build
# =========================================================
async def get_test_results(job_name: str, build_number: Optional[int] = None):
    """
    Get test results from a Jenkins build.
    If build_number is not provided, uses the last build.
    """
    # Determine build path
    if build_number:
        build_path = f"{build_number}"
    else:
        build_path = "lastBuild"
    
    url = f"{JENKINS_URL}/job/{job_name}/{build_path}/testReport/api/json"
    
    async with httpx.AsyncClient(auth=AUTH) as client:
        res = await client.get(url)
        
        # Test results might not exist if no tests ran
        if res.status_code == 404:
            return {
                "job_name": job_name,
                "build_number": build_number or "last",
                "status": "no_tests",
                "message": "No test results available for this build"
            }
        
        if res.status_code != 200:
            raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")
        
        data = res.json()
        
        # Parse test results
        failed_tests = []
        if data.get("failCount", 0) > 0:
            for suite in data.get("suites", []):
                for case in suite.get("cases", []):
                    if case.get("status") in ["FAILED", "REGRESSION"]:
                        failed_tests.append({
                            "name": case.get("name"),
                            "class_name": case.get("className"),
                            "status": case.get("status"),
                            "duration": case.get("duration"),
                            "error_message": case.get("errorDetails"),
                            "error_stacktrace": case.get("errorStackTrace")
                        })
        
        return {
            "job_name": job_name,
            "build_number": build_number or "last",
            "total_count": data.get("totalCount", 0),
            "fail_count": data.get("failCount", 0),
            "skip_count": data.get("skipCount", 0),
            "pass_count": data.get("passCount", 0),
            "duration": data.get("duration", 0),
            "failed_tests": failed_tests[:20]  # Limit to first 20 failures
        }


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
            {"name": "wait_for_build_completion", "description": "Wait for a build to complete"},
            {"name": "get_test_results", "description": "Get test results from a build"},
        ]
    }