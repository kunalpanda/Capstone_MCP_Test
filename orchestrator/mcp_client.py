import httpx
import json
import uuid
import asyncio


async def get_gcp_identity_token(audience: str) -> str:
    metadata_url = (
        f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
        f"?audience={audience}"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            metadata_url,
            headers={"Metadata-Flavor": "Google"}
        )
        response.raise_for_status()
        return response.text.strip()


async def call_mcp_tool(server_url: str, method: str, name: str = None, params: dict = None, headers: dict = None):
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

    try:
        token = await get_gcp_identity_token(audience=server_url)
        auth_headers = {"Authorization": f"Bearer {token}"}
    except Exception:
        auth_headers = {}  # fallback for local dev

    merged_headers = {**auth_headers, **(headers or {})}

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(server_url, json=payload, headers=merged_headers)
        response.raise_for_status()
        return response.json()
