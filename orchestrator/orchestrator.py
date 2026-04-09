import asyncio
import json
import os
import httpx
from string import Template
import time
from typing import Optional

from orchestrator.mcp_client import call_mcp_tool
from orchestrator.config import settings
from orchestrator.state import WorkflowState
from backend.event_emitter import EventEmitter

from orchestrator.firestore_client import get_firestore_client, generate_workflow_id


ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY.strip(
) if settings.ANTHROPIC_API_KEY else None
CLAUDE_MODEL = "claude-opus-4-5-20251101"
PROMPT_FILE = "prompts/revised_prompt.txt"
REPO_OWNER = "kunalpanda"
REPO_NAME = "space-rover-test"
JENKINS_JOB_NAME = "space-rover-test"

state = WorkflowState()
emitter = EventEmitter()


async def call_claude(messages: list, tools: list = None, system: str = None, max_retries: int = 5):
    """Retries on 429 (rate limit) and 529 (overloaded) with backoff."""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 8192,
        "messages": messages
    }

    if system:
        payload["system"] = system

    if tools:
        payload["tools"] = tools

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers
                )

                if res.status_code == 429:
                    retry_after = int(res.headers.get("retry-after", 60))
                    print(
                        f"⚠️  Rate limit (429). Waiting {retry_after}s before retry {attempt + 1}/{max_retries}...")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise Exception(
                            "Rate limit exceeded after max retries")

                if res.status_code == 529:
                    wait_time = 10 * (2 ** attempt)
                    print(
                        f"⚠️  API overloaded (529). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            "API overloaded - max retries exceeded. Try again later.")

                if res.status_code != 200:
                    print(f"❌ Claude API request failed.")
                    print(f"Status code: {res.status_code}")
                    print(f"Response: {res.text}")
                    res.raise_for_status()

                return res.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code not in (429, 529) or attempt == max_retries - 1:
                raise


class WorkflowActionLog:
    """Incrementally built log of tool calls, consumed by compress_message_history()."""

    def __init__(self):
        self.entries: list[dict] = []

    def record(self, iteration: int, tool_name: str, tool_input: dict, result: dict, success: bool):
        entry = {
            "iteration": iteration,
            "tool": tool_name,
            "success": success,
        }

        if tool_name == "create_branch":
            entry["detail"] = f"Created branch '{result.get('branch_name', '?')}' from '{result.get('from_branch', 'main')}'"

        elif tool_name == "create_or_update_file":
            entry["detail"] = f"{result.get('operation', 'modified').capitalize()} file: {tool_input.get('path', '?')} on branch '{result.get('branch', '?')}'"

        elif tool_name == "trigger_build":
            branch_param = (tool_input.get("parameters") or {}).get("BRANCH", "?")
            build_num = result.get("build_number", "?")
            entry["detail"] = f"Triggered build #{build_num} for branch '{branch_param}'"

        elif tool_name == "wait_for_build_completion":
            entry["detail"] = f"Build #{result.get('build_number', '?')} finished: {result.get('result', '?')}"

        elif tool_name == "get_test_results":
            total = result.get("total_count", 0)
            fail = result.get("fail_count", 0)
            passed = result.get("pass_count", 0)
            entry["detail"] = f"Tests: {passed} passed, {fail} failed, {total} total"
            if fail > 0:
                names = [t.get("name", "?") for t in result.get("failed_tests", [])[:5]]
                entry["detail"] += f" — failures: {', '.join(names)}"

        elif tool_name == "get_coverage_report":
            if result.get("coverage_available"):
                cov = result.get("coverage", {})
                entry["detail"] = f"Coverage: line={cov.get('line', '?')}%, branch={cov.get('branch', '?')}%, method={cov.get('method', '?')}%"
            else:
                entry["detail"] = "Coverage not available"

        elif tool_name == "get_file_content":
            entry["detail"] = f"Read file: {tool_input.get('path', '?')} (ref={tool_input.get('ref', 'main')})"

        elif tool_name == "get_file_tree":
            count = result.get("count", 0)
            entry["detail"] = f"Listed file tree: {count} files (ref={tool_input.get('ref', 'main')})"

        elif tool_name == "get_console_output":
            entry["detail"] = f"Retrieved console log for build #{tool_input.get('build_number', '?')} ({result.get('total_length', 0):,} chars)"

        elif tool_name == "create_pull_request":
            entry["detail"] = f"Created PR #{result.get('number', '?')}: {result.get('title', '?')}"

        elif tool_name == "get_repo_info":
            entry["detail"] = f"Retrieved repo info for {tool_input.get('owner', '?')}/{tool_input.get('repo', '?')}"

        elif tool_name == "get_build_info":
            entry["detail"] = f"Build #{result.get('build_number', '?')} status: {result.get('status', '?')}"

        else:
            input_preview = str(tool_input)[:80]
            entry["detail"] = f"{tool_name}({input_preview})"

        if not success:
            error_msg = str(result.get("error", "unknown error"))[:120]
            entry["detail"] = f"FAILED: {tool_name} — {error_msg}"

        self.entries.append(entry)

    def format_summary(self, up_to_iteration: int = None) -> str:
        """If up_to_iteration is set, excludes entries at or above that iteration (they're already in recent context)."""
        if not self.entries:
            return "No actions recorded yet."

        lines = []
        for e in self.entries:
            if up_to_iteration is not None and e["iteration"] >= up_to_iteration:
                break
            status = "✓" if e["success"] else "✗"
            lines.append(f"  [{status}] Iter {e['iteration']}: {e['detail']}")

        if not lines:
            return "No actions to summarize (all are in recent context)."

        return "\n".join(lines)


def _estimate_tokens(messages: list) -> int:
    """~4 chars/token heuristic. Only used to decide when compression kicks in."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        total_chars += len(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        total_chars += len(json.dumps(block.get("input", {})))
                    elif block.get("type") == "tool_result":
                        total_chars += len(str(block.get("content", "")))
                elif isinstance(block, str):
                    total_chars += len(block)
    return total_chars // 4


def compress_message_history(
    messages: list,
    action_log: WorkflowActionLog,
    workflow_state: WorkflowState,
    keep_recent: int = 8,
    token_ceiling: int = 60000
) -> list:
    """Swaps old messages for a structured state summary when nearing the context ceiling.
    Uses the action log (built incrementally) rather than parsing raw tool results.
    Keeps `keep_recent` raw messages verbatim at the end."""
    if len(messages) <= keep_recent + 2:
        return messages

    estimated_tokens = _estimate_tokens(messages)
    if estimated_tokens < token_ceiling:
        return messages

    print(f"📦 Compressing message history: ~{estimated_tokens:,} tokens estimated, "
          f"{len(messages)} messages → keeping last {keep_recent}")

    initial_message = messages[0]
    recent_messages = messages[-keep_recent:]

    recent_start_iteration = None
    for msg in recent_messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    pass

    old_message_count = len(messages) - keep_recent - 1
    summarized_entry_count = max(0, len(action_log.entries) - (keep_recent // 2))

    files_modified = []
    for entry in action_log.entries:
        if entry["tool"] == "create_or_update_file" and entry["success"]:
            detail = entry.get("detail", "")
            if "file:" in detail:
                path_part = detail.split("file:")[1].split(" on branch")[0].strip()
                if path_part and path_part not in files_modified:
                    files_modified.append(path_part)

    builds_triggered = []
    for entry in action_log.entries:
        if entry["tool"] == "wait_for_build_completion" and entry["success"]:
            builds_triggered.append(entry.get("detail", ""))

    branch_info = workflow_state.get_branch()
    coverage_summary = workflow_state.get_coverage_summary()
    action_summary = action_log.format_summary(up_to_iteration=None)

    summary_text = f"""[WORKFLOW CONTEXT — AUTO-GENERATED SUMMARY OF PREVIOUS ACTIONS]

CURRENT STATE:
  Active Branch: {branch_info}
  PR Created: {'#' + str(workflow_state.pr_number) if workflow_state.pr_number else 'Not yet'}
  Phase: {workflow_state.phase}

FILES MODIFIED IN THIS WORKFLOW:
  {chr(10).join('  • ' + f for f in files_modified) if files_modified else '  None yet'}

{coverage_summary}

COMPLETE ACTION HISTORY ({len(action_log.entries)} actions):
{action_summary}

[END OF SUMMARY — The {keep_recent} most recent messages follow in full detail.]"""

    summary_message = {
        "role": "user",
        "content": summary_text
    }

    compressed = [initial_message, summary_message] + recent_messages

    new_token_estimate = _estimate_tokens(compressed)
    print(f"📦 Compressed: {len(messages)} → {len(compressed)} messages, "
          f"~{estimated_tokens:,} → ~{new_token_estimate:,} tokens")

    return compressed


def truncate_tool_results(messages: list, max_result_length: int = 55000) -> list:
    """55k limit accommodates Jenkins 50k console logs while staying within Claude's ~100k token window."""
    truncated_messages = []

    for msg in messages:
        if msg["role"] == "user" and isinstance(msg["content"], list):
            truncated_content = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content", "")
                    if isinstance(content, str) and len(content) > max_result_length:
                        truncated_block = block.copy()
                        truncated_block["content"] = content[:max_result_length] + \
                            "\n\n[... truncated for length]"
                        truncated_content.append(truncated_block)
                    else:
                        truncated_content.append(block)
                else:
                    truncated_content.append(block)

            truncated_messages.append({
                "role": msg["role"],
                "content": truncated_content
            })
        else:
            truncated_messages.append(msg)

    return truncated_messages


async def fetch_all_tools():
    all_tools = []
    tool_to_server = {}

    mcp_servers = [
        {"name": "GitHub", "url": settings.GITHUB_MCP_URL},
        {"name": "Jenkins", "url": settings.JENKINS_MCP_URL},
    ]

    try:
        for server in mcp_servers:
            server_name = server["name"]
            server_url = server["url"]

            print(f"🔧 Fetching tools from {server_name} MCP server...")

            try:
                response = await call_mcp_tool(
                    server_url=server_url,
                    method="tools/list"
                )

                if "result" in response and "tools" in response["result"]:
                    server_tools = response["result"]["tools"]

                    for tool in server_tools:
                        tool_name = tool["name"]
                        if tool_name in tool_to_server:
                            print(
                                f"   ⚠️  Warning: Tool '{tool_name}' provided by multiple servers")
                        else:
                            all_tools.append(tool)
                            tool_to_server[tool_name] = server_url

                    print(
                        f"   ✅ Loaded {len(server_tools)} tools from {server_name}")
                else:
                    print(
                        f"   ⚠️  No tools found in response from {server_name}")

            except Exception as e:
                print(f"   ❌ Failed to fetch tools from {server_name}: {e}")
                continue

        print(f"📦 Total tools available: {len(all_tools)}\n")
        return all_tools, tool_to_server

    except Exception as e:
        print(f"❌ Failed to fetch tools from MCP servers: {e}")
        print("💡 Falling back to empty tool list - workflow may fail")
        return [], {}


def enforce_branch(params: dict) -> dict:
    """Fill in missing branch/ref params so Claude doesn't accidentally revert to main."""
    if not isinstance(params, dict):
        return params

    active = state.get_branch()

    if "branch" in params and not params["branch"]:
        params["branch"] = active
    if "ref" in params and not params["ref"]:
        params["ref"] = active

    if "parameters" in params and isinstance(params["parameters"], dict):
        params["parameters"].setdefault("BRANCH", active)

    return params


def _ensure_unique_branch_name(tool_input: dict) -> dict:
    """Appends a timestamp suffix (e.g. fix-tests-20250319 → fix-tests-20250319-142635)
    so create_branch never collides with an existing remote branch."""
    from datetime import datetime, timezone

    original_name = tool_input.get("branch_name", "")
    if not original_name:
        return tool_input

    suffix = datetime.now(timezone.utc).strftime("%H%M%S")
    unique_name = f"{original_name}-{suffix}"

    tool_input["branch_name"] = unique_name
    print(f"🔖 Branch name uniquified: '{original_name}' → '{unique_name}'")

    return tool_input


# Pre-calibrated time values (minutes) — NOT generated by the LLM.
# See prompts/productivity_rubric_research.md for research backing each value.
PRODUCTIVITY_TIME_MAP = {
    "codebase_comprehension": {"small": 15, "medium": 30, "large": 45},
    "ci_triage": {
        "build_status_check": 10,
        "test_result_analysis": 20,
        "console_log_analysis": 30,
        "coverage_analysis": 15,
    },
    "root_cause_diagnosis": {"none": 0, "simple": 20, "moderate": 60, "complex": 120},
    "fix_implementation": {"none": 0, "modify_existing": 30, "create_new": 60, "both": 75},
    "build_verify_cycle": 30,       # per cycle
    "pr_created": 20,               # flat
    "verification_per_file": 5,      # per file re-read
    "diff_inspection": 10,           # per diff check
}

DEFAULT_HOURLY_RATE = 75  # USD, fully loaded

PRODUCTIVITY_PROMPT_FILE = "prompts/productivity_analysis_prompt.txt"


async def analyze_workflow_productivity(
    action_log: WorkflowActionLog,
    workflow_duration_seconds: float,
    iteration_count: int
) -> dict:
    """Lightweight Claude call that classifies the work done, then maps those
    classifications to PRODUCTIVITY_TIME_MAP constants. The LLM never estimates times."""
    try:
        prompt_template = open(PRODUCTIVITY_PROMPT_FILE, "r", encoding="utf-8").read()
        action_summary = action_log.format_summary()
        prompt = prompt_template.replace("${ACTION_LOG}", action_summary)

        print(f"\n{'='*60}")
        print("📊 RUNNING PRODUCTIVITY ANALYSIS")
        print(f"{'='*60}")

        response = await call_claude(
            messages=[{"role": "user", "content": prompt}],
            system="You are a workflow analyst. Respond with ONLY valid JSON. No markdown, no backticks, no explanation.",
            max_retries=2
        )

        raw_text = ""
        for block in response.get("content", []):
            if block.get("type") == "text":
                raw_text = block.get("text", "")
                break

        clean = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        classification = json.loads(clean)

        print(f"✅ Classification received: {json.dumps(classification, indent=2)}")

        breakdown = {}
        total_minutes = 0

        comp_level = classification.get("codebase_comprehension", "small")
        comp_min = PRODUCTIVITY_TIME_MAP["codebase_comprehension"].get(comp_level, 15)
        breakdown["codebase_comprehension"] = {"classification": comp_level, "minutes": comp_min}
        total_minutes += comp_min

        ci_triage = classification.get("ci_triage", {})
        ci_minutes = 0
        ci_detail = {}
        for check, time_val in PRODUCTIVITY_TIME_MAP["ci_triage"].items():
            if ci_triage.get(check, False):
                ci_detail[check] = time_val
                ci_minutes += time_val
        breakdown["ci_triage"] = {"components": ci_detail, "minutes": ci_minutes}
        total_minutes += ci_minutes

        diag_level = classification.get("root_cause_diagnosis", "none")
        diag_min = PRODUCTIVITY_TIME_MAP["root_cause_diagnosis"].get(diag_level, 0)
        breakdown["root_cause_diagnosis"] = {"classification": diag_level, "minutes": diag_min}
        total_minutes += diag_min

        fix_level = classification.get("fix_implementation", "none")
        fix_min = PRODUCTIVITY_TIME_MAP["fix_implementation"].get(fix_level, 0)
        breakdown["fix_implementation"] = {"classification": fix_level, "minutes": fix_min}
        total_minutes += fix_min

        cycles = classification.get("build_verify_cycles", 0)
        cycle_min = cycles * PRODUCTIVITY_TIME_MAP["build_verify_cycle"]
        breakdown["build_verify_cycles"] = {"count": cycles, "minutes": cycle_min}
        total_minutes += cycle_min

        pr_created = classification.get("pr_created", False)
        pr_min = PRODUCTIVITY_TIME_MAP["pr_created"] if pr_created else 0
        breakdown["pr_creation"] = {"created": pr_created, "minutes": pr_min}
        total_minutes += pr_min

        verif_count = classification.get("verification_actions", 0)
        verif_min = verif_count * PRODUCTIVITY_TIME_MAP["verification_per_file"]
        breakdown["change_verification"] = {"files_verified": verif_count, "minutes": verif_min}
        total_minutes += verif_min

        diff_count = classification.get("diff_inspections", 0)
        diff_min = diff_count * PRODUCTIVITY_TIME_MAP["diff_inspection"]
        breakdown["diff_inspections"] = {"count": diff_count, "minutes": diff_min}
        total_minutes += diff_min

        total_hours = round(total_minutes / 60, 2)
        cost_saved = round(total_hours * DEFAULT_HOURLY_RATE, 2)
        ai_minutes = round(workflow_duration_seconds / 60, 1)

        result = {
            "breakdown": breakdown,
            "total_manual_minutes": total_minutes,
            "total_manual_hours": total_hours,
            "ai_resolution_minutes": ai_minutes,
            "time_saved_minutes": round(total_minutes - ai_minutes, 1),
            "hourly_rate": DEFAULT_HOURLY_RATE,
            "cost_saved": cost_saved,
            "iteration_count": iteration_count,
            "files_modified": classification.get("files_modified_count", 0),
        }

        print(f"\n📊 PRODUCTIVITY ANALYSIS RESULTS")
        print(f"   Manual estimate: {total_hours} hrs ({total_minutes} min)")
        print(f"   AI resolution:   {ai_minutes} min")
        print(f"   Time saved:      {result['time_saved_minutes']} min")
        print(f"   Cost saved:      ${cost_saved}")
        print(f"{'='*60}\n")

        return result

    except Exception as e:
        print(f"⚠️  Productivity analysis failed (non-fatal): {e}")
        return None


async def fetch_pr_summary_if_exists(repo_owner: str, repo_name: str, branch: str):
    try:
        if not state.pr_number:
            print("ℹ️  No PR number tracked - PR may not have been created")
            return None

        print(f"\n{'='*60}")
        print(f"📥 Fetching PR #{state.pr_number} summary...")
        print(f"{'='*60}")

        pr_details = await call_mcp_tool(
            server_url=settings.GITHUB_MCP_URL,
            method="tools/call",
            name="get_pr_details",
            params={
                "owner": repo_owner,
                "repo": repo_name,
                "pr_number": state.pr_number
            }
        )

        if "result" not in pr_details:
            print("❌ Failed to fetch PR details")
            return None

        pr = pr_details["result"]

        print(f"\n📋 PULL REQUEST SUMMARY")
        print(f"{'='*60}")
        print(f"PR #{pr['number']}: {pr['title']}")
        print(f"Branch: {pr['head_branch']} → {pr['base_branch']}")
        print(f"URL: {pr['url']}")
        print(f"\n{'-'*60}")
        print(f"Claude's Summary:")
        print(f"{'-'*60}")
        print(pr['body'])
        print(f"{'='*60}\n")

        await emitter.emit_pr_summary(
            pr_number=pr['number'],
            pr_url=pr['url'],
            title=pr['title'],
            body=pr['body'],
            branch=pr['head_branch'],
            iteration=state.iteration
        )

        return pr

    except Exception as e:
        print(f"⚠️  Could not fetch PR summary: {e}")
        return None


async def fetch_baseline_coverage(job_name: str, _jenkins_headers: dict = None) -> dict:
    try:
        print(f"\n{'='*60}")
        print("📊 FETCHING BASELINE COVERAGE")
        print(f"{'='*60}")

        result = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="get_coverage_report",
            params={"job_name": job_name},
            headers=_jenkins_headers
        )

        if "result" in result:
            coverage_result = result["result"]

            if coverage_result.get("coverage_available"):
                coverage = coverage_result.get("coverage", {})
                print(f"✅ Baseline coverage retrieved:")
                print(f"   Line: {coverage.get('line', 'N/A')}%")
                print(f"   Branch: {coverage.get('branch', 'N/A')}%")
                print(f"   Method: {coverage.get('method', 'N/A')}%")
                print(f"{'='*60}\n")
                return coverage
            else:
                print(
                    f"⚠️  {coverage_result.get('message', 'No coverage data available')}")
                print(f"{'='*60}\n")
                return {}
        else:
            print(f"⚠️  Failed to fetch coverage: {result}")
            print(f"{'='*60}\n")
            return {}

    except Exception as e:
        print(f"❌ Error fetching baseline coverage: {e}")
        print(f"{'='*60}\n")
        return {}


