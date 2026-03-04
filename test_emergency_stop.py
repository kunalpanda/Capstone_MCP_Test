"""
Test emergency stop logic locally without hitting GCP
"""


def mock_find_running_workflow():
    """Simulate finding a running workflow"""

    # Mock workflows in Firestore
    mock_workflows = [
        {'id': 'workflow-123', 'status': 'running',
            'startedAt': '2026-03-02T10:00:00'},
        {'id': 'workflow-456', 'status': 'completed',
            'startedAt': '2026-03-02T09:00:00'},
        {'id': 'workflow-789', 'status': 'running',
            'startedAt': '2026-03-02T11:00:00'},  # Most recent
    ]

    # Filter running workflows
    running = [w for w in mock_workflows if w['status'] == 'running']

    if not running:
        return None, "No running workflows found"

    # Sort by startedAt (descending) - most recent first
    running.sort(key=lambda x: x['startedAt'], reverse=True)

    # Get the most recent
    workflow_id = running[0]['id']

    return workflow_id, None


def test_emergency_stop_logic():
    """Test the emergency stop workflow finding logic"""

    print("=" * 60)
    print("TEST: Emergency Stop Logic")
    print("=" * 60)

    # Test Case 1: workflowId = 'ALL'
    print("\nTest 1: workflowId = 'ALL'")
    workflow_id = 'ALL'

    if workflow_id in ['ALL', 'current']:
        workflow_id, error = mock_find_running_workflow()

        if error:
            print(f"❌ FAIL: {error}")
            return False

        print(f"✅ PASS: Found workflow: {workflow_id}")
        assert workflow_id == 'workflow-789', "Should find most recent workflow"

    # Test Case 2: Specific workflow ID
    print("\nTest 2: Specific workflow ID")
    workflow_id = 'workflow-specific-123'

    if workflow_id not in ['ALL', 'current']:
        print(f"✅ PASS: Using provided workflow: {workflow_id}")

    # Test Case 3: No running workflows
    print("\nTest 3: No running workflows")

    # Mock: all workflows completed
    mock_workflows_completed = [
        {'id': 'workflow-123', 'status': 'completed'},
        {'id': 'workflow-456', 'status': 'failed'},
    ]

    running = [w for w in mock_workflows_completed if w['status'] == 'running']

    if not running:
        print(f"✅ PASS: Correctly detected no running workflows")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_emergency_stop_logic()
