// Event types from backend
export type EventType = 
  | 'workflow_start'
  | 'iteration_start'
  | 'iteration_end'
  | 'claude_response'
  | 'tool_call'
  | 'tool_result'
  | 'state_update'
  | 'workflow_complete'
  | 'pr_summary'
  | 'error'
  | 'log';

// Base event structure
export interface BaseEvent {
  type: EventType;
  timestamp: string;
  data: any;
}

// Specific event data types
export interface WorkflowStartData {
  repo_owner: string;
  repo_name: string;
  branch: string;
  max_iterations: number;
  workflow_type: string;
}

export interface IterationStartData {
  iteration: number;
  max_iterations: number;
  progress_percent: number;
}

export interface ClaudeResponseData {
  iteration: number;
  stop_reason: string;
  text_content: string | null;
  has_tool_use: boolean;
  tool_count: number;
  message_preview: string | null;
}

export interface ToolCallData {
  iteration: number;
  tool_name: string;
  tool_input: Record<string, any>;
  tool_use_id: string;
  input_preview: string;
}

export interface ToolResultData {
  iteration: number;
  tool_name: string;
  tool_use_id: string;
  success: boolean;
  result_summary: string | null;
  error_message: string | null;
  execution_time_ms: number | null;
}

export interface StateUpdateData {
  branch: string | null;
  commit_sha: string | null;
  iteration: number | null;
  phase: string | null;
}

export interface PRSummaryData {
  pr_number: number;
  pr_url: string;
  title: string;
  body: string;
  branch: string;
  iteration: number;
  body_preview: string;
}

export interface WorkflowCompleteData {
  total_iterations: number;
  success: boolean;
  reason: string | null;
  summary: {
    tests_fixed: number | null;
    tests_generated: number | null;
    files_modified: number | null;
  };
  duration_seconds: number | null;
}

// Orchestrator state
export interface OrchestratorState {
  status: 'idle' | 'running' | 'complete' | 'error';
  currentIteration: number;
  maxIterations: number;
  repo: string;
  branch: string;
  recentActions: string[];
  prSummary: PRSummaryData | null;
}
