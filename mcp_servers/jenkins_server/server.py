from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import tools
import os

app = FastAPI(title="Jenkins MCP Server")


@app.post("/")
async def handle_rpc(request: Request):
    payload = await request.json()
    method = payload.get("method")
    params = payload.get("params", {})
    req_id = payload.get("id")
    # Fall back to env vars if no per-request credential headers
    jenkins_token = (
        request.headers.get("X-Jenkins-Token")
        or os.getenv("JENKINS_TOKEN")
    )
    jenkins_url = (
        request.headers.get("X-Jenkins-URL")
        or os.getenv("JENKINS_URL")
    )
    jenkins_user = (
        request.headers.get("X-Jenkins-User")
        or os.getenv("JENKINS_USER")
    )
    try:
        if method == "tools/list":
            result = await tools.list_tools()

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("params", {})

            if not hasattr(tools, tool_name):
                raise ValueError(f"Tool '{tool_name}' not found")

            func = getattr(tools, tool_name)
            result = await func(
                jenkins_token=jenkins_token,
                jenkins_url=jenkins_url,
                jenkins_user=jenkins_user,
                **tool_params
            )

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
    return {"message": f"Jenkins MCP Server running (active branch: {branch})"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8010))
    uvicorn.run(app, host="0.0.0.0", port=port)
