# orchestrator/mcp_client.py
import httpx
import json
import uuid
import asyncio

async def call_mcp_tool(server_url: str, method: str, name: str = None, params: dict = None):
    """Generic JSON-RPC client for calling MCP tools."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": {}
    }

    if name:
        payload["params"]["name"] = name
    if params:
        payload["params"]["params"] = params

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(server_url, json=payload)
        response.raise_for_status()
        return response.json()
