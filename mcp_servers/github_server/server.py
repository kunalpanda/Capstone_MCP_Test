# mcp_servers/github_server/server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from . import tools

app = FastAPI(title="GitHub MCP JSON-RPC Server")

@app.post("/")
async def handle_rpc(request: Request):
    """Main JSON-RPC 2.0 endpoint"""
    payload = await request.json()
    method = payload.get("method")
    params = payload.get("params", {})
    req_id = payload.get("id")

    try:
        # === 1. List tools ===
        if method == "tools/list":
            result = await tools.list_tools()

        # === 2. Call a specific tool ===
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("params", {})

            # Look up the requested tool dynamically
            if not hasattr(tools, tool_name):
                raise ValueError(f"Tool '{tool_name}' not found")

            func = getattr(tools, tool_name)
            result = await func(**tool_params)

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
                "id": req_id
            })

        return JSONResponse({"jsonrpc": "2.0", "result": result, "id": req_id})

    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": str(e)},
            "id": req_id
        })


@app.get("/")
async def root():
    import os
    branch = os.getenv("ACTIVE_BRANCH", "main")
    return {"message": f"GitHub MCP JSON-RPC Server running (active branch: {branch})"}
