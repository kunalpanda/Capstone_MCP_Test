export interface WorkflowRecord {
  prNumber?: number;
  completedAt?: string | null;
  branch?: string;
  updatedAt?: string;
  result?: string | null;
  commitSha?: string;
  phase?: string;
  createdAt?: string;
  iteration?: number;
  status?: string;
  triggeredBy?: string;
  repo?: string;
}

export interface ProductivityBreakdown {
  ci_triage?: { minutes?: number; components?: Record<string, number> };
  build_verify_cycles?: { minutes?: number; count?: number };
  change_verification?: { minutes?: number; files_verified?: number };
  fix_implementation?: { minutes?: number; classification?: string };
  pr_creation?: { minutes?: number; created?: boolean };
  codebase_comprehension?: { minutes?: number; classification?: string };
  diff_inspections?: { minutes?: number; count?: number };
  root_cause_diagnosis?: { minutes?: number; classification?: string };
}

export interface ProductivityData {
  cost_saved: number;
  time_saved_minutes: number;
  total_manual_hours: number;
  ai_resolution_minutes: number;
  hourly_rate: number;
  iteration_count: number;
  total_manual_minutes: number;
  files_modified: number;
  breakdown?: ProductivityBreakdown;
}

export interface ProductivityEvent {
  type: string;
  timestamp: string;
  _doc_id: string;
  data: ProductivityData;
}

export interface SourceData {
  exported_at: string;
  project_id: string;
  workflow_count: number;
  productivity_event_count: number;
  event_type_summary?: Record<string, number>;
  workflows: Record<string, WorkflowRecord>;
  productivity_events: ProductivityEvent[];
}

export interface MatchedEvent extends ProductivityEvent {
  matchedRepo: string | null;
  workflowId: string | null;
  confidence: 'High' | 'Medium' | 'Unassigned';
  deltaMinutes: number | null;
}

export interface RepoAggregate {
  repo: string;
  runs: number;
  avgCostSaved: number;
  avgTimeSaved: number;
  avgManualMinutes: number;
  avgAiMinutes: number;
  avgIterations: number;
  avgFilesModified: number;
  efficiencyPercent: number;
  avgBreakdown: {
    ciTriage: number;
    buildVerify: number;
    changeVerification: number;
    fixImplementation: number;
    codebaseComprehension: number;
    rootCauseDiagnosis: number;
    prCreation: number;
    diffInspections: number;
  };
}
