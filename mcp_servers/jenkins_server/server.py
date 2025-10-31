from fastapi import FastAPI
from . import tools

app = FastAPI(title="Jenkins MCP Server")

@app.get("/")
async def root():
    return {"message": "Jenkins MCP Server is running"}

@app.get("/trigger_job")
async def trigger_job(name: str = "default-job"):
    return {"message": f"Triggered Jenkins job '{name}'"}
