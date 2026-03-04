"""
Test webhook filtering logic without running servers
"""

# Test 1: Branch Filter
print("=" * 60)
print("TEST 1: Branch Filter")
print("=" * 60)

test_cases = [
    {"ref": "refs/heads/main", "should_pass": True},
    {"ref": "refs/heads/fix-tests-123", "should_pass": False},
    {"ref": "refs/heads/feature/new-ui", "should_pass": False},
    {"ref": "refs/heads/develop", "should_pass": False},
]

for case in test_cases:
    ref = case["ref"]
    branch = ref.split('/')[-1] if '/' in ref else ref

    passed = (branch == 'main')

    status = "✅ PASS" if passed == case["should_pass"] else "❌ FAIL"
    action = "QUEUE" if passed else "IGNORE"

    print(f"{status} | Branch: {branch:20s} | Action: {action}")

# Test 2: Skip CI Detection
print("\n" + "=" * 60)
print("TEST 2: Skip CI Detection")
print("=" * 60)

skip_patterns = ['[skip ci]', '[ci skip]', '[skip-ci]', 'fix-tests-']

commit_messages = [
    {"msg": "Fix bug in authentication", "should_pass": True},
    {"msg": "[skip ci] Add new test file", "should_pass": False},
    {"msg": "Updated README [skip-ci]", "should_pass": False},
    {"msg": "Merge fix-tests-123 into main", "should_pass": False},
    {"msg": "Regular commit message", "should_pass": True},
]

for case in commit_messages:
    msg = case["msg"]
    msg_lower = msg.lower()

    has_skip = any(pattern in msg_lower for pattern in skip_patterns)
    passed = not has_skip

    status = "✅ PASS" if passed == case["should_pass"] else "❌ FAIL"
    action = "QUEUE" if passed else "IGNORE"

    print(f"{status} | Action: {action:6s} | Message: {msg[:40]}")

# Test 3: GitHub Merge Detection
print("\n" + "=" * 60)
print("TEST 3: GitHub Merge Detection")
print("=" * 60)

merge_cases = [
    {
        "committer": "github",
        "message": "Merge pull request #58 from fix-tests-123",
        "should_ignore": True
    },
    {
        "committer": "web-flow",
        "message": "Merge automated test PR",
        "should_ignore": True
    },
    {
        "committer": "kunalpanda",
        "message": "Regular commit",
        "should_ignore": False
    },
]

for case in merge_cases:
    committer = case["committer"].lower()
    message = case["message"].lower()

    is_github_merge = 'github' in committer or 'web-flow' in committer
    is_automated = 'automated' in message or 'fix-tests-' in message

    should_ignore = is_github_merge and is_automated

    status = "✅ PASS" if should_ignore == case["should_ignore"] else "❌ FAIL"
    action = "IGNORE" if should_ignore else "QUEUE"

    print(
        f"{status} | Action: {action:6s} | Committer: {case['committer']:12s} | Msg: {case['message'][:30]}")

# Test 4: Commit Message Tagging
print("\n" + "=" * 60)
print("TEST 4: GitHub MCP Commit Tagging")
print("=" * 60)

original_messages = [
    "Add new test file",
    "Update dependencies",
    "[skip ci] Already tagged"
]

for msg in original_messages:
    if not msg.startswith('[skip ci]'):
        tagged = f"[skip ci] {msg}"
    else:
        tagged = msg

    has_tag = tagged.startswith('[skip ci]')
    status = "✅ PASS" if has_tag else "❌ FAIL"

    print(f"{status} | Original: {msg:30s} → Tagged: {tagged}")

# Test 5: PR Title/Body Tagging
print("\n" + "=" * 60)
print("TEST 5: GitHub MCP PR Tagging")
print("=" * 60)

pr_cases = [
    {"title": "Fix failing tests", "body": "This PR fixes 5 tests"},
    {"title": "[Automated] Already tagged", "body": "Auto-generated"},
]

for case in pr_cases:
    title = case["title"]
    body = case["body"]

    # Tag title
    if not title.startswith('[Automated]'):
        tagged_title = f"[Automated] {title}"
    else:
        tagged_title = title

    # Tag body
    tagged_body = f"[skip ci] {body}"

    has_title_tag = tagged_title.startswith('[Automated]')
    has_body_tag = '[skip ci]' in tagged_body

    status = "✅ PASS" if (has_title_tag and has_body_tag) else "❌ FAIL"

    print(f"{status} | Title tagged: {has_title_tag} | Body tagged: {has_body_tag}")
    print(f"      Original: {title}")
    print(f"      Tagged:   {tagged_title}\n")

print("=" * 60)
print("🎉 ALL LOGIC TESTS COMPLETE!")
print("=" * 60)
