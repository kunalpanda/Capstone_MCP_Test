"""
Integration tests for orchestrator.config and orchestrator.gcp_config.

Tests verify environment variable loading, defaults, and Secret Manager
fallback behavior.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


# =========================================================================
# orchestrator.config.Settings
# =========================================================================
class TestConfigSettings:
    def test_defaults_from_env(self):
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "GITHUB_TOKEN": "ghp_test",
            "JENKINS_TOKEN": "jtok",
            "PROJECT_ID": "my-project",
            "GITHUB_MCP_URL": "http://g:8010",
            "JENKINS_MCP_URL": "http://j:8020",
            "TARGET_LINE_COVERAGE": "80",
            "TARGET_BRANCH_COVERAGE": "70",
            "TARGET_METHOD_COVERAGE": "85",
        }, clear=False):
            import importlib
            import orchestrator.config as cfg
            importlib.reload(cfg)

            assert cfg.settings.ANTHROPIC_API_KEY == "sk-ant-test"
            assert cfg.settings.GITHUB_TOKEN == "ghp_test"
            assert cfg.settings.TARGET_LINE_COVERAGE == 80
            assert cfg.settings.TARGET_BRANCH_COVERAGE == 70
            assert cfg.settings.TARGET_METHOD_COVERAGE == 85

    def test_default_coverage_targets(self):
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "GITHUB_TOKEN": "ghp_test",
            "JENKINS_TOKEN": "jtok",
        }, clear=False):
            # Remove coverage overrides to test defaults
            env = os.environ.copy()
            env.pop("TARGET_LINE_COVERAGE", None)
            env.pop("TARGET_BRANCH_COVERAGE", None)
            env.pop("TARGET_METHOD_COVERAGE", None)
            with patch.dict(os.environ, env, clear=True):
                import importlib
                import orchestrator.config as cfg
                importlib.reload(cfg)
                assert cfg.settings.TARGET_LINE_COVERAGE == 75
                assert cfg.settings.TARGET_BRANCH_COVERAGE == 70
                assert cfg.settings.TARGET_METHOD_COVERAGE == 75


# =========================================================================
# orchestrator.firestore_client.generate_workflow_id
# =========================================================================
class TestWorkflowIdGeneration:
    def test_collision_resistance(self):
        """Different commits to same repo/branch produce unique IDs."""
        from orchestrator.firestore_client import generate_workflow_id

        ids = set()
        for i in range(100):
            wid = generate_workflow_id("o/r", "main", f"sha-{i}")
            ids.add(wid)
        assert len(ids) == 100


# =========================================================================
# orchestrator.gcp_config.get_secret
# =========================================================================
class TestGetSecret:
    def test_env_var_takes_precedence(self):
        with patch.dict(os.environ, {"MY_SECRET": "from-env"}, clear=False):
            from orchestrator.gcp_config import get_secret
            result = get_secret("my-secret")
            assert result == "from-env"

    def test_falls_back_to_secret_manager(self):
        # Remove any env var so it falls through
        env = os.environ.copy()
        env.pop("CUSTOM_KEY", None)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data = b"secret-from-sm"
        mock_client.access_secret_version.return_value = mock_response

        with patch.dict(os.environ, {**env, "PROJECT_ID": "test-proj"}, clear=True):
            with patch(
                "orchestrator.gcp_config.secretmanager.SecretManagerServiceClient",
                return_value=mock_client,
            ):
                from orchestrator.gcp_config import get_secret
                result = get_secret("custom-key", "test-proj")
                assert result == "secret-from-sm"

    def test_raises_when_no_project_id(self):
        env = os.environ.copy()
        env.pop("MISSING_SECRET", None)
        env.pop("PROJECT_ID", None)
        env.pop("GCP_PROJECT", None)

        with patch.dict(os.environ, env, clear=True):
            from orchestrator.gcp_config import get_secret
            with pytest.raises(ValueError, match="PROJECT_ID"):
                get_secret("missing-secret")


# =========================================================================
# orchestrator.gcp_config.get_client_secrets
# =========================================================================
class TestGetClientSecrets:
    def test_fetches_four_secrets(self):
        secrets = {
            "CLIENT_DEFAULT_GITHUB_TOKEN": "ghp_x",
            "CLIENT_DEFAULT_JENKINS_TOKEN": "jt_x",
            "CLIENT_DEFAULT_JENKINS_URL": "http://j",
            "CLIENT_DEFAULT_JENKINS_USER": "admin",
        }
        with patch.dict(os.environ, secrets, clear=False):
            from orchestrator.gcp_config import get_client_secrets
            result = get_client_secrets("default")
            assert result["github_token"] == "ghp_x"
            assert result["jenkins_token"] == "jt_x"
            assert result["jenkins_url"] == "http://j"
            assert result["jenkins_user"] == "admin"
