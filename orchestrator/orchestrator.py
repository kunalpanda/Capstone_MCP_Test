import asyncio
import httpx

async def discovery_phase():
    print("\n🔍 [1] Discovery & Analysis Phase")
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://127.0.0.1:8010/tools/list_pr_files")
        print("Files discovered:", resp.json())

async def verification_phase():
    print("\n✅ [2] Verification Phase")
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://127.0.0.1:8020/trigger_job", params={"name": "integration-tests"})
        print("Jenkins response:", resp.json())

async def run_workflow():
    print("🚀 Starting Autonomous Test Generation Workflow...")
    await discovery_phase()
    await verification_phase()
    print("\n🎯 Workflow Complete.")

if __name__ == "__main__":
    asyncio.run(run_workflow())
