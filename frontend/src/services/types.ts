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
  | 'productivity_analysis'
  | 'error'
  | 'log';

export interface BaseEvent {
  type: EventType;
  timestamp: string;
  data: any;
}

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

export interface CoverageMetrics {
  line?: number;
  branch?: number;
  method?: number;
}

export interface StateUpdateData {
  branch: string | null;
  commit_sha: string | null;
  iteration: number | null;
  phase: string | null;
  current_coverage?: CoverageMetrics;
  target_coverage?: CoverageMetrics;
}

export interface PRSummaryData {
  pr_number: number;
  pr_url: string;
  html_url?: string;
  title: string;
  body: string;
  branch: string;
  head_branch?: string;
  base_branch?: string;
  iteration: number;
  body_preview: string;
  created_at?: string;
}

export type PRSummary = PRSummaryData;

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

export interface ProductivityBreakdownItem {
  classification?: string;
  components?: Record<string, number>;
  count?: number;
  created?: boolean;
  files_verified?: number;
  minutes: number;
}

export interface ProductivityAnalysis {
  breakdown: Record<string, ProductivityBreakdownItem>;
  total_manual_minutes: number;
  total_manual_hours: number;
  ai_resolution_minutes: number;
  time_saved_minutes: number;
  hourly_rate: number;
  cost_saved: number;
  iteration_count: number;
  files_modified: number;
}

export interface OrchestratorState {
  status: 'idle' | 'running' | 'complete' | 'error';
  currentInteraction: number;  // renamed from currentIteration
  maxInteractions: number;     // renamed from maxIterations
  repo: string;
  branch: string;
  recentActions: string[];
  totalActions: number;
  prSummary: PRSummaryData | null;
  currentCoverage: CoverageMetrics | null;
  targetCoverage: CoverageMetrics | null;
  productivityAnalysis: ProductivityAnalysis | null;
}
