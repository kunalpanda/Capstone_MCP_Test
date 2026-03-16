"""
Integration tests for orchestrator_worker.app.

Tests the Pub/Sub push handler, health endpoint, and error handling
with mocked Firestore and orchestrator execution.
"""
import base64
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_firestore_db():
    db = MagicMock()
    db.collection.return_value.document.return_value.set = MagicMock()
    db.collection.return_value.document.return_value.get.return_value = MagicMock(
        exists=False
    )
    return db


@pytest.fixture
def worker_client(mock_firestore_db):
    with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
        import importlib
        import orchestrator_worker.app as mod
        importlib.reload(mod)
        return TestClient(mod.app)


# =========================================================================
# Health / root
# =========================================================================
class TestWorkerHealth:
    def test_health(self, worker_client):
        resp = worker_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root(self, worker_client):
        resp = worker_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Orchestrator Worker"
        assert "/pubsub/push" in str(data["endpoints"])


# =========================================================================
# /pubsub/push
# =========================================================================
class TestPubSubPush:
    def _make_envelope(self, payload: dict) -> dict:
        data = base64.b64encode(json.dumps(payload).encode()).decode()
        return {
            "message": {
                "data": data,
                "messageId": "msg-001",
                "publishTime": "2025-01-01T00:00:00Z",
            },
            "subscription": "projects/test/subscriptions/test-sub",
        }

    def test_missing_message_returns_400(self, worker_client):
        resp = worker_client.post("/pubsub/push", json={})
        assert resp.status_code == 400

    def test_missing_data_returns_400(self, worker_client):
        resp = worker_client.post("/pubsub/push", json={"message": {}})
        assert resp.status_code == 400

    def test_missing_workflow_params_returns_400(self, worker_client):
        envelope = self._make_envelope({"workflowId": "wf-1"})  # Missing repo, branch, commitSha
        resp = worker_client.post("/pubsub/push", json=envelope)
        assert resp.status_code == 400

    def test_invalid_json_returns_400(self, worker_client):
        bad_data = base64.b64encode(b"not json").decode()
        envelope = {"message": {"data": bad_data, "messageId": "m1"}}
        resp = worker_client.post("/pubsub/push", json=envelope)
        assert resp.status_code == 400

    def test_valid_payload_runs_workflow(self, worker_client, mock_firestore_db):
        payload = {
            "workflowId": "wf-test-123",
            "repo": "kunalpanda/test_banking_app",
            "branch": "main",
            "commitSha": "abc123",
            "clientId": "default",
        }
        envelope = self._make_envelope(payload)

        mock_secrets = {
            "github_token": "ghp_fake",
            "jenkins_token": "jtok",
            "jenkins_url": "http://j:8080",
            "jenkins_user": "admin",
        }

        with patch(
            "orchestrator_worker.app.run_orchestrator_workflow",
            new_callable=AsyncMock,
            return_value={"status": "completed"},
        ) as mock_run:
            with patch(
                "orchestrator.gcp_config.get_client_secrets",
                return_value=mock_secrets,
            ):
                resp = worker_client.post("/pubsub/push", json=envelope)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        mock_run.assert_awaited_once()

    def test_workflow_failure_returns_500(self, worker_client):
        payload = {
            "workflowId": "wf-fail",
            "repo": "o/r",
            "branch": "main",
            "commitSha": "sha",
            "clientId": "default",
        }
        envelope = self._make_envelope(payload)

        with patch(
            "orchestrator_worker.app.run_orchestrator_workflow",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Orchestrator exploded"),
        ):
            with patch(
                "orchestrator.gcp_config.get_client_secrets",
                return_value={"github_token": "g", "jenkins_token": "j", "jenkins_url": "u", "jenkins_user": "a"},
            ):
                resp = worker_client.post("/pubsub/push", json=envelope)

        assert resp.status_code == 500


# =========================================================================
# /test/firestore
# =========================================================================
class TestFirestoreConnectivity:
    def test_firestore_test_endpoint(self, worker_client, mock_firestore_db):
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"message": "Connection successful"}
        mock_firestore_db.collection.return_value.document.return_value.get.return_value = mock_doc

        resp = worker_client.get("/test/firestore")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["firestore_working"] is True


# =========================================================================
# /test/mcp
# =========================================================================
class TestMCPConnectivity:
    def test_mcp_test_when_urls_not_set(self, worker_client):
        with patch.dict("os.environ", {"GITHUB_MCP_URL": "", "JENKINS_MCP_URL": ""}, clear=False):
            import importlib
            import orchestrator_worker.app as mod
            # The URLs were captured at import time; check what the endpoint returns
            resp = worker_client.get("/test/mcp")
            assert resp.status_code == 200
