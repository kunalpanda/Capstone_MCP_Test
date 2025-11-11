import { useState, useEffect } from 'react';
import { BaseEvent, OrchestratorState } from '../services/types';

export const useOrchestratorState = (events: BaseEvent[]): OrchestratorState => {
  const [state, setState] = useState<OrchestratorState>({
    status: 'idle',
    currentIteration: 0,
    maxIterations: 50,
    repo: '',
    branch: '',
    recentActions: []
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
          newState.maxIterations = latestEvent.data.max_iterations;
          break;

        case 'iteration_start':
          newState.currentIteration = latestEvent.data.iteration;
          break;

        case 'state_update':
          if (latestEvent.data.branch) {
            newState.branch = latestEvent.data.branch;
          }
          break;

        case 'workflow_complete':
          newState.status = latestEvent.data.success ? 'complete' : 'error';
          break;

        case 'tool_call':
          newState.recentActions = [
            `Called ${latestEvent.data.tool_name}`,
            ...prev.recentActions.slice(0, 9)
          ];
          break;
      }

      return newState;
    });
  }, [events]);

  return state;
};
