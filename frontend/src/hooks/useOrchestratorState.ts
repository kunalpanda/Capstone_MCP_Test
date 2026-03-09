import { useState, useEffect } from 'react';
import { BaseEvent, OrchestratorState } from '../services/types';

export const useOrchestratorState = (events: BaseEvent[]): OrchestratorState => {
  const [state, setState] = useState<OrchestratorState>({
    status: 'idle',
    currentInteraction: 0,
    maxInteractions: 50,
    repo: '',
    branch: '',
    recentActions: [],
    totalActions: 0,
    prSummary: null,
    currentCoverage: null,
    targetCoverage: null
  });

  useEffect(() => {
    if (events.length === 0) return;

    const latestEvent = events[events.length - 1];

    setState(prev => {
      const newState = { ...prev };

      switch (latestEvent.type) {
        case 'workflow_start':
          newState.status = 'running';
          newState.repo = `${latestEvent.data.repo_owner}/${latestEvent.data.repo_name}`;
          newState.branch = latestEvent.data.branch;
          newState.maxInteractions = latestEvent.data.max_iterations;
          newState.recentActions = [];
          newState.totalActions = 0;
          break;

        case 'iteration_start':
          newState.currentInteraction = latestEvent.data.iteration;
          break;

        case 'state_update':
          if (latestEvent.data.branch) {
            newState.branch = latestEvent.data.branch;
          }
          if (latestEvent.data.current_coverage) {
            newState.currentCoverage = latestEvent.data.current_coverage;
          }
          if (latestEvent.data.target_coverage) {
            newState.targetCoverage = latestEvent.data.target_coverage;
          }
          break;

        case 'workflow_complete':
          newState.status = latestEvent.data.success ? 'complete' : 'error';
          break;
        
        case 'pr_summary':
          newState.prSummary = {
            pr_number: latestEvent.data.pr_number,
            pr_url: latestEvent.data.pr_url,
            title: latestEvent.data.title,
            body: latestEvent.data.body,
            branch: latestEvent.data.branch,
            iteration: latestEvent.data.iteration,
            body_preview: latestEvent.data.body_preview
          };
          break;

        case 'tool_call':
          newState.recentActions = [
            `Called ${latestEvent.data.tool_name}`,
            ...prev.recentActions.slice(0, 9)
          ];
          newState.totalActions = prev.totalActions + 1;
          break;
      }

      return newState;
    });
  }, [events]);

  return state;
};
