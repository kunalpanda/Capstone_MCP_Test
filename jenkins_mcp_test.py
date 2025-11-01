import asyncio
import json
import websockets
import time

# --- CONFIGURATION ---
SERVER_URL = "ws://localhost:4001"
TEST_JOB_NAME = "test-job" # !!! REPLACE with a job name on your Jenkins server !!!
TEST_BUILD_NUMBER = 1          # !!! REPLACE with a valid build number for the job !!!
UNIQUE_ID = int(time.time())

# Base dictionary for tool arguments
TOOL_ARGS = {
    "job_name": TEST_JOB_NAME,
    "build_number": TEST_BUILD_NUMBER,
    "parameters": {"BRANCH": "main", "REVISION": f"test-{UNIQUE_ID}"}
}

async def send_tool_request(websocket, id_num, tool_name, arguments):
    """Helper function to send a tool request and print the response."""
    request = {
        "id": id_num,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    print(f"\n>>> Calling tool '{tool_name}' (ID: {id_num})...")
    await websocket.send(json.dumps(request))
    
    response = await websocket.recv()
    parsed_response = json.loads(response)
    print(f"<<< Received Response for '{tool_name}':")
    
    # Check for text content and handle JSON output gracefully
    result = parsed_response.get("result", {})
    if result.get("text"):
        print(f"Raw Text Output (truncated):\n{result['text'][:500]}...")
    else:
        print(json.dumps(parsed_response, indent=2))
        
    return parsed_response

async def test_jenkins_client():
    """Connects to the MCP server and tests all 8 tool functions."""
    
    print(f"Attempting to connect to {SERVER_URL}...")
    print(f"!!! Testing actions on job: {TEST_JOB_NAME} !!!")
    print("-" * 50)

    try:
        async with websockets.connect(SERVER_URL) as websocket:
            print("🟢 Connection successful!")
            
            # --- 1. Test "tools/list" method (Tool Discovery) ---
            print("\n>>> Requesting tool definitions (tools/list, ID: 1)...")
            list_tools_request = {
                "id": 1,
                "method": "tools/list",  # <--- Correct JSON-RPC method call
                "params": {}
            }
            await websocket.send(json.dumps(list_tools_request))

            response = await websocket.recv()
            parsed_response = json.loads(response)
            print("<<< Received Tool List Response (tools/list):")
            print(json.dumps(parsed_response, indent=2))
            
            if parsed_response.get("result", {}).get("tools"):
                print(f"✅ Successfully received {len(parsed_response['result']['tools'])} tool definitions.")
            
            # --- 2. Test 'list_jobs' ---
            await send_tool_request(websocket, 2, "list_jobs", {})

            # --- 3. Test 'get_job_info' ---
            await send_tool_request(websocket, 3, "get_job_info", {"job_name": TEST_JOB_NAME})

            # --- 4. Test 'get_build_info' ---
            await send_tool_request(websocket, 4, "get_build_info", {
                "job_name": TEST_JOB_NAME, 
                "build_number": TEST_BUILD_NUMBER
            })
            
            # --- 5. Test 'get_console_output' ---
            await send_tool_request(websocket, 5, "get_console_output", {
                "job_name": TEST_JOB_NAME, 
                "build_number": TEST_BUILD_NUMBER
            })
            
            # --- 6. Test 'trigger_build' ---
            await send_tool_request(websocket, 6, "trigger_build", {
                "job_name": TEST_JOB_NAME,
                "parameters": TOOL_ARGS["parameters"] 
            })
            
            # --- 7. Test 'get_queue_info' ---
            await send_tool_request(websocket, 7, "get_queue_info", {})

            # --- 8. Test 'get_job_config' ---
            await send_tool_request(websocket, 8, "get_job_config", {"job_name": TEST_JOB_NAME})
            
            # --- 9. Test 'update_job_config' (Skipped for safety) ---
            print("\nSkipping 'update_job_config' test as it requires full XML input.")


    except ConnectionRefusedError:
        print(f"\n❌ Connection failed: Ensure your Jenkins MCP server is running at {SERVER_URL}")
    except websockets.exceptions.ConnectionClosedOK:
        print("\n❌ Connection closed by server.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_jenkins_client())