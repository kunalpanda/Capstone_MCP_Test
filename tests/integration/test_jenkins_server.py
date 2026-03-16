"""
Integration tests for mcp_servers.jenkins_server (server.py + tools.py).

Uses FastAPI TestClient against the JSON-RPC endpoint with mocked httpx
calls to Jenkins API.
"""
import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

JENKINS_SERVER_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "mcp_servers", "jenkins_server"
)
if JENKINS_SERVER_DIR not in sys.path:
    sys.path.insert(0, JENKINS_SERVER_DIR)


@pytest.fixture(autouse=True)
def _set_jenkins_env(monkeypatch):
    monkeypatch.setenv("JENKINS_TOKEN", "fake-token")
    monkeypatch.setenv("JENKINS_URL", "http://jenkins.test:8080")
    monkeypatch.setenv("JENKINS_USER", "admin")


@pytest.fixture
def jenkins_client():
    from fastapi.testclient import TestClient
    import importlib
    import config as cfg_mod
    importlib.reload(cfg_mod)
    import server as srv_mod
    importlib.reload(srv_mod)
    return TestClient(srv_mod.app)


def jsonrpc(method, params=None):
    return {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": "1"}


# =========================================================================
# Root / health
# =========================================================================
class TestJenkinsServerRoot:
    def test_root(self, jenkins_client):
        resp = jenkins_client.get("/")
        assert resp.status_code == 200
        assert "Jenkins MCP" in resp.json()["message"]


# =========================================================================
# tools/list
# =========================================================================
class TestJenkinsToolsList:
    def test_lists_all_jenkins_tools(self, jenkins_client):
        resp = jenkins_client.post("/", json=jsonrpc("tools/list"))
        assert resp.status_code == 200
        tool_names = [t["name"] for t in resp.json()["result"]["tools"]]
        expected = [
            "trigger_build", "get_queue_info", "get_build_info",
            "get_console_output", "wait_for_build_completion",
            "get_test_results", "get_coverage_report",
        ]
        for name in expected:
            assert name in tool_names


# =========================================================================
# tools/call – trigger_build
# =========================================================================
class TestTriggerBuild:
    def test_trigger_build_success(self, jenkins_client):
        post_resp = MagicMock()
        post_resp.status_code = 201
        post_resp.headers = {"Location": "http://jenkins.test:8080/queue/item/99/"}

        queue_resp = MagicMock()
        queue_resp.status_code = 200
        queue_resp.json.return_value = {"executable": {"number": 42}}

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=post_resp)
            instance.get = AsyncMock(return_value=queue_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "trigger_build",
                "params": {"job_name": "test_banking_app"},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["status"] == "triggered"
        assert result["build_number"] == 42

    def test_trigger_build_injects_branch(self, jenkins_client):
        """Even without explicit BRANCH param, enforce_branch_param adds it."""
        captured = {}

        async def capture_post(url, params=None, **kwargs):
            captured.update(params or {})
            resp = MagicMock()
            resp.status_code = 201
            resp.headers = {}
            return resp

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = capture_post
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "trigger_build",
                "params": {"job_name": "test_banking_app"},
            })
            jenkins_client.post("/", json=payload)

        assert "BRANCH_NAME" in captured


# =========================================================================
# tools/call – get_build_info
# =========================================================================
class TestGetBuildInfo:
    def test_returns_build_details(self, jenkins_client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "number": 42,
            "result": "SUCCESS",
            "duration": 120000,
            "url": "http://jenkins.test:8080/job/test_banking_app/42/",
        }

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_build_info",
                "params": {"job_name": "test_banking_app"},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["build_number"] == 42
        assert result["status"] == "SUCCESS"


