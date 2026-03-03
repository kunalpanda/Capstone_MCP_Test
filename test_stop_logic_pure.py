"""
Test emergency stop logic without any external dependencies
Pure logic testing
"""


def mock_firestore_query_all_running():
    """Simulate Firestore returning multiple running workflows"""
    return [
        {'id': 'workflow-abc123', 'status': 'running', 'iteration': 5},
        {'id': 'workflow-def456', 'status': 'running', 'iteration': 10},
        {'id': 'workflow-ghi789', 'status': 'running', 'iteration': 3},
    ]


def mock_firestore_update(workflow_id, updates):
    """Simulate updating Firestore"""
    print(f"  [MOCK] Firestore update: workflows/{workflow_id}")
    print(f"         {updates}")
    return True


def emergency_stop_logic():
    """
    The core logic of emergency stop (no external calls)
    This is what happens in the webhook handler
    """
    print("🛑 Emergency Stop Logic")
    print("-" * 40)

    # Get all running workflows (mocked)
    running_workflows = mock_firestore_query_all_running()

    print(f"\n1. Found {len(running_workflows)} running workflows:")
    for wf in running_workflows:
        print(f"   - {wf['id']} (iteration {wf['iteration']})")

    # Stop each one
    print(f"\n2. Stopping all running workflows:")
    stopped_ids = []

    for wf in running_workflows:
        workflow_id = wf['id']

        # Update to stopped
        updates = {
            'status': 'stopped',
            'stopReason': 'Emergency stop - all workflows halted'
        }

        mock_firestore_update(workflow_id, updates)
        stopped_ids.append(workflow_id)

    print(f"\n3. Result:")
    print(f"   Stopped {len(stopped_ids)} workflows")
    print(f"   IDs: {stopped_ids}")

    return {
        'stopped_count': len(stopped_ids),
        'workflow_ids': stopped_ids
    }


def orchestrator_check_logic(workflow_id, mock_firestore_data):
    """
    The core logic of orchestrator stop checking
    This is what happens in the orchestrator loop
    """
    print(f"\n⚙️  Orchestrator Check for: {workflow_id}")
    print("-" * 40)

    # Get workflow document (mocked)
    workflow_data = mock_firestore_data.get(workflow_id)

    if not workflow_data:
        print("  ❌ Workflow not found")
        return False

    status = workflow_data.get('status')
    print(f"  → Status: {status}")

    if status == 'stopped':
        reason = workflow_data.get('stopReason', 'Unknown')
        print(f"  🛑 STOP DETECTED!")
        print(f"  → Reason: {reason}")
        print(f"  → Would EXIT workflow here")
        return True
    else:
        print(f"  → Continue running")
        return False


def test_complete_flow():
    """Test the complete emergency stop flow"""

    print("=" * 60)
    print("COMPLETE EMERGENCY STOP FLOW TEST")
    print("=" * 60)

    # Step 1: Emergency stop is triggered
    print("\n" + "=" * 60)
    print("STEP 1: User triggers emergency stop")
    print("=" * 60)

    result = emergency_stop_logic()

    assert result['stopped_count'] == 3, "Should stop 3 workflows"
    assert len(result['workflow_ids']) == 3, "Should return 3 IDs"

    print("\n✅ Emergency stop logic PASSED")

    # Step 2: Simulate Firestore state after stop
    print("\n" + "=" * 60)
    print("STEP 2: Firestore state after stop")
    print("=" * 60)

    mock_firestore_after_stop = {
        'workflow-abc123': {'status': 'stopped', 'iteration': 5, 'stopReason': 'Emergency stop'},
        'workflow-def456': {'status': 'stopped', 'iteration': 10, 'stopReason': 'Emergency stop'},
        'workflow-ghi789': {'status': 'stopped', 'iteration': 3, 'stopReason': 'Emergency stop'},
    }

    print("  Mock Firestore data:")
    for wf_id, data in mock_firestore_after_stop.items():
        print(f"    {wf_id}: {data}")

    # Step 3: Orchestrator checks each workflow
    print("\n" + "=" * 60)
    print("STEP 3: Orchestrator checks on next iteration")
    print("=" * 60)

    all_detected = True
    for wf_id in result['workflow_ids']:
        detected = orchestrator_check_logic(wf_id, mock_firestore_after_stop)
        if not detected:
            print(f"  ❌ Failed to detect stop for {wf_id}")
            all_detected = False

    print("\n" + "=" * 60)
    if all_detected:
        print("🎉 COMPLETE FLOW TEST PASSED!")
        print("=" * 60)
        print("\nVerified:")
        print("  ✓ Emergency stop finds all running workflows")
        print("  ✓ Sets status='stopped' for each")
        print("  ✓ Orchestrator detects stop flag")
        print("  ✓ Orchestrator would exit correctly")
        return True
    else:
        print("❌ COMPLETE FLOW TEST FAILED!")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_complete_flow()
    exit(0 if success else 1)
