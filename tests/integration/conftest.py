"""
Shared fixtures for integration tests.

All tests use mocks for external services (GCP, GitHub API, Jenkins API,
Anthropic API) so they can run without credentials or network access.
"""
import os
import sys
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Make the repo root importable
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ---------------------------------------------------------------------------
# Set required env vars BEFORE any application module is imported
# ---------------------------------------------------------------------------
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-fake")
os.environ.setdefault("GITHUB_TOKEN", "ghp_test_token_fake")
os.environ.setdefault("JENKINS_TOKEN", "test-jenkins-token")
os.environ.setdefault("JENKINS_URL", "http://jenkins.test:8080")
os.environ.setdefault("JENKINS_USER", "admin")
os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("GITHUB_MCP_URL", "http://localhost:8010")
os.environ.setdefault("JENKINS_MCP_URL", "http://localhost:8020")
os.environ.setdefault("PUBSUB_EMULATOR_HOST", "localhost:8085")
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8086")


# ---------------------------------------------------------------------------
# Event loop fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Workflow state fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_state():
    """Return a brand-new WorkflowState for each test."""
    from orchestrator.state import WorkflowState
    return WorkflowState()


# ---------------------------------------------------------------------------
# Mock Firestore client
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_firestore_client():
    """Provide a mock FirestoreClient that doesn't need a real Firestore."""
    client = AsyncMock()
    client.create_workflow = AsyncMock()
    client.get_workflow = AsyncMock(return_value=None)
    client.update_workflow = AsyncMock()
    client.workflow_exists = AsyncMock(return_value=False)
    client.add_event = AsyncMock(return_value="evt-123")
    client.get_recent_events = AsyncMock(return_value=[])
    client.save_context = AsyncMock()
    client.load_context = AsyncMock(return_value=None)
    return client


# ---------------------------------------------------------------------------
# Mock MCP tool call
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_mcp_call():
    """Return a patchable AsyncMock for orchestrator.mcp_client.call_mcp_tool."""
    return AsyncMock(return_value={"result": {"tools": []}})


# ---------------------------------------------------------------------------
# Sample webhook payloads
# ---------------------------------------------------------------------------
@pytest.fixture
def github_push_payload():
    """Realistic GitHub push webhook payload."""
    return {
        "ref": "refs/heads/main",
        "after": "abc123def456",
        "repository": {
            "full_name": "kunalpanda/test_banking_app",
            "name": "test_banking_app",
            "owner": {"login": "kunalpanda"},
        },
        "head_commit": {
            "message": "Update README",
            "committer": {"name": "Kunal", "email": "kunal@example.com"},
        },
    }


@pytest.fixture
def github_push_skip_ci_payload():
    """Payload whose commit message includes [skip ci]."""
    return {
        "ref": "refs/heads/main",
        "after": "abc123def456",
        "repository": {
            "full_name": "kunalpanda/test_banking_app",
            "name": "test_banking_app",
            "owner": {"login": "kunalpanda"},
        },
        "head_commit": {
            "message": "[skip ci] Auto-generated tests",
            "committer": {"name": "Kunal"},
        },
    }


@pytest.fixture
def github_push_non_main_payload():
    """Push to a feature branch (should be ignored)."""
    return {
        "ref": "refs/heads/feature-xyz",
        "after": "999888777666",
        "repository": {
            "full_name": "kunalpanda/test_banking_app",
            "name": "test_banking_app",
            "owner": {"login": "kunalpanda"},
        },
        "head_commit": {
            "message": "WIP feature",
            "committer": {"name": "Kunal"},
        },
    }


# ---------------------------------------------------------------------------
# Sample Jenkins responses
# ---------------------------------------------------------------------------
@pytest.fixture
def jenkins_build_info_response():
    return {
        "result": {
            "job_name": "test_banking_app",
            "build_number": 42,
            "status": "SUCCESS",
            "duration": 120000,
            "url": "http://jenkins.test:8080/job/test_banking_app/42/",
        }
    }


@pytest.fixture
def jenkins_test_results_response():
    return {
        "result": {
            "job_name": "test_banking_app",
            "build_number": 42,
            "total_count": 25,
            "fail_count": 2,
            "skip_count": 1,
            "pass_count": 22,
            "duration": 8.5,
            "failed_tests": [
                {
                    "name": "testTransferNegativeAmount",
                    "class_name": "com.bank.TransferTest",
                    "status": "FAILED",
                    "duration": 0.02,
                    "error_message": "Expected exception not thrown",
                    "error_stacktrace": "at TransferTest.java:42",
                },
                {
                    "name": "testBalanceAfterWithdraw",
                    "class_name": "com.bank.AccountTest",
                    "status": "REGRESSION",
                    "duration": 0.01,
                    "error_message": "Expected 100 but was 50",
                    "error_stacktrace": "at AccountTest.java:88",
                },
            ],
        }
    }


@pytest.fixture
def jenkins_coverage_response():
    return {
        "result": {
            "job_name": "test_banking_app",
            "build_number": 42,
            "coverage_available": True,
            "coverage": {
                "line": 72.5,
                "branch": 65.0,
                "method": 80.0,
                "class": 90.0,
                "instruction": 70.0,
            },
            "summary": "Line: 72.5%, Branch: 65.0%, Method: 80.0%",
            "url": "http://jenkins.test:8080/job/test_banking_app/42/jacoco/",
        }
    }


# ---------------------------------------------------------------------------
# Claude / Anthropic mock response helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def claude_text_response():
    """Claude response with only text (end_turn)."""
    return {
        "content": [
            {"type": "text", "text": "Analysis complete. All tests passing."}
        ],
        "stop_reason": "end_turn",
    }


@pytest.fixture
def claude_tool_use_response():
    """Claude response that requests a tool call."""
    return {
        "content": [
            {"type": "text", "text": "Let me check the repo structure."},
            {
                "type": "tool_use",
                "id": "toolu_01abc",
                "name": "get_file_tree",
                "input": {
                    "owner": "kunalpanda",
                    "repo": "test_banking_app",
                    "ref": "main",
                },
            },
        ],
        "stop_reason": "tool_use",
    }