# =========================================================================
# tools/call – get_test_results
# =========================================================================
class TestGetTestResults:
    def test_returns_passed_and_failed(self, jenkins_client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalCount": 10,
            "failCount": 2,
            "skipCount": 1,
            "passCount": 7,
            "duration": 5.0,
            "suites": [
                {
                    "cases": [
                        {"name": "testA", "className": "C", "status": "PASSED", "duration": 0.1},
                        {
                            "name": "testB", "className": "C", "status": "FAILED",
                            "duration": 0.2,
                            "errorDetails": "assertion fail",
                            "errorStackTrace": "at C:10",
                        },
                    ]
                }
            ],
        }

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_test_results",
                "params": {"job_name": "test_banking_app", "build_number": 42},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["fail_count"] == 2
        assert result["pass_count"] == 7
        assert len(result["failed_tests"]) == 1
        assert result["failed_tests"][0]["name"] == "testB"

    def test_no_test_results_404(self, jenkins_client):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_test_results",
                "params": {"job_name": "test_banking_app", "build_number": 99},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["status"] == "no_tests"


# =========================================================================
# tools/call – get_console_output + smart_truncate_log
# =========================================================================
class TestConsoleOutput:
    def test_short_log_not_truncated(self, jenkins_client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "BUILD SUCCESS\nAll tests passed."

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_console_output",
                "params": {"job_name": "test_banking_app", "build_number": 42},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["truncated"] is False
        assert "BUILD SUCCESS" in result["log"]

    def test_long_log_is_truncated(self, jenkins_client):
        long_log = "x" * 100_000

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = long_log

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_console_output",
                "params": {"job_name": "test_banking_app", "build_number": 42},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["truncated"] is True
        assert result["total_length"] == 100_000
        assert "omitted" in result["log"]


# =========================================================================
# smart_truncate_log unit-level checks
# =========================================================================
class TestSmartTruncateLog:
    def test_below_threshold_not_truncated(self):
        from tools import smart_truncate_log
        result = smart_truncate_log("short", max_chars=50000)
        assert result["truncated"] is False

    def test_above_threshold_preserves_head_and_tail(self):
        from tools import smart_truncate_log
        log = "H" * 20_000 + "M" * 60_000 + "T" * 20_000
        result = smart_truncate_log(log, max_chars=50000)
        assert result["truncated"] is True
        assert result["log"].startswith("H")
        assert result["log"].endswith("T" * 100)  # tail preserved


# =========================================================================
# tools/call – get_coverage_report
# =========================================================================
class TestGetCoverageReport:
    def test_returns_coverage_metrics(self, jenkins_client):
        build_resp = MagicMock()
        build_resp.status_code = 200
        build_resp.json.return_value = {"number": 42}

        coverage_resp = MagicMock()
        coverage_resp.status_code = 200
        coverage_resp.json.return_value = {
            "lineCoverage": {"total": 100, "covered": 75},
            "branchCoverage": {"total": 100, "covered": 65},
            "methodCoverage": {"total": 100, "covered": 80},
            "classCoverage": {"total": 100, "covered": 90},
            "instructionCoverage": {"total": 100, "covered": 70},
        }

        call_count = 0
        async def route_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return build_resp if call_count == 1 else coverage_resp

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = route_get
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_coverage_report",
                "params": {"job_name": "test_banking_app"},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["coverage_available"] is True
        assert result["coverage"]["line"] == 75.0
        assert result["coverage"]["branch"] == 65.0

    def test_coverage_not_available_404(self, jenkins_client):
        build_resp = MagicMock()
        build_resp.status_code = 200
        build_resp.json.return_value = {"number": 42}

        cov_resp = MagicMock()
        cov_resp.status_code = 404

        call_count = 0
        async def route_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return build_resp if call_count == 1 else cov_resp

        with patch("tools.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = route_get
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            payload = jsonrpc("tools/call", {
                "name": "get_coverage_report",
                "params": {"job_name": "test_banking_app"},
            })
            resp = jenkins_client.post("/", json=payload)

        result = resp.json()["result"]
        assert result["coverage_available"] is False


# =========================================================================
# Unknown method
# =========================================================================
class TestJenkinsUnknownMethod:
    def test_unknown_method(self, jenkins_client):
        resp = jenkins_client.post("/", json=jsonrpc("tools/nonexistent"))
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == -32601
