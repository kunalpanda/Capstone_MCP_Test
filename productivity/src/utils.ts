import type { MatchedEvent, RepoAggregate, SourceData, WorkflowRecord } from './types';

function normalizeIso(input: string): string {
  let s = input.trim();

  // Trim microseconds to milliseconds because the JS Date parser can fail on 6-digit fractions.
  s = s.replace(/(\.\d{3})\d+/, '$1');

  // If there is no timezone suffix, assume UTC for consistency with workflow timestamps.
  if (/^\d{4}-\d{2}-\d{2}T/.test(s) && !(/[zZ]|[+-]\d{2}:\d{2}$/.test(s))) {
    s += 'Z';
  }

  return s;
}

function parseTimestamp(input?: string | null): number | null {
  if (!input) return null;
  const normalized = normalizeIso(input);
  const ms = Date.parse(normalized);
  return Number.isNaN(ms) ? null : ms;
}

const safeMinutesBetween = (a?: string | null, b?: string | null) => {
  const ta = parseTimestamp(a);
  const tb = parseTimestamp(b);
  if (ta === null || tb === null) return Number.POSITIVE_INFINITY;
  return Math.abs(ta - tb) / 60000;
};

function getWorkflowTimestamp(workflow: WorkflowRecord): string | null {
  return workflow.completedAt || workflow.updatedAt || workflow.createdAt || null;
}

export function matchProductivityEvents(data: SourceData): MatchedEvent[] {
  const workflowEntries = Object.entries(data.workflows || {});

  return (data.productivity_events || []).map((event) => {
    let best: { id: string; repo: string | undefined; delta: number } | null = null;

    for (const [id, workflow] of workflowEntries) {
      const workflowTs = getWorkflowTimestamp(workflow);
      const delta = safeMinutesBetween(event.timestamp, workflowTs);
      if (!Number.isFinite(delta)) continue;

      if (!best || delta < best.delta) {
        best = { id, repo: workflow.repo, delta };
      }
    }

    if (!best || !best.repo) {
      return { ...event, matchedRepo: null, workflowId: null, confidence: 'Unassigned', deltaMinutes: null };
    }

    if (best.delta <= 2) {
      return { ...event, matchedRepo: best.repo, workflowId: best.id, confidence: 'High', deltaMinutes: best.delta };
    }

    if (best.delta <= 10) {
      return { ...event, matchedRepo: best.repo, workflowId: best.id, confidence: 'Medium', deltaMinutes: best.delta };
    }

    return { ...event, matchedRepo: null, workflowId: null, confidence: 'Unassigned', deltaMinutes: best.delta };
  });
}

const safeDivide = (n: number, d: number) => (d === 0 ? 0 : n / d);

export function buildRepoAggregates(events: MatchedEvent[]): RepoAggregate[] {
  const matched = events.filter((e) => e.matchedRepo);
  const groups = new Map<string, MatchedEvent[]>();

  for (const event of matched) {
    const repo = event.matchedRepo!;
    const existing = groups.get(repo) || [];
    existing.push(event);
    groups.set(repo, existing);
  }

  const repos: RepoAggregate[] = Array.from(groups.entries()).map(([repo, repoEvents]) => {
    const runs = repoEvents.length;
    const sum = <T extends number>(selector: (item: MatchedEvent) => T) => repoEvents.reduce((acc, item) => acc + selector(item), 0);

    const avgBreakdown = {
      ciTriage: safeDivide(sum((e) => e.data.breakdown?.ci_triage?.minutes || 0), runs),
      buildVerify: safeDivide(sum((e) => e.data.breakdown?.build_verify_cycles?.minutes || 0), runs),
      changeVerification: safeDivide(sum((e) => e.data.breakdown?.change_verification?.minutes || 0), runs),
      fixImplementation: safeDivide(sum((e) => e.data.breakdown?.fix_implementation?.minutes || 0), runs),
      codebaseComprehension: safeDivide(sum((e) => e.data.breakdown?.codebase_comprehension?.minutes || 0), runs),
      rootCauseDiagnosis: safeDivide(sum((e) => e.data.breakdown?.root_cause_diagnosis?.minutes || 0), runs),
      prCreation: safeDivide(sum((e) => e.data.breakdown?.pr_creation?.minutes || 0), runs),
      diffInspections: safeDivide(sum((e) => e.data.breakdown?.diff_inspections?.minutes || 0), runs)
    };

    const avgManualMinutes = safeDivide(sum((e) => e.data.total_manual_minutes || 0), runs);
    const avgAiMinutes = safeDivide(sum((e) => e.data.ai_resolution_minutes || 0), runs);

    return {
      repo,
      runs,
      avgCostSaved: safeDivide(sum((e) => e.data.cost_saved || 0), runs),
      avgTimeSaved: safeDivide(sum((e) => e.data.time_saved_minutes || 0), runs),
      avgManualMinutes,
      avgAiMinutes,
      avgIterations: safeDivide(sum((e) => e.data.iteration_count || 0), runs),
      avgFilesModified: safeDivide(sum((e) => e.data.files_modified || 0), runs),
      efficiencyPercent: avgManualMinutes === 0 ? 0 : ((avgManualMinutes - avgAiMinutes) / avgManualMinutes) * 100,
      avgBreakdown
    };
  });

  return repos.sort((a, b) => b.avgCostSaved - a.avgCostSaved);
}

export function summarize(events: MatchedEvent[], source: SourceData) {
  const totalCostSaved = events.reduce((acc, e) => acc + (e.data.cost_saved || 0), 0);
  const totalTimeSaved = events.reduce((acc, e) => acc + (e.data.time_saved_minutes || 0), 0);
  const totalManualMinutes = events.reduce((acc, e) => acc + (e.data.total_manual_minutes || 0), 0);
  const totalAiMinutes = events.reduce((acc, e) => acc + (e.data.ai_resolution_minutes || 0), 0);
  const avgAiMinutes = safeDivide(totalAiMinutes, events.length);
  const avgManualMinutes = safeDivide(totalManualMinutes, events.length);
  const avgEfficiency = avgManualMinutes === 0 ? 0 : ((avgManualMinutes - avgAiMinutes) / avgManualMinutes) * 100;

  const confidenceCounts = events.reduce(
    (acc, event) => {
      acc[event.confidence] += 1;
      return acc;
    },
    { High: 0, Medium: 0, Unassigned: 0 }
  );

  return {
    totalCostSaved,
    totalTimeSaved,
    totalManualMinutes,
    totalAiMinutes,
    avgAiMinutes,
    avgManualMinutes,
    avgEfficiency,
    productivityEventCount: source.productivity_event_count || events.length,
    workflowCount: source.workflow_count || Object.keys(source.workflows || {}).length,
    matchedRepoCount: new Set(events.filter((e) => e.matchedRepo).map((e) => e.matchedRepo)).size,
    confidenceCounts
  };
}

export const currency = new Intl.NumberFormat('en-CA', {
  style: 'currency',
  currency: 'CAD',
  maximumFractionDigits: 0
});

export const numberFmt = new Intl.NumberFormat('en-CA', { maximumFractionDigits: 1 });

export function minutesToHoursText(value: number) {
  return `${numberFmt.format(value / 60)}h`;
}
