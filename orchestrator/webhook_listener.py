from fastapi import FastAPI, Request
from orchestrator.orchestrator import run_workflow

app = FastAPI()

@app.post("/webhook/github")
async def github_webhook(request: Request):
    payload = await request.json()
    await run_workflow(payload)
    return {"status": "ok"}
