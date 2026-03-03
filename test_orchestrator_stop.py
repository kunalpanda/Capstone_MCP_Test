"""
Test orchestrator emergency stop detection logic
"""


def mock_orchestrator_stop_check(workflow_id, firestore_data):
    """Simulate orchestrator checking for stop flag"""

    # Simulate getting workflow document
    workflow_doc = firestore_data.get(workflow_id)

    if not workflow_doc:
        return False, "Workflow not found"

    # Check if status is 'stopped'
    if workflow_doc.get('status') == 'stopped':
        return True, f"STOP detected for {workflow_id}"

    return False, "Continue running"


def test_orchestrator_logic():
    """Test orchestrator stop detection"""

    print("=" * 60)
    print("TEST: Orchestrator Stop Detection")
    print("=" * 60)

    # Mock Firestore data
    mock_firestore = {
        'workflow-123': {'status': 'running', 'iteration': 5},
        'workflow-456': {'status': 'stopped', 'iteration': 10, 'stopReason': 'User stop'},
        'workflow-789': {'status': 'completed', 'iteration': 50},
    }

    # Test Case 1: Running workflow (should NOT stop)
    print("\nTest 1: Running workflow")
    should_stop, message = mock_orchestrator_stop_check(
        'workflow-123', mock_firestore)
    print(f"  Workflow: workflow-123")
    print(f"  Should stop: {should_stop}")
    print(f"  Message: {message}")
    assert should_stop == False, "Running workflow should NOT stop"
    print("  ✅ PASS")

    # Test Case 2: Stopped workflow (should STOP)
    print("\nTest 2: Stopped workflow")
    should_stop, message = mock_orchestrator_stop_check(
        'workflow-456', mock_firestore)
    print(f"  Workflow: workflow-456")
    print(f"  Should stop: {should_stop}")
    print(f"  Message: {message}")
    assert should_stop == True, "Stopped workflow should STOP"
    print("  ✅ PASS")

    # Test Case 3: Completed workflow (should NOT stop - already done)
    print("\nTest 3: Completed workflow")
    should_stop, message = mock_orchestrator_stop_check(
        'workflow-789', mock_firestore)
    print(f"  Workflow: workflow-789")
    print(f"  Should stop: {should_stop}")
    print(f"  Message: {message}")
    assert should_stop == False, "Completed workflow should NOT stop"
    print("  ✅ PASS")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    test_orchestrator_logic()
