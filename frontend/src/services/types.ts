// src/services/types.ts
// TypeScript type definitions for dashboard data structures

export interface OrchestratorEvent {
  timestamp: string;
  type: 'iteration_start' | 'claude_response' | 'tool_result' | 'state_update';
  data: any;
}

export interface WorkflowState {
  phase: string;
  commit: string | null;
  repo: string | null;
  branch: string;
  iteration: number;
  failed_tests: number;
  proposed_fixes: number;
  approved_fixes: number;
}

export interface Message {
  id: string;
  timestamp: string;
  iteration: number;
  content: string;
  toolCall?: ToolCall;
  stopReason?: string;
}

export interface ToolCall {
  name: string;
  input: any;
  result?: any;
  success?: boolean;
}

export interface TestMetrics {
  total: number;
  passing: number;
  failing: number;
  skipped: number;
}

export interface BuildInfo {
  buildNumber: number;
  status: 'SUCCESS' | 'FAILURE' | 'RUNNING' | 'PENDING';
  duration?: string;
  triggeredBy?: string;
}

export interface RepositoryInfo {
  name: string;
  owner: string;
  branch: string;
  commit: string;
}
