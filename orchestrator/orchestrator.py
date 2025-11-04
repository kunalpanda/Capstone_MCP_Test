# orchestrator/orchestrator.py
import asyncio
import json
import os
import httpx
from string import Template

from orchestrator.mcp_client import call_mcp_tool
from orchestrator.config import settings
from orchestrator.state import WorkflowState


# ======================================
# Configuration
# ======================================
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
PROMPT_FILE = "prompts/test_run.txt"

state = WorkflowState()


# ======================================
# Claude 4.5 Tool-Use Function
# ======================================
async def call_claude(messages: list, tools: list = None, system: str = None):
    """Send messages to Claude 4.5 with native tool-use support."""
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

    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers
        )
        
        if res.status_code != 200:
            print("❌ Claude API request failed.")
            print("Status code:", res.status_code)
            print("Response:", res.text)
            res.raise_for_status()
            
        return res.json()


# ======================================
# Flattened MCP Tool Definitions
# ======================================
# Add to TOOLS list
TOOLS = [
    # ========== GITHUB TOOLS - READ ==========
    {
        "name": "get_repo_info",
        "description": "Get detailed metadata for a specific GitHub repository including stars, forks, description, and default branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (username or org name)"},
                "repo": {"type": "string", "description": "Repository name"}
            },
            "required": ["owner", "repo"]
        }
    },
    {
        "name": "get_file_tree",
        "description": "Recursively list all files in a repository branch. Returns file paths for the entire repository structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "ref": {"type": "string", "description": "Git reference (branch name, tag, or commit SHA). Default is 'main'", "default": "main"}
            },
            "required": ["owner", "repo"]
        }
    },
    {
        "name": "get_file_content",
        "description": "Read the content of a specific file from a repository. Returns decoded file content as text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "File path within the repository (e.g., 'src/main.py')"},
                "ref": {"type": "string", "description": "Git reference (branch, tag, or commit). Default is 'main'", "default": "main"}
            },
            "required": ["owner", "repo", "path"]
        }
    },
    
    # ========== GITHUB TOOLS - WRITE ==========
    {
        "name": "create_branch",
        "description": "Create a new branch from an existing branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "branch_name": {"type": "string", "description": "Name for the new branch"},
                "from_branch": {"type": "string", "description": "Source branch to create from (default: main)", "default": "main"}
            },
            "required": ["owner", "repo", "branch_name"]
        }
    },
    {
        "name": "create_or_update_file",
        "description": "Create a new file or update an existing file in the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "File path (e.g., 'web/tests/new_test.py')"},
                "content": {"type": "string", "description": "Complete file content"},
                "message": {"type": "string", "description": "Commit message"},
                "branch": {"type": "string", "description": "Branch name (default: main)", "default": "main"}
            },
            "required": ["owner", "repo", "path", "content", "message"]
        }
    },
    {
        "name": "create_pull_request",
        "description": "Create a pull request to merge one branch into another.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description"},
                "head": {"type": "string", "description": "Source branch"},
                "base": {"type": "string", "description": "Target branch (default: main)", "default": "main"}
            },
            "required": ["owner", "repo", "title", "body", "head"]
        }
    },
    
    # ========== JENKINS TOOLS ==========
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
    }
]

# ======================================
# Tool Routing Helper
# ======================================
def get_server_for_tool(tool_name: str) -> str:
    """Determine which MCP server handles a given tool."""
    github_tools = {"get_repo_info", "get_file_tree", "get_file_content", "get_commit_diff"}
    jenkins_tools = {"get_build_info", "get_console_output"}
    
    if tool_name in github_tools:
        return settings.GITHUB_MCP_URL
    elif tool_name in jenkins_tools:
        return settings.JENKINS_MCP_URL
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# ======================================
# Main Orchestration Loop with Tool Execution
# ======================================
async def run_conversation_with_tools(initial_prompt: str, max_iterations: int = 5):
    """
    Run a multi-turn conversation with Claude, executing tools as requested.
    """
    # Initial message
    messages = [
        {
            "role": "user",
            "content": initial_prompt
        }
    ]
    
    system_prompt = (
        "You are an autonomous agent for software test analysis and improvement. "
        "Use the provided tools to explore repositories and analyze CI/CD pipelines. "
        "Always use exact tool names and required parameters."
    )
    
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"{'='*60}")
        
        # Call Claude
        print(f"🤖 Calling Claude (iteration {iteration})...")
        response = await call_claude(messages, tools=TOOLS, system=system_prompt)
        
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
                print(f"\n💬 Claude says:\n{block['text']}\n")
        
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
                    print(f"📦 Input: {json.dumps(tool_input, indent=2)}")
                    
                    try:
                        # Route to appropriate MCP server
                        server_url = get_server_for_tool(tool_name)
                        
                        # Call the MCP server
                        mcp_response = await call_mcp_tool(
                            server_url=server_url,
                            method="tools/call",
                            name=tool_name,
                            params=tool_input
                        )
                        
                        # Extract result from JSON-RPC response
                        if "result" in mcp_response:
                            result = mcp_response["result"]
                            print(f"✅ Success: {json.dumps(result, indent=2)[:300]}...")
                        elif "error" in mcp_response:
                            result = {"error": mcp_response["error"]}
                            print(f"❌ Error: {result}")
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
                print(f"📨 Sending {len(tool_results)} tool result(s) back to Claude...")
        else:
            print(f"⚠️  Unexpected stop reason: {stop_reason}")
            break
    
    print(f"\n{'='*60}")
    print(f"Completed after {iteration} iterations")
    print(f"{'='*60}")
    
    return messages


# ======================================
# Main Orchestrator Execution Flow
# ======================================
async def run_llm_workflow():
    print("🚀 Starting Claude MCP integration test...")
    print("="*60)

    # Load prompt template
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    # Prepare context
    context = {
        "OWNER": "kunalpanda",
        "REPO_NAME": "capstone_test_repo_1",
        "BRANCH": "main",
        "GITHUB_MCP_URL": settings.GITHUB_MCP_URL
    }

    # Replace template variables
    prompt = Template(base_prompt).safe_substitute(context)
    
    print("\n📝 Initial Prompt:")
    print("-"*60)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-"*60)

    # Run the conversation loop
    final_messages = await run_conversation_with_tools(prompt, max_iterations=10)
    
    print("\n✅ Workflow complete!")
    print(f"📊 Total messages exchanged: {len(final_messages)}")


if __name__ == "__main__":
    asyncio.run(run_llm_workflow())