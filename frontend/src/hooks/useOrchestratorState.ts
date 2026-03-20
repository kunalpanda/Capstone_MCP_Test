import { useState, useEffect, useRef } from 'react';
import { BaseEvent, OrchestratorState } from '../services/types';

/**
 * Reduces a single event into the current state.
 *
 * Extracted as a pure function so the same logic can be used both for
 * real-time events and for replaying history on reconnect.
 */
function applyEvent(prev: OrchestratorState, event: BaseEvent): OrchestratorState {
  const newState = { ...prev };

  switch (event.type) {
    case 'workflow_start':
      newState.status = 'running';
      newState.repo = `${event.data.repo_owner}/${event.data.repo_name}`;
      newState.branch = event.data.branch;
      newState.maxInteractions = event.data.max_iterations;
      newState.currentInteraction = 0;
      newState.recentActions = [];
      newState.totalActions = 0;
      newState.prSummary = null;
      newState.currentCoverage = null;
      newState.targetCoverage = null;
      newState.productivityAnalysis = null;
      break;

    case 'iteration_start':
      newState.currentInteraction = event.data.iteration;
      break;

    case 'state_update':
      if (event.data.branch) {
        newState.branch = event.data.branch;
      }
      if (event.data.current_coverage) {
        newState.currentCoverage = event.data.current_coverage;
      }
      if (event.data.target_coverage) {
        newState.targetCoverage = event.data.target_coverage;
      }
      break;

    case 'workflow_complete':
      newState.status = event.data.success ? 'complete' : 'error';
      break;

    case 'pr_summary':
      newState.prSummary = {
        pr_number: event.data.pr_number,
        pr_url: event.data.pr_url,
        title: event.data.title,
        body: event.data.body,
        branch: event.data.branch,
        iteration: event.data.iteration,
        body_preview: event.data.body_preview
      };
      break;

    case 'productivity_analysis':
      newState.productivityAnalysis = {
        breakdown: event.data.breakdown,
        total_manual_minutes: event.data.total_manual_minutes,
        total_manual_hours: event.data.total_manual_hours,
        ai_resolution_minutes: event.data.ai_resolution_minutes,
        time_saved_minutes: event.data.time_saved_minutes,
        hourly_rate: event.data.hourly_rate,
        cost_saved: event.data.cost_saved,
        iteration_count: event.data.iteration_count,
        files_modified: event.data.files_modified
      };
      break;

    case 'tool_call':
      newState.recentActions = [
        `Called ${event.data.tool_name}`,
        ...prev.recentActions.slice(0, 9)
      ];
      newState.totalActions = prev.totalActions + 1;
      break;
  }

  return newState;
}

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
    targetCoverage: null,
    productivityAnalysis: null
  });

  // Track how many events we've already processed so we never skip
  // events that arrive in the same React batch.
  const processedCountRef = useRef(0);

  useEffect(() => {
    if (events.length === 0) return;

    // If the events array shrank (cleared on workflow_start),
    // reset the counter so we reprocess from the beginning.
    if (events.length < processedCountRef.current) {
      processedCountRef.current = 0;
    }

    // Only process events we haven't seen yet
    const newStart = processedCountRef.current;
    if (newStart >= events.length) return;

    const newEvents = events.slice(newStart);
    processedCountRef.current = events.length;

    setState(prev => {
      let current = prev;
      for (const event of newEvents) {
        current = applyEvent(current, event);
      }
      return current;
    });
  }, [events]);

  return state;
};
