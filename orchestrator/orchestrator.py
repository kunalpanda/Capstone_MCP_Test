# orchestrator/orchestrator.py
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
# jenkins_utils REMOVED - Claude now interprets raw console logs directly (language-agnostic)
from backend.event_emitter import EventEmitter

from orchestrator.firestore_client import get_firestore_client, generate_workflow_id


# ======================================
# Configuration
# ======================================
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY.strip(
) if settings.ANTHROPIC_API_KEY else None
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
PROMPT_FILE = "prompts/revised_prompt.txt"
REPO_OWNER = "kunalpanda"
REPO_NAME = "test_banking_app"

state = WorkflowState()
emitter = EventEmitter()


# ======================================
# Claude 4.5 Tool-Use Function
# ======================================
async def call_claude(messages: list, tools: list = None, system: str = None, max_retries: int = 5):
    """
    Send messages to Claude 4.5 with native tool-use support.

    Handles:
    - 429: Rate limit (waits for retry-after header)
    - 529: Overloaded (exponential backoff)
    """
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

                # Handle rate limit (429)
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

                # Handle overloaded (529)
                if res.status_code == 529:
                    # Exponential backoff: 10s, 20s, 40s, 80s, 160s
                    wait_time = 10 * (2 ** attempt)
                    print(
                        f"⚠️  API overloaded (529). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            "API overloaded - max retries exceeded. Try again later.")

                # Handle other errors
                if res.status_code != 200:
                    print(f"❌ Claude API request failed.")
                    print(f"Status code: {res.status_code}")
                    print(f"Response: {res.text}")
                    res.raise_for_status()

                return res.json()

        except httpx.HTTPStatusError as e:
            # Re-raise if not a retryable error or max retries reached
            if e.response.status_code not in (429, 529) or attempt == max_retries - 1:
                raise
            # Otherwise continue to next retry attempt


# Increased from 3
async def summarize_old_messages(messages: list, keep_recent: int = 6) -> list:
    """Keep more recent context and include tool results in summary"""
    if len(messages) <= keep_recent + 2:
        return messages

    # Keep initial message + last 6 exchanges (12 messages)
    initial_message = messages[0]
    old_messages = messages[1:-(keep_recent * 2)]
    recent_messages = messages[-(keep_recent * 2):]

    # Create DETAILED summary including tool results
    summary_parts = []
    current_branch = None
    files_modified = []

    for msg in old_messages:
        content = msg["content"]

        # Extract key information
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        result_content = block.get("content", "")
                        # Parse for branch names, file paths
                        if "branch_name" in result_content:
                            # Extract branch
                            pass
                        if "path" in result_content and "operation" in result_content:
                            # Track files modified
                            pass

    summary_message = {
        "role": "user",
        "content": f"""[WORKFLOW STATE SUMMARY]
        Current Branch: {current_branch or "unknown"}
        Files Modified: {", ".join(files_modified) if files_modified else "none"}
        Previous Actions: {len(old_messages)} steps completed
        Key Results: {"\n".join(summary_parts[:15])}
        """
    }

    return [initial_message, summary_message] + recent_messages


def truncate_tool_results(messages: list, max_result_length: int = 55000) -> list:
    """
    Truncate large tool results to prevent token overflow.

    Note: Increased to 55k to accommodate 50k console logs from Jenkins.
    Claude can handle ~100k tokens per request, so 55k chars (~14k tokens) is safe.
    """
    truncated_messages = []

    for msg in messages:
        if msg["role"] == "user" and isinstance(msg["content"], list):
            # Process tool results
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

# ======================================
# Flattened MCP Tool Definitions
# ======================================
# Add to TOOLS list

# ======================================
# Dynamic Tool Discovery from MCP Servers
# ======================================


async def fetch_all_tools():
    """
    Dynamically fetch tool definitions from all MCP servers.
    Returns tuple of (tools_list, tool_to_server_map)
    """
    all_tools = []
    tool_to_server = {}  # Maps tool_name -> server_url

    # Define MCP servers to query
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
                    all_tools.extend(server_tools)

                    # Build routing map: tool_name -> server_url
                    for tool in server_tools:
                        tool_name = tool["name"]
                        if tool_name in tool_to_server:
                            print(
                                f"   ⚠️  Warning: Tool '{tool_name}' provided by multiple servers")
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
    """
    Injects the currently active branch into any GitHub or Jenkins tool params
    when missing. Prevents Claude from reverting to 'main'.
    """
    if not isinstance(params, dict):
        return params

    active = state.get_branch()

    # GitHub write/read tools
    if "branch" in params and not params["branch"]:
        params["branch"] = active
    if "ref" in params and not params["ref"]:
        params["ref"] = active

    # Jenkins trigger
    if "parameters" in params and isinstance(params["parameters"], dict):
        params["parameters"].setdefault("BRANCH", active)

    return params


async def fetch_pr_summary_if_exists(repo_owner: str, repo_name: str, branch: str):
    """
    After workflow completion, search for PR from the branch and fetch its summary.
    Returns PR details including body (Claude's summary) or None if no PR found.
    """
    try:
        # Step 1: List open PRs for the repo to find PR number
        # Note: GitHub MCP doesn't have list_prs, so we'll search by branch
        # We can infer the PR was just created, so it should be the latest

        # Alternative: Track PR number when it's created
        # For now, let's use the state to track it

        if not state.pr_number:
            print("ℹ️  No PR number tracked - PR may not have been created")
            return None

        print(f"\n{'='*60}")
        print(f"📥 Fetching PR #{state.pr_number} summary...")
        print(f"{'='*60}")

        # Fetch PR details using existing GitHub MCP tool
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

        # Display in CLI
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

        # Emit to dashboard
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


async def fetch_baseline_coverage(job_name: str) -> dict:
    """
    Fetch initial coverage report from Jenkins to establish baseline.

    Returns:
        Dictionary with coverage data or empty dict if unavailable
    """
    try:
        print(f"\n{'='*60}")
        print("📊 FETCHING BASELINE COVERAGE")
        print(f"{'='*60}")

        # Call Jenkins MCP to get coverage
        result = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="get_coverage_report",
            params={"job_name": job_name}
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


# =========================================================
# GENERATION WORKFLOW ENTRY
# =========================================================
async def run_full_test_repair_and_generation_workflow(
    workflow_id: str = None,
    repo: str = None,
    branch: str = None,
    commit_sha: str = None
):
    """
    Complete autonomous CI/CD cycle:
    1. Identify failing tests on main branch via Jenkins
    2. Analyze repository structure & failures
    3. Fix failing tests (test files only, never edit implementation)
    4. Generate new integration tests
    5. Verify via Jenkins
    6. Document results & reasoning

    Args:
        workflow_id: Pre-generated workflow ID from webhook (optional)
        repo: Repository full name (e.g., "kunalpanda/test_banking_app")
        branch: Branch name to work on
        commit_sha: Commit SHA from webhook
    """

    await emitter.emit_workflow_start(
        repo_owner=REPO_OWNER,
        repo_name=REPO_NAME,
        branch="main",
        max_iterations=50
    )

    # === Use provided workflow ID or generate new one ===
    if not workflow_id:
        # Generate workflow ID if not provided (for local/manual runs)
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

    # Get Firestore client
    firestore_client = get_firestore_client(project_id=settings.PROJECT_ID)

    # Create initial workflow record in Firestore
    # NOTE: Webhook handler no longer creates this - orchestrator does it
    await firestore_client.create_workflow(workflow_id, {
        'repo': f"{REPO_OWNER}/{REPO_NAME}",
        'branch': 'main',
        'commitSha': commit_sha or 'initial-run',
        'status': 'running',
        'phase': state.phase,
        'iteration': 0,
        'triggeredBy': 'webhook' if commit_sha else 'manual'
    })

    # Initialize baseline_coverage variable BEFORE try block
    baseline_coverage = {}

    print("🚦 Running initial Jenkins build on main branch to detect failing tests...")
    try:
        # Step 1: Trigger Jenkins build on main
        trigger_resp = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="trigger_build",
            params={"job_name": "test_banking_app",
                    "parameters": {"BRANCH": "main"}}
        )
        print(
            f"✅ Triggered main branch build: {json.dumps(trigger_resp, indent=2)}")

        # Step 2: Retrieve latest build info
        build_info = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="get_build_info",
            params={"job_name": "test_banking_app"}
        )

        if "result" not in build_info:
            raise RuntimeError(
                f"Unexpected response from Jenkins MCP: {build_info}")

        build_number = build_info["result"]["build_number"]
        build_status = build_info["result"]["status"]

        print(f"📄 Latest Jenkins build #{build_number} status: {build_status}")

        # NEW: Wait for this specific build to finish before reading test results
        print(f"⏳ Waiting for Jenkins build #{build_number} to complete...")

        build_completion = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="wait_for_build_completion",
            params={
                "job_name": "test_banking_app",
                "build_number": build_number,
                "timeout_seconds": 600,
                "poll_interval": 10,
            },
        )

        if "result" not in build_completion:
            raise RuntimeError(
                f"Unexpected response from wait_for_build_completion: {build_completion}")

        # Update build_status based on the completed build
        build_status = build_completion["result"]["result"]
        print(
            f"📄 Jenkins build #{build_number} completed with status: {build_status}")

        # Step 3: Get test results
        test_results = await call_mcp_tool(
            server_url=settings.JENKINS_MCP_URL,
            method="tools/call",
            name="get_test_results",
            params={"job_name": "test_banking_app",
                    "build_number": build_number}
        )
        print(f"🧪 Test Results: {json.dumps(test_results, indent=2)[:800]}...")

        # Step 4: Prepare initial context for Claude
        base_prompt = open(PROMPT_FILE, "r", encoding="utf-8").read()
        context = {
            "OWNER": REPO_OWNER,
            "REPO_NAME": REPO_NAME,
            "DEFAULT_BRANCH": "main",
            "BRANCH": "main",
            "INITIAL_BUILD": build_number,
            "INITIAL_STATUS": build_status,
            "TEST_RESULTS": json.dumps(test_results["result"], indent=2) if "result" in test_results else "{}",

            # Coverage metrics
            "TARGET_LINE_COVERAGE": settings.TARGET_LINE_COVERAGE,
            "TARGET_BRANCH_COVERAGE": settings.TARGET_BRANCH_COVERAGE,
            "TARGET_METHOD_COVERAGE": settings.TARGET_METHOD_COVERAGE,
            "BASELINE_LINE_COVERAGE": baseline_coverage.get("line", "N/A") if baseline_coverage else "N/A",
            "BASELINE_BRANCH_COVERAGE": baseline_coverage.get("branch", "N/A") if baseline_coverage else "N/A",
            "BASELINE_METHOD_COVERAGE": baseline_coverage.get("method", "N/A") if baseline_coverage else "N/A",
        }

        # Build the final prompt
        from string import Template
        prompt = Template(base_prompt).safe_substitute(context)

        # Append explicit workflow instructions
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

        # Initialize target coverage from config
        state.target_coverage = {
            "line": settings.TARGET_LINE_COVERAGE,
            "branch": settings.TARGET_BRANCH_COVERAGE,
            "method": settings.TARGET_METHOD_COVERAGE
        }
        print(f"🎯 Coverage targets set: Line={settings.TARGET_LINE_COVERAGE}%, "
              f"Branch={settings.TARGET_BRANCH_COVERAGE}%, "
              f"Method={settings.TARGET_METHOD_COVERAGE}%")

        # Fetch baseline coverage from Jenkins
        baseline_coverage = await fetch_baseline_coverage(job_name="test_banking_app")
        if baseline_coverage:
            state.update_coverage(baseline_coverage)
            print(state.get_coverage_summary())

        # Emit initial coverage to frontend
        await emitter.emit_state_update(state.summary())

        print("\n🧠 Launching full repair + generation workflow...\n")
        await run_conversation_with_tools(
            prompt,
            max_iterations=50,
            tools=tools,
            tool_to_server=tool_to_server,  # Pass routing map
            workflow_id=workflow_id,        # Pass workflow ID
            firestore_client=firestore_client  # Pass Firestore client
        )

    except Exception as e:
        print(f"❌ Workflow failed: {e}")

        await emitter.emit_error(
            error_type=type(e).__name__,
            error_message=str(e),
            context={"function": "run_full_test_repair_and_generation_workflow"}
        )

        raise


