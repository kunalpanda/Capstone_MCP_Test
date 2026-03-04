"""
Verify that the correct code is deployed and in the right files
"""
import os


def check_file_contains(filepath, search_strings):
    """Check if file contains all search strings"""
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    missing = []
    for search_str in search_strings:
        if search_str not in content:
            missing.append(search_str)

    if missing:
        return False, f"Missing: {missing}"

    return True, "All found"


def verify_deployment():
    """Verify all code is in place"""

    print("=" * 60)
    print("CODE VERIFICATION")
    print("=" * 60)

    checks = [
        {
            'name': 'Webhook Handler - Emergency Stop',
            'file': 'webhook_handler/app.py',
            'contains': [
                '@app.post("/emergency-stop")',
                "where('status', '==', 'running')",
                'stopped_count',
                'workflow_ids'
            ]
        },
        {
            'name': 'Orchestrator - Stop Check',
            'file': 'orchestrator/orchestrator.py',
            'contains': [
                'EMERGENCY STOP CHECK',
                "workflow_doc = firestore_client.collection('workflows').document(workflow_id).get()",
                "if workflow_data.get('status') == 'stopped':",
            ]
        },
        {
            'name': 'Frontend - Emergency Button',
            'file': 'frontend/src/components/Header.tsx',
            'contains': [
                'handleEmergencyStop',
                'Emergency Stop',
                '/emergency-stop'
            ]
        }
    ]

    all_passed = True

    for check in checks:
        print(f"\n📁 {check['name']}")
        print(f"   File: {check['file']}")

        passed, message = check_file_contains(check['file'], check['contains'])

        if passed:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CODE VERIFIED!")
        print("=" * 60)
        print("\nAll emergency stop code is present:")
        print("  ✓ Webhook handler has stop-all logic")
        print("  ✓ Orchestrator has stop detection")
        print("  ✓ Frontend has stop button")
    else:
        print("❌ SOME CODE MISSING!")
        print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = verify_deployment()
    exit(0 if success else 1)
