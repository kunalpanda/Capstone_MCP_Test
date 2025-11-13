# orchestrator/state.py
import json
from datetime import datetime

class WorkflowState:
    """
    Tracks all persistent information about the current workflow session.
    This extended version keeps an active_branch value and provides helpers
    for enforcing branch consistency across GitHub and Jenkins operations.
    """

    def __init__(self):
        self.start_time = datetime.utcnow().isoformat()
        self.commit_sha = None
        self.repo = None
        self.branch = "main"
        self.active_branch = None        # <-- NEW
        self.phase = "init"
        self.failed_tests = []
        self.proposed_fixes = []
        self.approved_fixes = []
        self.iteration = 0
        self.pr_number = None
        self.pr_summary = None

    # ========== NEW UTILS ==========

    def set_branch(self, branch_name: str):
        """Safely set and log the current working branch."""
        import os
        self.active_branch = branch_name
        self.branch = branch_name
        os.environ["ACTIVE_BRANCH"] = branch_name
        print(f"🌿 Active branch set to: {branch_name}")


    def get_branch(self) -> str:
        """Return active branch or fallback to main."""
        return self.active_branch or self.branch or "main"

    def advance_phase(self, new_phase: str):
        self.phase = new_phase
        print(f"🔄 Workflow phase -> {new_phase}")

    def summary(self):
        return {
            "phase": self.phase,
            "commit": self.commit_sha,
            "repo": self.repo,
            "branch": self.branch,
            "active_branch": self.active_branch,
            "iteration": self.iteration,
            "failed_tests": len(self.failed_tests),
            "proposed_fixes": len(self.proposed_fixes),
            "approved_fixes": len(self.approved_fixes),
        }

    def save(self, path="workflow_state.json"):
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)
