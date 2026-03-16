"""
Integration tests for orchestrator.state.WorkflowState.

Tests cover state transitions, branch tracking, coverage tracking,
phase advancement, and serialization to Firestore-ready dicts.
"""
import os
import pytest
from unittest.mock import AsyncMock, patch


class TestWorkflowStateInit:
    """Verify the initial defaults of a fresh WorkflowState."""

    def test_default_branch_is_main(self, fresh_state):
        assert fresh_state.branch == "main"

    def test_active_branch_initially_none(self, fresh_state):
        assert fresh_state.active_branch is None

    def test_get_branch_fallback_to_main(self, fresh_state):
        assert fresh_state.get_branch() == "main"

    def test_phase_starts_at_init(self, fresh_state):
        assert fresh_state.phase == "init"

    def test_iteration_starts_at_zero(self, fresh_state):
        assert fresh_state.iteration == 0

    def test_pr_number_is_none(self, fresh_state):
        assert fresh_state.pr_number is None

    def test_empty_coverage(self, fresh_state):
        assert fresh_state.current_coverage == {}
        assert fresh_state.target_coverage == {}


class TestBranchTracking:
    """Branch set / get helpers and env-var side-effect."""

    def test_set_branch_updates_both_fields(self, fresh_state):
        fresh_state.set_branch("fix-tests-123")
        assert fresh_state.branch == "fix-tests-123"
        assert fresh_state.active_branch == "fix-tests-123"

    def test_set_branch_updates_env_var(self, fresh_state):
        fresh_state.set_branch("ci/new-tests")
        assert os.environ.get("ACTIVE_BRANCH") == "ci/new-tests"

    def test_get_branch_returns_active_when_set(self, fresh_state):
        fresh_state.set_branch("feature-x")
        assert fresh_state.get_branch() == "feature-x"

    def test_get_branch_falls_back_to_branch_field(self, fresh_state):
        fresh_state.branch = "dev"
        fresh_state.active_branch = None
        assert fresh_state.get_branch() == "dev"

    def test_get_branch_ultimate_fallback_main(self, fresh_state):
        fresh_state.branch = None
        fresh_state.active_branch = None
        assert fresh_state.get_branch() == "main"


class TestPhaseAdvancement:
    """Phase transitions via advance_phase."""

    def test_advance_phase_sets_phase(self, fresh_state):
        fresh_state.advance_phase("analyzing")
        assert fresh_state.phase == "analyzing"

    def test_advance_phase_can_go_back(self, fresh_state):
        fresh_state.advance_phase("fixing")
        fresh_state.advance_phase("init")
        assert fresh_state.phase == "init"


class TestCoverageTracking:
    """update_coverage and get_coverage_summary."""

    def test_update_coverage_stores_metrics(self, fresh_state):
        data = {"line": 75.0, "branch": 60.0, "method": 80.0}
        fresh_state.update_coverage(data)
        assert fresh_state.current_coverage == data

    def test_update_coverage_ignores_none(self, fresh_state):
        fresh_state.update_coverage(None)
        assert fresh_state.current_coverage == {}

    def test_update_coverage_ignores_non_dict(self, fresh_state):
        fresh_state.update_coverage("bad data")
        assert fresh_state.current_coverage == {}

    def test_coverage_summary_no_data(self, fresh_state):
        assert "Not yet measured" in fresh_state.get_coverage_summary()

    def test_coverage_summary_with_target(self, fresh_state):
        fresh_state.target_coverage = {"line": 75, "branch": 70, "method": 75}
        fresh_state.update_coverage({"line": 80.0, "branch": 65.0, "method": 78.0})
        summary = fresh_state.get_coverage_summary()
        assert "✅" in summary  # line and method meet target
        assert "⚠️" in summary  # branch does not

    def test_coverage_summary_all_passing(self, fresh_state):
        fresh_state.target_coverage = {"line": 50, "branch": 50, "method": 50}
        fresh_state.update_coverage({"line": 90.0, "branch": 90.0, "method": 90.0})
        summary = fresh_state.get_coverage_summary()
        assert "⚠️" not in summary


class TestStateSummary:
    """summary() produces a Firestore-friendly dict."""

    def test_summary_keys(self, fresh_state):
        s = fresh_state.summary()
        expected = {
            "phase", "commit", "repo", "branch",
            "active_branch", "iteration", "failed_tests",
            "proposed_fixes", "approved_fixes",
            "current_coverage", "target_coverage",
        }
        assert expected == set(s.keys())

    def test_summary_reflects_mutations(self, fresh_state):
        fresh_state.set_branch("feature-y")
        fresh_state.pr_number = 7
        fresh_state.iteration = 3
        s = fresh_state.summary()
        assert s["branch"] == "feature-y"
        assert s["active_branch"] == "feature-y"
        assert s["iteration"] == 3


class TestSaveToFirestore:
    """save_to_firestore delegates to FirestoreClient."""

    @pytest.mark.asyncio
    async def test_save_calls_firestore(self, fresh_state, mock_firestore_client):
        with patch(
            "orchestrator.state.get_firestore_client",
            return_value=mock_firestore_client,
        ):
            await fresh_state.save_to_firestore("wf-abc")
            mock_firestore_client.update_workflow.assert_awaited_once()
            args = mock_firestore_client.update_workflow.call_args
            assert args[0][0] == "wf-abc"
