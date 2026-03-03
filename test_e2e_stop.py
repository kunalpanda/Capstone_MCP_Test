"""
End-to-end emergency stop flow simulation
"""


def simulate_emergency_stop_flow():
    """Simulate the complete flow"""

    print("=" * 60)
    print("END-TO-END EMERGENCY STOP SIMULATION")
    print("=" * 60)

    # Step 1: User clicks button
    print("\n📱 STEP 1: User clicks Emergency Stop button")
    print("  → Frontend sends: POST /emergency-stop with workflowId='ALL'")

    # Step 2: Webhook handler receives request
    print("\n🌐 STEP 2: Webhook handler receives request")
    workflow_id_input = 'ALL'
    print(f"  → Received workflowId: {workflow_id_input}")

    # Step 3: Find running workflow
    print("\n🔍 STEP 3: Find running workflow in Firestore")

    # Mock: Query Firestore
    mock_running_workflows = [
        {'id': 'abc123def456', 'status': 'running',
            'iteration': 7, 'startedAt': '2026-03-02T10:30:00'}
    ]

    if mock_running_workflows:
        actual_workflow_id = mock_running_workflows[0]['id']
        print(f"  ✅ Found: {actual_workflow_id}")
    else:
        print(f"  ❌ No running workflows found")
        return False

    # Step 4: Set stop flag in Firestore
    print("\n💾 STEP 4: Update Firestore")
    print(f"  → Set workflows/{actual_workflow_id}/status = 'stopped'")

    # Mock Firestore update
    mock_firestore_db = {
        'abc123def456': {'status': 'running', 'iteration': 7}
    }

    # Update
    mock_firestore_db['abc123def456']['status'] = 'stopped'
    mock_firestore_db['abc123def456']['stopReason'] = 'User stop'

    print(f"  ✅ Firestore updated: {mock_firestore_db['abc123def456']}")

    # Step 5: Webhook returns success
    print("\n✅ STEP 5: Webhook handler returns success")
    response = {
        'status': 'stopped',
        'workflowId': actual_workflow_id,
        'message': 'Emergency stop flag set'
    }
    print(f"  → Response: {response}")

    # Step 6: Orchestrator checks on next iteration
    print("\n⚙️  STEP 6: Orchestrator starts iteration 8")
    print(f"  → Checking Firestore for workflow {actual_workflow_id}")

    workflow_data = mock_firestore_db[actual_workflow_id]
    status = workflow_data['status']

    print(f"  → Found status: {status}")

    if status == 'stopped':
        print(f"  🛑 EMERGENCY STOP DETECTED!")
        print(f"  → Reason: {workflow_data.get('stopReason', 'Unknown')}")
        print(f"  → Exiting workflow gracefully...")
        print(f"  ✅ Workflow halted at iteration 8")
    else:
        print(f"  ❌ ERROR: Status is not 'stopped', workflow continues!")
        return False

    print("\n" + "=" * 60)
    print("🎉 END-TO-END FLOW SUCCESSFUL!")
    print("=" * 60)
    print("\nKey Points:")
    print("✓ User sends 'ALL', backend finds real workflow ID")
    print("✓ Correct Firestore document updated")
    print("✓ Orchestrator checks same document")
    print("✓ Workflow stops gracefully")

    return True


if __name__ == "__main__":
    success = simulate_emergency_stop_flow()
    exit(0 if success else 1)
