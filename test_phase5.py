# test_phase5.py
"""
Test Phase 5: Verify Firestore persistence in orchestrator
"""
import asyncio
import os

# Set emulator
os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:9090'
os.environ['DEV_MODE'] = 'true'
os.environ['PROJECT_ID'] = 'test-project'

from orchestrator.state import WorkflowState
from orchestrator.firestore_client import get_firestore_client, generate_workflow_id

async def test_state_persistence():
    print("🧪 Testing Phase 5: State Persistence\n")
    
    # Generate workflow ID
    workflow_id = generate_workflow_id(
        repo="kunalpanda/test_banking_app",
        branch="test-branch",
        commit_sha="test123"
    )
    print(f"Generated workflow ID: {workflow_id}\n")
    
    # Initialize Firestore client
    client = get_firestore_client(project_id='test-project')
    
    # Test 1: Check idempotency (workflow shouldn't exist yet)
    print("Test 1: Check workflow doesn't exist...")
    exists = await client.workflow_exists(workflow_id)
    assert not exists, "Workflow shouldn't exist yet"
    print("✅ Pass: Workflow doesn't exist\n")
    
    # Test 2: Create workflow
    print("Test 2: Create workflow...")
    await client.create_workflow(workflow_id, {
        'repo': 'kunalpanda/test_banking_app',
        'branch': 'test-branch',
        'commitSha': 'test123',
        'status': 'running',
        'phase': 'init',
        'iteration': 0
    })
    print("✅ Pass: Workflow created\n")
    
    # Test 3: Verify workflow exists now
    print("Test 3: Verify workflow exists...")
    exists = await client.workflow_exists(workflow_id)
    assert exists, "Workflow should exist now"
    print("✅ Pass: Workflow exists\n")
    
    # Test 4: Create WorkflowState and save to Firestore
    print("Test 4: Save WorkflowState to Firestore...")
    state = WorkflowState()
    state.repo = 'kunalpanda/test_banking_app'
    state.branch = 'test-branch'
    state.phase = 'test_analysis'
    state.iteration = 5
    
    await state.save_to_firestore(workflow_id)
    print("✅ Pass: State saved\n")
    
    # Test 5: Read back and verify
    print("Test 5: Read back workflow state...")
    workflow_data = await client.get_workflow(workflow_id)
    print(f"Retrieved data: {workflow_data}\n")
    
    assert workflow_data['iteration'] == 5, "Iteration should be 5"
    assert workflow_data['phase'] == 'test_analysis', "Phase should be test_analysis"
    print("✅ Pass: State persisted correctly\n")
    
    # Test 6: Save and load context
    print("Test 6: Save and load Claude context...")
    messages = [
        {'role': 'user', 'content': 'Fix the failing tests'},
        {'role': 'assistant', 'content': 'I will analyze the test failures'}
    ]
    await client.save_context(workflow_id, messages)
    
    loaded_messages = await client.load_context(workflow_id)
    assert len(loaded_messages) == 2, "Should have 2 messages"
    print("✅ Pass: Context saved and loaded\n")
    
    # Test 7: Update workflow multiple times (simulate iterations)
    print("Test 7: Simulate multiple iterations...")
    for i in range(1, 4):
        await client.update_workflow(workflow_id, {
            'iteration': i,
            'status': 'running'
        })
        print(f"  Updated iteration {i}")
    
    workflow_data = await client.get_workflow(workflow_id)
    assert workflow_data['iteration'] == 3, "Should be at iteration 3"
    print("✅ Pass: Multiple updates work\n")
    
    # Test 8: Final status update
    print("Test 8: Update final status...")
    await client.update_workflow(workflow_id, {
        'status': 'completed',
        'iteration': 10
    })
    
    workflow_data = await client.get_workflow(workflow_id)
    assert workflow_data['status'] == 'completed', "Status should be completed"
    print("✅ Pass: Final status updated\n")
    
    print("="*60)
    print("🎉 ALL TESTS PASSED!")
    print("="*60)
    print("\nPhase 5 implementation is working correctly!")
    print("State is now persisted to Firestore instead of local files.")
    print("\n✅ Ready to move to Phase 6: Webhook Handler Service")

if __name__ == "__main__":
    asyncio.run(test_state_persistence())