# ======================================
# Main Orchestration Loop with Tool Execution
# ======================================
async def run_conversation_with_tools(
        initial_prompt: str,
        max_iterations: int = 50,
        tools: list = None,
        tool_to_server: dict = None,
        workflow_id: str = None,
        firestore_client=None
):
    """
    Run a multi-turn conversation with Claude, executing tools as requested.
    Now with message management to avoid rate limits.

    Args:
        initial_prompt: The initial prompt to send to Claude
        max_iterations: Maximum number of conversation turns
        tools: List of tool definitions. If None, will be fetched dynamically.
    """
    # Fetch tools dynamically if not provided
    if tools is None or tool_to_server is None:
        print("🔄 Tools not provided - fetching from MCP servers...")
        tools, tool_to_server = await fetch_all_tools()
        if not tools or not tool_to_server:
            raise RuntimeError("Failed to fetch tools from MCP servers")

    # Initial message
    messages = [
        {
            "role": "user",
            "content": initial_prompt
        }
    ]

    system_prompt = (
        "You are an autonomous agent for software test analysis and improvement. "
        "CRITICAL STATE TRACKING:\n"
        "- Always note which branch you're working on\n"
        "- After updating files, VERIFY changes with get_file_content\n"
        "- Before triggering builds, confirm the branch name\n"
        "- If tests fail repeatedly, read back your changes to debug\n"
        "- Document your current state in each response\n\n"
        "Use the provided tools to explore repositories and analyze CI/CD pipelines. "
        "Be concise but track state carefully."
    )

    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        print(
            f"🔍 DEBUG: Starting iteration {iteration}, checking stop flag for workflow {workflow_id}")

        # ============================================
        # EMERGENCY STOP CHECK
        # ============================================
        if firestore_client and workflow_id:
            try:
                # Use the FirestoreClient wrapper methods
                workflow_data = await firestore_client.get_workflow(workflow_id)

                if workflow_data and workflow_data.get('status') == 'stopped':
                    print(
                        f"\n🛑 EMERGENCY STOP detected for workflow {workflow_id}")
                    print(
                        f"   Stop reason: {workflow_data.get('stopReason', 'Unknown')}")
                    print(f"   Iteration: {iteration}/{max_iterations}")
                    print(f"✅ Workflow halted gracefully\n")

                    # Update final state
                    await emitter.emit_workflow_complete(
                        total_iterations=iteration,
                        success=False,
                        reason="emergency_stop"
                    )

                    # Set final status
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
                # Continue anyway - don't fail workflow just because of stop check

        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"{'='*60}")

        await emitter.emit_iteration_start(iteration, max_iterations)

        # === Update Firestore at start of iteration ===
        if firestore_client and workflow_id:
            await firestore_client.update_workflow(workflow_id, {
                'iteration': iteration,
                'phase': state.phase,
                'status': 'running'
            })

        # Truncate large tool results BEFORE sending
        messages = truncate_tool_results(messages)

        # Summarize old messages if conversation is getting long
        if len(messages) > 10:
            print(
                f"📊 Message count: {len(messages)} - Summarizing old messages...")
            messages = await summarize_old_messages(messages, keep_recent=3)
            print(f"📊 After summarization: {len(messages)} messages")

        # Call Claude with retry logic
        print(f"🤖 Calling Claude (iteration {iteration})...")
        try:
            response = await call_claude(messages, tools=tools, system=system_prompt)
            # === Save context after Claude response ===
            if firestore_client and workflow_id:
                await firestore_client.save_context(workflow_id, messages)

        except Exception as e:
            print(f"❌ Failed to call Claude: {e}")
            print(f"💡 Consider reducing max_iterations or message history length")
            break

        # Add Claude's response to message history
        assistant_message = {
            "role": "assistant",
            "content": response["content"]
        }
        messages.append(assistant_message)

        # Check stop reason
        stop_reason = response.get("stop_reason")
        print(f"⏸️  Stop reason: {stop_reason}")

        # Display text content
        for block in response["content"]:
            if block["type"] == "text":
                text = block["text"]
                # Truncate long text for display
                if len(text) > 500:
                    print(f"\n💬 Claude says:\n{text[:500]}...\n[truncated]\n")
                else:
                    print(f"\n💬 Claude says:\n{text}\n")

        await emitter.emit_claude_response(
            iteration=iteration,
            stop_reason=stop_reason,
            content=response["content"]
        )

        # If no tool use, we're done
        if stop_reason == "end_turn":
            print("✅ Conversation complete - no more tool requests")
            break

        # Process tool calls
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
                        # Route to appropriate MCP server dynamically
                        server_url = tool_to_server.get(tool_name)

                        if server_url is None:
                            raise ValueError(
                                f"Unknown tool '{tool_name}' - not provided by any MCP server")

                        # Call the MCP server
                        mcp_response = await call_mcp_tool(
                            server_url=server_url,
                            method="tools/call",
                            name=tool_name,
                            params=enforce_branch(tool_input)
                        )

                        # Extract result from JSON-RPC response
                        if "result" in mcp_response:
                            result = mcp_response["result"]

                            # === Branch tracking ===
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

                            # CONSOLE OUTPUT: Pass raw log directly to Claude (language-agnostic)
                            # The Jenkins MCP server now handles smart truncation at 50k chars
                            # Claude interprets the raw output - no regex parsing needed
                            if tool_name == "get_console_output" and "log" in result:
                                log_length = result.get(
                                    "total_length", len(result["log"]))
                                truncated = result.get("truncated", False)

                                print(f"\n📋 JENKINS CONSOLE LOG:")
                                print(f"   Total length: {log_length:,} chars")
                                print(f"   Truncated: {truncated}")
                                print(
                                    f"   Note: Raw log passed to Claude for language-agnostic analysis")

                            # COVERAGE TRACKING: Update state when Claude checks coverage
                            if tool_name == "get_coverage_report" and "coverage" in result:
                                if result.get("coverage_available"):
                                    coverage = result.get("coverage", {})
                                    state.update_coverage(coverage)
                                    print(f"\n📊 COVERAGE UPDATE:")
                                    print(state.get_coverage_summary())

                                    # Emit updated coverage to frontend
                                    await emitter.emit_state_update(state.summary())
                                else:
                                    print(
                                        f"\n⚠️  Coverage not available: {result.get('message', 'Unknown reason')}")

                            result_str = json.dumps(result)

                            # Log truncated result
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

                        # Add to tool results
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result)
                        })

                    except Exception as e:
                        print(f"❌ Tool execution failed: {e}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps({"error": str(e)})
                        })

            # Send tool results back to Claude
            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                print(
                    f"📨 Sending {len(tool_results)} tool result(s) back to Claude...")

                # === Save context after tool results ===
                if firestore_client and workflow_id:
                    await firestore_client.save_context(workflow_id, messages)

                await emitter.emit_state_update(state.summary())
        else:
            print(f"⚠️  Unexpected stop reason: {stop_reason}")
            break

    print(f"\n{'='*60}")
    print(f"Completed after {iteration} iterations")
    print(f"📊 Final message count: {len(messages)}")
    print(f"{'='*60}")

    if state.pr_number:
        pr_summary = await fetch_pr_summary_if_exists(
            repo_owner=REPO_OWNER,
            repo_name=REPO_NAME,
            branch=state.get_branch()
        )
        state.pr_summary = pr_summary

    await emitter.emit_workflow_complete(
        total_iterations=iteration,
        success=(iteration < max_iterations),
        reason="max_iterations_reached" if iteration >= max_iterations else "workflow_complete"
    )

    # === Update final status in Firestore ===
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
