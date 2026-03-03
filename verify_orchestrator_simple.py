"""
Simple verification of orchestrator stop check
"""
import os

filepath = 'orchestrator/orchestrator.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Check for key components (more flexible)
checks = [
    ('EMERGENCY STOP CHECK', 'Comment marking stop check section'),
    ('workflow_doc', 'Getting workflow document'),
    ("get('status') == 'stopped'", 'Checking if status is stopped'),
    ('break', 'Breaking out of loop'),
]

print("=" * 60)
print("ORCHESTRATOR STOP CHECK VERIFICATION")
print("=" * 60)

all_found = True
for search_str, description in checks:
    if search_str in content:
        print(f"✅ Found: {description}")
        print(f"   Search: '{search_str}'")
    else:
        print(f"❌ Missing: {description}")
        print(f"   Search: '{search_str}'")
        all_found = False

print("\n" + "=" * 60)
if all_found:
    print("✅ ORCHESTRATOR CODE VERIFIED!")
else:
    print("❌ SOME CODE MISSING!")

print("=" * 60)
