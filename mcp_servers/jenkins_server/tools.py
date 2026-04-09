from typing import Optional
import asyncio
import httpx

# Credentials are passed per-request via jenkins_token, jenkins_url, jenkins_user params
# No module-level AUTH or JENKINS_URL constants


def enforce_branch_param(parameters: dict | None) -> dict:
    """Defaults BRANCH_NAME to ACTIVE_BRANCH env var or 'main'."""
    import os
    active_branch = os.getenv("ACTIVE_BRANCH", "main")
    parameters = parameters or {}
    parameters.setdefault("BRANCH_NAME", active_branch)
    return parameters


async def trigger_build(job_name: str, parameters: dict = None,
                        jenkins_token: str = None, jenkins_url: str = None, jenkins_user: str = None):
    auth = (jenkins_user, jenkins_token)
    parameters = enforce_branch_param(parameters)

    url = f"{jenkins_url}/job/{job_name}/buildWithParameters"

    async with httpx.AsyncClient(auth=auth) as client:
        res = await client.post(url, params=parameters)
        if res.status_code not in (200, 201, 202):
            raise RuntimeError(
                f"Jenkins returned {res.status_code}: {res.text}")

        queue_url = res.headers.get("Location")
        build_number = None

        if queue_url:
            for _ in range(20):
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


async def get_queue_info(jenkins_token: str = None, jenkins_url: str = None, jenkins_user: str = None):
    auth = (jenkins_user, jenkins_token)
    url = f"{jenkins_url}/queue/api/json"
    async with httpx.AsyncClient(auth=auth) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json()
    return {"queue_length": len(data.get("items", [])), "items": data.get("items", [])[:5]}


async def get_build_info(job_name: str,
                         jenkins_token: str = None, jenkins_url: str = None, jenkins_user: str = None):
    auth = (jenkins_user, jenkins_token)
    url = f"{jenkins_url}/job/{job_name}/lastBuild/api/json"
    async with httpx.AsyncClient(auth=auth) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise RuntimeError(
                f"Jenkins returned {res.status_code}: {res.text}")
        data = res.json()
    return {
        "job_name": job_name,
        "build_number": data.get("number"),
        "status": data.get("result"),
        "duration": data.get("duration"),
        "url": data.get("url"),
    }


def smart_truncate_log(log: str, max_chars: int = 50000) -> dict:
    """20% head (build setup/checkout) + 80% tail (test results, errors, summary)."""
    total_length = len(log)

    if total_length <= max_chars:
        return {
            "log": log,
            "truncated": False,
            "total_length": total_length
        }

    head_size = max_chars // 5
    tail_size = (max_chars * 4) // 5

    head = log[:head_size]
    tail = log[-tail_size:]

    omitted = total_length - max_chars
    truncation_notice = f"\n\n{'='*60}\n[... {omitted:,} characters omitted ...]\n{'='*60}\n\n"

    return {
        "log": head + truncation_notice + tail,
        "truncated": True,
        "total_length": total_length,
        "omitted_chars": omitted,
        "hint": "Test results and errors are typically at the end of the log. The LLM should analyze this raw output directly."
    }


async def get_console_output(job_name: str, build_number: int,
                             jenkins_token: str = None, jenkins_url: str = None, jenkins_user: str = None):
    auth = (jenkins_user, jenkins_token)
    url = f"{jenkins_url}/job/{job_name}/{build_number}/logText/progressiveText"
    async with httpx.AsyncClient(auth=auth) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise RuntimeError(
                f"Jenkins returned {res.status_code}: {res.text}")

    truncation_result = smart_truncate_log(res.text, max_chars=50000)

    return {
        "job_name": job_name,
        "build_number": build_number,
        "log": truncation_result["log"],
        "total_length": truncation_result["total_length"],
        "truncated": truncation_result["truncated"],
        "note": "Raw console log provided. Analyze for test results, failures, errors, and coverage information."
    }


