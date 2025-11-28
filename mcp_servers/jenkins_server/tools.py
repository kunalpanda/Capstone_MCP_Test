# mcp_servers/jenkins_server/tools.py
import httpx
from .config import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN
import asyncio 

# Jenkins requires basic authentication
AUTH = (JENKINS_USER, JENKINS_TOKEN)

# === Helper: enforce branch parameter for all builds ===
def enforce_branch_param(parameters: dict | None) -> dict:
    """
    Ensures every Jenkins build has a BRANCH parameter.
    Pulls from ACTIVE_BRANCH environment variable or defaults to 'main'.
    """
    import os
    active_branch = os.getenv("ACTIVE_BRANCH", "main")
    parameters = parameters or {}
    parameters.setdefault("BRANCH", active_branch)
    return parameters


# =========================================================
# 1️⃣ trigger_build → Start a Jenkins job
# =========================================================
async def trigger_build(job_name: str, parameters: dict = None):
    """
    Trigger a Jenkins job, ensuring BRANCH parameter and proper endpoint usage.
    """
    # ✅ Always enforce branch
    parameters = enforce_branch_param(parameters)

    url = f"{JENKINS_URL}/job/{job_name}/buildWithParameters"

    async with httpx.AsyncClient(auth=AUTH) as client:
        res = await client.post(url, params=parameters)
        if res.status_code not in (200, 201, 202):
            raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")

        queue_url = res.headers.get("Location")
        build_number = None

        # Poll the queue for assigned build number
        if queue_url:
            for _ in range(20):  # up to ~10s
                qres = await client.get(f"{queue_url}api/json")
                if qres.status_code == 200:
                    qdata = qres.json()
                    if "executable" in qdata and qdata["executable"]:
                        build_number = qdata["executable"]["number"]
                        break
                await asyncio.sleep(0.5)

    return {
        "status": "triggered",
        "job": job_name,
        "parameters": parameters,
        "queue_url": queue_url,
        "build_number": build_number,
    }




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
# wait_for_build_completion → Poll Jenkins until a build finishes
# =========================================================
async def wait_for_build_completion(
    job_name: str,
    build_number: int,
    timeout_seconds: int = 600,
    poll_interval: int = 10,
    max_retries: int = 10,
):
    """
    Waits for a Jenkins build to complete.
    Retries up to `max_retries` times on HTTP 404 (build not yet created).
    """
    import asyncio, time
    start = time.time()
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/api/json"

    async with httpx.AsyncClient(auth=AUTH) as client:
        retries = 0
        while True:
            try:
                res = await client.get(url)
                # Handle 404: build not yet available
                if res.status_code == 404:
                    retries += 1
                    if retries > max_retries:
                        raise RuntimeError(
                            f"Build #{build_number} not found after {max_retries} retries."
                        )
                    print(f"⚠️ Build #{build_number} not yet created (404). Retry {retries}/{max_retries} in {poll_interval}s...")
                    await asyncio.sleep(poll_interval)
                    continue

                if res.status_code != 200:
                    raise RuntimeError(f"Jenkins returned {res.status_code}: {res.text}")

                data = res.json()
                if data.get("building", False):
                    elapsed = int(time.time() - start)
                    print(f"⏳ Build #{build_number} still running... ({elapsed}s elapsed)")
                    await asyncio.sleep(poll_interval)
                    if elapsed > timeout_seconds:
                        raise TimeoutError(f"Timed out after {timeout_seconds}s waiting for build #{build_number}")
                    continue

                # Completed successfully or failed
                result = data.get("result", "UNKNOWN")
                duration = data.get("duration", 0)
                elapsed = int(time.time() - start)
                print(f"✅ Build #{build_number} finished with status: {result}")
                return {
                    "status": "completed",
                    "job_name": job_name,
                    "build_number": build_number,
                    "result": result,
                    "duration": duration,
                    "elapsed_seconds": elapsed,
                    "url": f"{JENKINS_URL}/job/{job_name}/{build_number}/",
                }

            except httpx.RequestError as e:
                retries += 1
                if retries > max_retries:
                    raise RuntimeError(f"Failed after {max_retries} retries: {str(e)}")
                print(f"⚠️ Request error: {e}. Retry {retries}/{max_retries} in {poll_interval}s...")
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
# MCP Tool Manifest - COMPLETE DEFINITIONS WITH SCHEMAS
# =========================================================
async def list_tools():
    """Enumerate available Jenkins tools with complete schemas."""
    return {
        "tools": [
            {
                "name": "trigger_build",
                "description": "Trigger a new Jenkins build for a job.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_name": {"type": "string", "description": "Name of the Jenkins job"},
                        "parameters": {"type": "object", "description": "Build parameters (optional)"}
                    },
                    "required": ["job_name"]
                }
            },
            {
                "name": "get_queue_info",
                "description": "Check the current Jenkins build queue",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_build_info",
                "description": "Get detailed information about the latest build of a Jenkins job including status, duration, and URL.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_name": {"type": "string", "description": "Name of the Jenkins job"}
                    },
                    "required": ["job_name"]
                }
            },
            {
                "name": "get_console_output",
                "description": "Retrieve the console log output for a specific Jenkins build. Useful for debugging failed builds.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_name": {"type": "string", "description": "Name of the Jenkins job"},
                        "build_number": {"type": "integer", "description": "Specific build number to retrieve logs for"}
                    },
                    "required": ["job_name", "build_number"]
                }
            },
            {
                "name": "wait_for_build_completion",
                "description": "Wait for a Jenkins build to complete and return its result.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_name": {"type": "string", "description": "Name of the Jenkins job"},
                        "build_number": {"type": "integer", "description": "Build number to wait for"},
                        "timeout_seconds": {"type": "integer", "description": "Max wait time (default: 600)", "default": 600},
                        "poll_interval": {"type": "integer", "description": "Seconds between polls (default: 10)", "default": 10}
                    },
                    "required": ["job_name", "build_number"]
                }
            },
            {
                "name": "get_test_results",
                "description": "Get test results from a Jenkins build including failed tests details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_name": {"type": "string", "description": "Name of the Jenkins job"},
                        "build_number": {"type": "integer", "description": "Build number (optional, uses lastBuild)"}
                    },
                    "required": ["job_name"]
                }
            }
        ]
    }