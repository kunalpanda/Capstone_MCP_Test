# orchestrator/state.py
import json
from datetime import datetime

class WorkflowState:
    def __init__(self):
        self.start_time = datetime.utcnow().isoformat()
        self.commit_sha = None
        self.repo = None
        self.branch = None
        self.phase = "init"
        self.failed_tests = []
        self.proposed_fixes = []
        self.approved_fixes = []
        self.iteration = 0

    def summary(self):
        return {
            "phase": self.phase,
            "commit": self.commit_sha,
            "repo": self.repo,
            "branch": self.branch,
            "iteration": self.iteration,
            "failed_tests": len(self.failed_tests),
            "proposed_fixes": len(self.proposed_fixes),
            "approved_fixes": len(self.approved_fixes),
        }

    def save(self, path="workflow_state.json"):
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)