async def run_full_test_repair_and_generation_workflow(
    workflow_id: str = None,
    repo: str = None,
    branch: str = None,
    commit_sha: str = None,
    github_headers: dict = None,
    jenkins_headers: dict = None
):
    await emitter.emit_workflow_start(
        repo_owner=REPO_OWNER,
        repo_name=REPO_NAME,
        branch="main",
        max_iterations=50
    )

    if not workflow_id:
        workflow_id = generate_workflow_id(
            repo=f"{REPO_OWNER}/{REPO_NAME}",
            branch="main",
            commit_sha="initial-run"
        )
        print(f"⚠️  No workflow_id provided - generated: {workflow_id}")
    else:
        print(f"✅ Using provided workflow_id: {workflow_id}")

    print(f"\n{'='*60}")
    print(f"🆔 Workflow ID: {workflow_id}")
    print(f"{'='*60}\n")

    firestore_client = get_firestore_client(project_id=settings.PROJECT_ID)

    # Webhook handler no longer creates this — orchestrator owns it
    await firestore_client.create_workflow(workflow_id, {
        'repo': f"{REPO_OWNER}/{REPO_NAME}",
        'branch': 'main',
        'commitSha': commit_sha or 'initial-run',
        'status': 'running',
        'phase': state.phase,
        'iteration': 0,
        'triggeredBy': 'webhook' if commit_sha else 'manual'
    })

    baseline_coverage = {}

    print("🚦 Running initial Jenkins build on main branch to detect failing tests...")
    try:
        trigger_resp = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="trigger_build",
            params={"job_name": JENKINS_JOB_NAME,
                    "parameters": {"BRANCH": "main"}},
            headers=jenkins_headers
        )
        print(
            f"✅ Triggered main branch build: {json.dumps(trigger_resp, indent=2)}")

        build_info = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="get_build_info",
            params={"job_name": JENKINS_JOB_NAME},
            headers=jenkins_headers
        )

        if "result" not in build_info:
            raise RuntimeError(
                f"Unexpected response from Jenkins MCP: {build_info}")

        build_number = build_info["result"]["build_number"]
        build_status = build_info["result"]["status"]

        print(f"📄 Latest Jenkins build #{build_number} status: {build_status}")

        print(f"⏳ Waiting for Jenkins build #{build_number} to complete...")

        build_completion = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="wait_for_build_completion",
            headers=jenkins_headers,
            params={
                "job_name": JENKINS_JOB_NAME,
                "build_number": build_number,
                "timeout_seconds": 600,
                "poll_interval": 10,
            },
        )

        if "result" not in build_completion:
            raise RuntimeError(
                f"Unexpected response from wait_for_build_completion: {build_completion}")

        build_status = build_completion["result"]["result"]
        print(
            f"📄 Jenkins build #{build_number} completed with status: {build_status}")

        test_results = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="get_test_results",
            params={"job_name": JENKINS_JOB_NAME,
                    "build_number": build_number},
            headers=jenkins_headers
        )
        print(f"🧪 Test Results: {json.dumps(test_results, indent=2)[:800]}...")

        base_prompt = open(PROMPT_FILE, "r", encoding="utf-8").read()
        context = {
            "OWNER": REPO_OWNER,
            "REPO_NAME": REPO_NAME,
            "DEFAULT_BRANCH": "main",
            "BRANCH": "main",
            "INITIAL_BUILD": build_number,
            "INITIAL_STATUS": build_status,
            "TEST_RESULTS": json.dumps(test_results["result"], indent=2) if "result" in test_results else "{}",

            "TARGET_LINE_COVERAGE": settings.TARGET_LINE_COVERAGE,
            "TARGET_BRANCH_COVERAGE": settings.TARGET_BRANCH_COVERAGE,
            "TARGET_METHOD_COVERAGE": settings.TARGET_METHOD_COVERAGE,
            "BASELINE_LINE_COVERAGE": baseline_coverage.get("line", "N/A") if baseline_coverage else "N/A",
            "BASELINE_BRANCH_COVERAGE": baseline_coverage.get("branch", "N/A") if baseline_coverage else "N/A",
            "BASELINE_METHOD_COVERAGE": baseline_coverage.get("method", "N/A") if baseline_coverage else "N/A",
        }

        from string import Template
        prompt = Template(base_prompt).safe_substitute(context)

        prompt += (
            "\n\nYou have just retrieved the latest Jenkins build results for the main branch. "
            "Start by analyzing failing tests (if any). "
            "Follow this order:\n"
            "1. Fix failing tests (test files only, never edit implementation)\n"
            "2. Generate new tests for improved coverage\n"
            "3. Verify all tests via Jenkins\n"
            "4. Document all tests and reasoning in README.md or TEST_SUMMARY.md\n"
            "Proceed step by step via MCP tools.\n"
        )

        print("\n🔧 Initializing tool discovery...")
        tools, tool_to_server = await fetch_all_tools()

        state.target_coverage = {
            "line": settings.TARGET_LINE_COVERAGE,
            "branch": settings.TARGET_BRANCH_COVERAGE,
            "method": settings.TARGET_METHOD_COVERAGE
        }
        print(f"🎯 Coverage targets set: Line={settings.TARGET_LINE_COVERAGE}%, "
              f"Branch={settings.TARGET_BRANCH_COVERAGE}%, "
              f"Method={settings.TARGET_METHOD_COVERAGE}%")

        baseline_coverage = await fetch_baseline_coverage(job_name=JENKINS_JOB_NAME, _jenkins_headers=jenkins_headers)
        if baseline_coverage:
            state.update_coverage(baseline_coverage)
            print(state.get_coverage_summary())

        await emitter.emit_state_update(state.summary())

        print("\n🧠 Launching full repair + generation workflow...\n")
        await run_conversation_with_tools(
            prompt,
            max_iterations=50,
            tools=tools,
            tool_to_server=tool_to_server,
            workflow_id=workflow_id,
            firestore_client=firestore_client,
            github_headers=github_headers,
            jenkins_headers=jenkins_headers
        )

    except Exception as e:
        print(f"❌ Workflow failed: {e}")

        await emitter.emit_error(
            error_type=type(e).__name__,
            error_message=str(e),
            context={"function": "run_full_test_repair_and_generation_workflow"}
        )

        raise


