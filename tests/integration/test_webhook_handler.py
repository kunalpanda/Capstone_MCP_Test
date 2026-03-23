"""
Integration tests for webhook_handler.app.

Uses FastAPI TestClient to exercise the /webhook/github,
/emergency-stop, /health, and / endpoints with mocked Pub/Sub and Firestore.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# We need to mock GCP clients BEFORE the app module is imported.
# ---------------------------------------------------------------------------
_mock_publisher = MagicMock()
_mock_publisher.topic_path.return_value = "projects/test-project/topics/workflow-commands"
_future = MagicMock()
_future.result.return_value = "msg-id-123"
_mock_publisher.publish.return_value = _future


@pytest.fixture(autouse=True)
def _patch_pubsub():
    with patch("google.cloud.pubsub_v1.PublisherClient", return_value=_mock_publisher):
        # Force re-import to pick up mock
        import importlib
        import webhook_handler.app as mod
        importlib.reload(mod)
        mod.publisher = _mock_publisher
        mod.topic_path = "projects/test-project/topics/workflow-commands"
        yield mod


@pytest.fixture
def client(_patch_pubsub):
    return TestClient(_patch_pubsub.app)


# =========================================================================
# Health / root
# =========================================================================
class TestHealthAndRoot:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webhook-handler"

    def test_root_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Webhook Handler"
        assert "/webhook/github" in str(data)


# =========================================================================
# /webhook/github
# =========================================================================
class TestGitHubWebhook:
    def test_valid_push_queues_workflow(self, client, github_push_payload):
        resp = client.post("/webhook/github", json=github_push_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert "workflowId" in data
        assert len(data["workflowId"]) == 16  # SHA-256 hex prefix

    def test_skip_ci_is_ignored(self, client, github_push_skip_ci_payload):
        resp = client.post("/webhook/github", json=github_push_skip_ci_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert "skip ci" in data["reason"].lower()

    def test_non_main_branch_is_ignored(self, client, github_push_non_main_payload):
        resp = client.post("/webhook/github", json=github_push_non_main_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert "main" in data["reason"]

    def test_missing_repository_returns_400(self, client):
        resp = client.post("/webhook/github", json={"ref": "refs/heads/main"})
        assert resp.status_code == 400

    def test_automated_pr_merge_is_ignored(self, client):
        payload = {
            "ref": "refs/heads/main",
            "after": "aaa111bbb222",
            "repository": {
                "full_name": "kunalpanda/test_banking_app",
                "name": "test_banking_app",
                "owner": {"login": "kunalpanda"},
            },
            "head_commit": {
                "message": "[Automated] fix-tests-branch merge",
                "committer": {"name": "GitHub Web-Flow"},
            },
        }
        resp = client.post("/webhook/github", json=payload)
        data = resp.json()
        assert data["status"] == "ignored"
        assert "automated" in data["reason"].lower() or "merge" in data["reason"].lower()

    def test_deterministic_workflow_id(self, client, github_push_payload):
        """Two identical pushes produce the same workflow ID."""
        r1 = client.post("/webhook/github", json=github_push_payload)
        r2 = client.post("/webhook/github", json=github_push_payload)
        assert r1.json()["workflowId"] == r2.json()["workflowId"]

    def test_different_commits_produce_different_ids(self, client):
        p1 = {
            "ref": "refs/heads/main",
            "after": "aaa",
            "repository": {"full_name": "o/r", "name": "r", "owner": {"login": "o"}},
            "head_commit": {"message": "a", "committer": {"name": "x"}},
        }
        p2 = {**p1, "after": "bbb"}
        r1 = client.post("/webhook/github", json=p1).json()["workflowId"]
        r2 = client.post("/webhook/github", json=p2).json()["workflowId"]
        assert r1 != r2


# =========================================================================
# /emergency-stop
# =========================================================================
class TestEmergencyStop:
    def test_stop_with_no_running_workflows(self, client):
        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.return_value = iter([])

        with patch("google.cloud.firestore.Client", return_value=mock_db):
            resp = client.post("/emergency-stop", json={"reason": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stopped_count"] == 0

    def test_stop_with_running_workflows(self, client):
        mock_doc = MagicMock()
        mock_doc.id = "wf-running-1"

        mock_db = MagicMock()
        mock_db.collection.return_value.where.return_value.stream.return_value = iter(
            [mock_doc]
        )

        with patch("google.cloud.firestore.Client", return_value=mock_db):
            resp = client.post("/emergency-stop", json={"reason": "test halt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stopped_count"] == 1
        assert "wf-running-1" in data["workflow_ids"]