async def wait_for_build_completion(
    job_name: str,
    build_number: int,
    timeout_seconds: int = 600,
    poll_interval: int = 10,
    max_retries: int = 10,
    jenkins_token: str = None,
    jenkins_url: str = None,
    jenkins_user: str = None,
):
    """Retries on HTTP 404 (build not yet created in Jenkins)."""
    import asyncio
    import time
    auth = (jenkins_user, jenkins_token)
    start = time.time()
    url = f"{jenkins_url}/job/{job_name}/{build_number}/api/json"

    async with httpx.AsyncClient(auth=auth) as client:
        retries = 0
        while True:
            try:
                res = await client.get(url)
                if res.status_code == 404:
                    retries += 1
                    if retries > max_retries:
                        raise RuntimeError(
                            f"Build #{build_number} not found after {max_retries} retries."
                        )
                    print(
                        f"⚠️ Build #{build_number} not yet created (404). Retry {retries}/{max_retries} in {poll_interval}s...")
                    await asyncio.sleep(poll_interval)
                    continue

                if res.status_code != 200:
                    raise RuntimeError(
                        f"Jenkins returned {res.status_code}: {res.text}")

                data = res.json()
                if data.get("building", False):
                    elapsed = int(time.time() - start)
                    print(
                        f"⏳ Build #{build_number} still running... ({elapsed}s elapsed)")
                    await asyncio.sleep(poll_interval)
                    if elapsed > timeout_seconds:
                        raise TimeoutError(
                            f"Timed out after {timeout_seconds}s waiting for build #{build_number}")
                    continue

                result = data.get("result", "UNKNOWN")
                duration = data.get("duration", 0)
                elapsed = int(time.time() - start)
                print(
                    f"✅ Build #{build_number} finished with status: {result}")
                return {
                    "status": "completed",
                    "job_name": job_name,
                    "build_number": build_number,
                    "result": result,
                    "duration": duration,
                    "elapsed_seconds": elapsed,
                    "url": f"{jenkins_url}/job/{job_name}/{build_number}/",
                }

            except httpx.RequestError as e:
                retries += 1
                if retries > max_retries:
                    raise RuntimeError(
                        f"Failed after {max_retries} retries: {str(e)}")
                print(
                    f"⚠️ Request error: {e}. Retry {retries}/{max_retries} in {poll_interval}s...")
                await asyncio.sleep(poll_interval)


async def get_test_results(job_name: str, build_number: Optional[int] = None,
                           jenkins_token: str = None, jenkins_url: str = None, jenkins_user: str = None):
    """If build_number is omitted, uses lastBuild."""
    auth = (jenkins_user, jenkins_token)
    if build_number:
        build_path = f"{build_number}"
    else:
        build_path = "lastBuild"

    url = f"{jenkins_url}/job/{job_name}/{build_path}/testReport/api/json"

    async with httpx.AsyncClient(auth=auth) as client:
        res = await client.get(url)

        if res.status_code == 404:
            return {
                "job_name": job_name,
                "build_number": build_number or "last",
                "status": "no_tests",
                "message": "No test results available for this build"
            }

        if res.status_code != 200:
            raise RuntimeError(
                f"Jenkins returned {res.status_code}: {res.text}")

        data = res.json()

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
            "failed_tests": failed_tests[:20]
        }


async def get_coverage_report(job_name: str, build_number: int = None,
                              jenkins_token: str = None, jenkins_url: str = None, jenkins_user: str = None):
    auth = (jenkins_user, jenkins_token)
    if build_number is None:
        url = f"{jenkins_url}/job/{job_name}/lastBuild/api/json"
    else:
        url = f"{jenkins_url}/job/{job_name}/{build_number}/api/json"

    async with httpx.AsyncClient() as client:
        res = await client.get(url, auth=auth)
        if res.status_code != 200:
            raise RuntimeError(f"Failed to get build info: {res.status_code}")

        build_info = res.json()
        actual_build_number = build_info["number"]

        coverage_url = f"{jenkins_url}/job/{job_name}/{actual_build_number}/jacoco/api/json?depth=2"
        coverage_res = await client.get(coverage_url, auth=auth)

        if coverage_res.status_code == 404:
            return {
                "job_name": job_name,
                "build_number": actual_build_number,
                "coverage_available": False,
                "message": "No coverage data available. JaCoCo plugin may not be configured for this job."
            }

        if coverage_res.status_code != 200:
            raise RuntimeError(
                f"Failed to get coverage data: {coverage_res.status_code}: {coverage_res.text}")

        coverage_data = coverage_res.json()

        def extract_percentage(metric):
            if not metric:
                return None
            total = metric.get("total", 0)
            covered = metric.get("covered", 0)
            if total == 0:
                return 0.0
            return round((covered / total) * 100, 2)

        line_coverage = extract_percentage(coverage_data.get("lineCoverage"))
        branch_coverage = extract_percentage(
            coverage_data.get("branchCoverage"))
        method_coverage = extract_percentage(
            coverage_data.get("methodCoverage"))
        class_coverage = extract_percentage(coverage_data.get("classCoverage"))
        instruction_coverage = extract_percentage(
            coverage_data.get("instructionCoverage"))

        return {
            "job_name": job_name,
            "build_number": actual_build_number,
            "coverage_available": True,
            "coverage": {
                "line": line_coverage,
                "branch": branch_coverage,
                "method": method_coverage,
                "class": class_coverage,
                "instruction": instruction_coverage
            },
            "summary": f"Line: {line_coverage}%, Branch: {branch_coverage}%, Method: {method_coverage}%",
            "url": f"{jenkins_url}/job/{job_name}/{actual_build_number}/jacoco/"
        }


async def list_tools():
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
            },
            {
                "name": "get_coverage_report",
                "description": "Get test coverage metrics from Jenkins JaCoCo plugin for a specific build. Returns line, branch, method, class, and instruction coverage percentages.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_name": {
                            "type": "string",
                            "description": "Jenkins job name"
                        },
                        "build_number": {
                            "type": "integer",
                            "description": "Build number (optional, defaults to latest build)"
                        }
                    },
                    "required": ["job_name"]
                }
            }
        ]
    }