async def run_conversation_with_tools(
        initial_prompt: str,
        max_iterations: int = 50,
        tools: list = None,
        tool_to_server: dict = None,
        workflow_id: str = None,
        firestore_client=None,
        github_headers: dict = None,
        jenkins_headers: dict = None
):
    if tools is None or tool_to_server is None:
        print("🔄 Tools not provided - fetching from MCP servers...")
        tools, tool_to_server = await fetch_all_tools()
        if not tools or not tool_to_server:
            raise RuntimeError("Failed to fetch tools from MCP servers")

    # Hardcode routing to guarantee correct server regardless of discovery order
    GITHUB_TOOLS = {
        "list_user_repos", "get_repo_info", "get_file_tree", "get_file_content",
        "get_commit_diff", "get_pr_details", "get_pr_diff",
        "create_branch", "create_or_update_file", "create_pull_request"
    }
    JENKINS_TOOLS = {
        "trigger_build", "get_build_info", "get_queue_info",
        "wait_for_build_completion", "get_test_results",
        "get_console_output", "get_coverage_report"
    }
    for name in GITHUB_TOOLS:
        tool_to_server[name] = settings.GITHUB_MCP_URL
    for name in JENKINS_TOOLS:
        tool_to_server[name] = settings.JENKINS_MCP_URL

    messages = [
        {
            "role": "user",
            "content": initial_prompt
        }
    ]

    action_log = WorkflowActionLog()

    import time as _time
    _workflow_start_time = _time.time()

    system_prompt = (
        "You are an autonomous agent for software test analysis and improvement.\n\n"
        "AVAILABLE TOOLS - use ONLY these exact names:\n"
        "GitHub tools: list_user_repos, get_repo_info, get_file_tree, get_file_content, "
        "get_commit_diff, get_pr_details, get_pr_diff, create_branch, create_or_update_file, create_pull_request\n"
        "Jenkins tools: trigger_build, get_build_info, get_queue_info, "
        "wait_for_build_completion, get_test_results, get_console_output, get_coverage_report\n\n"
        "CRITICAL STATE TRACKING:\n"
        "- Always note which branch you're working on\n"
        "- After updating files, VERIFY changes with get_file_content\n"
        "- Before triggering builds, confirm the branch name\n"
        "- If tests fail repeatedly, read back your changes to debug\n"
        "- Document your current state in each response\n\n"
        "CONTEXT WINDOW NOTE:\n"
        "- Older messages may be replaced with a [WORKFLOW CONTEXT] summary.\n"
        "- If you see this summary, trust it — it was built from the actual tool results.\n"
        "- Your most recent messages are always kept in full.\n\n"
        "Use the provided tools to explore repositories and analyze CI/CD pipelines. "
        "Be concise but track state carefully."
    )

    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        print(
            f"🔍 DEBUG: Starting iteration {iteration}, checking stop flag for workflow {workflow_id}")

        if firestore_client and workflow_id:
            try:
                workflow_data = await firestore_client.get_workflow(workflow_id)

                if workflow_data and workflow_data.get('status') == 'stopped':
                    print(
                        f"\n🛑 EMERGENCY STOP detected for workflow {workflow_id}")
                    print(
                        f"   Stop reason: {workflow_data.get('stopReason', 'Unknown')}")
                    print(f"   Iteration: {iteration}/{max_iterations}")
                    print(f"✅ Workflow halted gracefully\n")

                    await emitter.emit_workflow_complete(
                        total_iterations=iteration,
                        success=False,
                        reason="emergency_stop"
                    )

                    await firestore_client.update_workflow(workflow_id, {
                        'status': 'stopped',
                        'iteration': iteration
                    })

                    return {
                        'status': 'stopped',
                        'reason': 'Emergency stop triggered',
                        'iteration': iteration
                    }
            except Exception as e:
                print(f"⚠️  Error checking emergency stop flag: {e}")

        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"{'='*60}")

        await emitter.emit_iteration_start(iteration, max_iterations)

        if firestore_client and workflow_id:
            await firestore_client.update_workflow(workflow_id, {
                'iteration': iteration,
                'phase': state.phase,
                'status': 'running'
            })

        messages = truncate_tool_results(messages)

        messages = compress_message_history(
            messages,
            action_log=action_log,
            workflow_state=state,
            keep_recent=8,
            token_ceiling=60000
        )

        print(f"🤖 Calling Claude (iteration {iteration})...")
        try:
            response = await call_claude(messages, tools=tools, system=system_prompt)
            if firestore_client and workflow_id:
                await firestore_client.save_context(workflow_id, messages)

        except Exception as e:
            print(f"❌ Failed to call Claude: {e}")
            print(f"💡 Consider reducing max_iterations or message history length")
            break

        assistant_message = {
            "role": "assistant",
            "content": response["content"]
        }
        messages.append(assistant_message)

        stop_reason = response.get("stop_reason")
        print(f"⏸️  Stop reason: {stop_reason}")

        for block in response["content"]:
            if block["type"] == "text":
                text = block["text"]
                if len(text) > 500:
                    print(f"\n💬 Claude says:\n{text[:500]}...\n[truncated]\n")
                else:
                    print(f"\n💬 Claude says:\n{text}\n")

        await emitter.emit_claude_response(
            iteration=iteration,
            stop_reason=stop_reason,
            content=response["content"]
        )

        if stop_reason == "end_turn":
            print("✅ Conversation complete - no more tool requests")
            break

        if stop_reason == "tool_use":
            tool_results = []

            for block in response["content"]:
                if block["type"] == "tool_use":
                    tool_name = block["name"]
                    tool_input = block["input"]
                    tool_use_id = block["id"]

                    print(f"\n⚙️  Tool requested: {tool_name}")
                    print(
                        f"📦 Input: {json.dumps(tool_input, indent=2)[:200]}...")

                    await emitter.emit_tool_call(
                        iteration=iteration,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_use_id=tool_use_id
                    )

                    try:
                        server_url = tool_to_server.get(tool_name)

                        if server_url is None:
                            raise ValueError(
                                f"Unknown tool '{tool_name}' - not provided by any MCP server")

                        _headers = github_headers if server_url == settings.GITHUB_MCP_URL else jenkins_headers

                        if tool_name == "create_branch":
                            tool_input = _ensure_unique_branch_name(tool_input)

                        mcp_response = await call_mcp_tool(
                            server_url=server_url,
                            method="tools/call",
                            name=tool_name,
                            params=enforce_branch(tool_input),
                            headers=_headers
                        )

                        if "result" in mcp_response:
                            result = mcp_response["result"]

                            if tool_name == "create_branch" and "branch_name" in result:
                                state.branch = result["branch_name"]
                                print(
                                    f"🔀 Updated active branch -> {state.branch}")

                            elif tool_name == "create_or_update_file" and "branch" in result:
                                state.branch = result["branch"]
                                print(
                                    f"📝 File modified on branch -> {state.branch}")

                            elif tool_name == "trigger_build" and "parameters" in tool_input:
                                branch_param = tool_input["parameters"].get(
                                    "BRANCH")
                                if branch_param:
                                    state.branch = branch_param
                                    print(
                                        f"🏗️ Build triggered for branch -> {state.branch}")
                            elif tool_name == "create_pull_request" and "number" in result:
                                state.pr_number = result.get("number")
                                print(
                                    f"📝 PR #{state.pr_number} created - will fetch summary after workflow")

                            if tool_name == "get_console_output" and "log" in result:
                                log_length = result.get(
                                    "total_length", len(result["log"]))
                                truncated = result.get("truncated", False)

                                print(f"\n📋 JENKINS CONSOLE LOG:")
                                print(f"   Total length: {log_length:,} chars")
                                print(f"   Truncated: {truncated}")
                                print(
                                    f"   Note: Raw log passed to Claude for language-agnostic analysis")

                            if tool_name == "get_coverage_report" and "coverage" in result:
                                if result.get("coverage_available"):
                                    coverage = result.get("coverage", {})
                                    state.update_coverage(coverage)
                                    print(f"\n📊 COVERAGE UPDATE:")
                                    print(state.get_coverage_summary())

                                    await emitter.emit_state_update(state.summary())
                                else:
                                    print(
                                        f"\n⚠️  Coverage not available: {result.get('message', 'Unknown reason')}")

                            result_str = json.dumps(result)

                            action_log.record(
                                iteration=iteration,
                                tool_name=tool_name,
                                tool_input=tool_input,
                                result=result,
                                success=True
                            )

                            if len(result_str) > 300:
                                print(
                                    f"✅ Success: {result_str[:300]}... [truncated]")
                            else:
                                print(f"✅ Success: {result_str}")

                            await emitter.emit_tool_result(
                                iteration=iteration,
                                tool_name=tool_name,
                                tool_use_id=tool_use_id,
                                success=True,
                                result=result
                            )

                        elif "error" in mcp_response:
                            result = {"error": mcp_response["error"]}
                            print(f"❌ Error: {result}")

                            action_log.record(
                                iteration=iteration,
                                tool_name=tool_name,
                                tool_input=tool_input,
                                result=result,
                                success=False
                            )

                            await emitter.emit_tool_result(
                                iteration=iteration,
                                tool_name=tool_name,
                                tool_use_id=tool_use_id,
                                success=False,
                                result=result,
                                error=str(mcp_response["error"])
                            )

                        else:
                            result = mcp_response

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result)
                        })

                    except Exception as e:
                        print(f"❌ Tool execution failed: {e}")

                        action_log.record(
                            iteration=iteration,
                            tool_name=tool_name,
                            tool_input=tool_input,
                            result={"error": str(e)},
                            success=False
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps({"error": str(e)})
                        })

            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                print(
                    f"📨 Sending {len(tool_results)} tool result(s) back to Claude...")

                if firestore_client and workflow_id:
                    await firestore_client.save_context(workflow_id, messages)

                await emitter.emit_state_update(state.summary())
        else:
            print(f"⚠️  Unexpected stop reason: {stop_reason}")
            break

    print(f"\n{'='*60}")
    print(f"Completed after {iteration} iterations")
    print(f"📊 Final message count: {len(messages)}")
    print(f"📋 Total actions logged: {len(action_log.entries)}")
    print(f"{'='*60}")

    if state.pr_number:
        pr_summary = await fetch_pr_summary_if_exists(
            repo_owner=REPO_OWNER,
            repo_name=REPO_NAME,
            branch=state.get_branch()
        )
        state.pr_summary = pr_summary

    workflow_duration = _time.time() - _workflow_start_time
    productivity = await analyze_workflow_productivity(
        action_log=action_log,
        workflow_duration_seconds=workflow_duration,
        iteration_count=iteration
    )
    if productivity:
        await emitter.emit_productivity_analysis(**productivity)

    await emitter.emit_workflow_complete(
        total_iterations=iteration,
        success=(iteration < max_iterations),
        reason="max_iterations_reached" if iteration >= max_iterations else "workflow_complete"
    )

    if firestore_client and workflow_id:
        final_status = 'completed' if iteration < max_iterations else 'failed'
        await firestore_client.update_workflow(workflow_id, {
            'status': final_status,
            'iteration': iteration,
            'prNumber': state.pr_number
        })

        print(f"💾 Final workflow status: {final_status}")

    return messages

if __name__ == "__main__":
    asyncio.run(run_full_test_repair_and_generation_workflow())
