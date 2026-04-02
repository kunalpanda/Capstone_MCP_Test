import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
  Legend,
  AreaChart,
  Area
} from 'recharts';

import sampleData from './data/productivity_data.json';
import type { RepoAggregate, SourceData } from './types';
import { buildRepoAggregates, currency, matchProductivityEvents, minutesToHoursText, numberFmt, summarize } from './utils';
import KpiCard from './components/KpiCard';
import ChartCard from './components/ChartCard';
import RepoTable from './components/RepoTable';

const COLORS = {
  cyan: '#39d0ff',
  violet: '#8b7cff',
  emerald: '#3ee089',
  amber: '#ffbf5f',
  grid: 'rgba(106, 133, 182, 0.18)',
  text: '#37506c'
};

function App() {
  const [data, setData] = useState<SourceData>(sampleData as SourceData);
  const [uploadName, setUploadName] = useState<string>('Bundled sample data');
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);

  const matchedEvents = useMemo(() => matchProductivityEvents(data), [data]);
  const repoAggregates = useMemo(() => buildRepoAggregates(matchedEvents), [matchedEvents]);
  const summary = useMemo(() => summarize(matchedEvents, data), [matchedEvents, data]);

  const selectedRepoData: RepoAggregate | null = useMemo(() => {
    if (!repoAggregates.length) return null;
    if (selectedRepo) return repoAggregates.find((repo) => repo.repo === selectedRepo) || repoAggregates[0];
    return repoAggregates[0];
  }, [repoAggregates, selectedRepo]);

  const repoBarData = repoAggregates.map((repo) => ({
    repo: shortRepo(repo.repo),
    fullRepo: repo.repo,
    avgCostSaved: round(repo.avgCostSaved),
    avgTimeSaved: round(repo.avgTimeSaved),
    efficiencyPercent: round(repo.efficiencyPercent)
  }));

  const scatterData = matchedEvents
    .filter((e) => e.matchedRepo)
    .map((e) => ({
      repo: shortRepo(e.matchedRepo!),
      fullRepo: e.matchedRepo!,
      manual: round(e.data.total_manual_minutes || 0),
      ai: round(e.data.ai_resolution_minutes || 0),
      cost: round(e.data.cost_saved || 0)
    }));

  const confidenceData = [
    { name: 'High confidence', value: summary.confidenceCounts.High, color: COLORS.emerald },
    { name: 'Medium confidence', value: summary.confidenceCounts.Medium, color: COLORS.cyan },
    { name: 'Unassigned', value: summary.confidenceCounts.Unassigned, color: COLORS.amber }
  ];

  const breakdownData = repoAggregates.map((repo) => ({
    repo: shortRepo(repo.repo),
    ciTriage: round(repo.avgBreakdown.ciTriage),
    buildVerify: round(repo.avgBreakdown.buildVerify),
    fixImplementation: round(repo.avgBreakdown.fixImplementation),
    comprehension: round(repo.avgBreakdown.codebaseComprehension),
    rootCause: round(repo.avgBreakdown.rootCauseDiagnosis)
  }));

  const areaData = repoAggregates.map((repo) => ({
    repo: shortRepo(repo.repo),
    avgIterations: round(repo.avgIterations),
    avgFilesModified: round(repo.avgFilesModified)
  }));

  const hasRepoData = repoAggregates.length > 0;
  const hasScatterData = scatterData.length > 0;

  function handleFileUpload(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result)) as SourceData;
        setData(parsed);
        setUploadName(file.name);
        setSelectedRepo(null);
      } catch {
        alert('Could not parse the uploaded JSON file.');
      }
    };
    reader.readAsText(file);
  }

  return (
    <div className="app-shell">
      <div className="bg-orb orb-a" />
      <div className="bg-orb orb-b" />
      <div className="bg-grid" />

      <header className="hero">
        <motion.div
          className="hero-copy"
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
        >
          <span className="eyebrow">Executive productivity intelligence</span>
          <h1>Agentic AI Integration Testing Dashboard</h1>
          <p>
            A local, pitch-ready analytics experience for showing how your agentic workflow reduces manual effort,
            compresses resolution time, and scales productivity across multiple repositories.
          </p>

          <div className="hero-actions">
            <label className="upload-button">
              Upload JSON
              <input
                type="file"
                accept=".json,application/json"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                }}
              />
            </label>

            <button
              className="ghost-button"
              onClick={() => {
                setData(sampleData as SourceData);
                setUploadName('Bundled sample data');
                setSelectedRepo(null);
              }}
            >
              Reset sample
            </button>
          </div>

          <div className="data-note">
            <span className="status-pill">Source: {uploadName}</span>
            <span className="status-pill">Project: {data.project_id}</span>
            <span className="status-pill">Exported: {new Date(data.exported_at).toLocaleString()}</span>
          </div>
        </motion.div>

        <motion.div
          className="hero-panel"
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="hero-panel-inner">
            <h2>Pitch headline</h2>
            <p>
              The workflow dataset shows {summary.productivityEventCount} productivity analyses across {summary.workflowCount}{' '}
              workflows, with {summary.matchedRepoCount} repositories confidently represented in repo-level comparisons.
            </p>
            <div className="mini-metrics">
              <div>
                <span>Total savings</span>
                <strong>{currency.format(summary.totalCostSaved)}</strong>
              </div>
              <div>
                <span>Time saved</span>
                <strong>{minutesToHoursText(summary.totalTimeSaved)}</strong>
              </div>
              <div>
                <span>Avg efficiency</span>
                <strong>{numberFmt.format(summary.avgEfficiency)}%</strong>
              </div>
            </div>
          </div>
        </motion.div>
      </header>

      <section className="kpi-grid">
        <KpiCard title="Estimated Cost Saved" value={currency.format(summary.totalCostSaved)} subtitle="Across all productivity analyses" accent="emerald" icon="↗" />
        <KpiCard title="Manual Hours Avoided" value={minutesToHoursText(summary.totalTimeSaved)} subtitle="Total manual effort compressed by the workflow" accent="cyan" icon="⏱" />
        <KpiCard title="Avg AI Resolution Time" value={`${numberFmt.format(summary.avgAiMinutes)} min`} subtitle="Average time spent by the AI workflow per event" accent="violet" icon="⚡" />
        <KpiCard title="Average Efficiency Gain" value={`${numberFmt.format(summary.avgEfficiency)}%`} subtitle="Relative reduction versus manual effort" accent="amber" icon="◎" />
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Interactive analysis</span>
          <h2>Repository and workflow performance</h2>
        </div>
      </section>

      <section className="charts-grid two-up">
        <ChartCard title="Average Cost Saved by Repository" subtitle="Aggregated by repository, averaged across matched runs">
          {hasRepoData ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={repoBarData}>
                <CartesianGrid stroke={COLORS.grid} vertical={false} />
                <XAxis dataKey="repo" tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value: number) => currency.format(value)} />
                <Bar dataKey="avgCostSaved" radius={[10, 10, 0, 0]} fill="url(#costGradient)" />
                <defs>
                  <linearGradient id="costGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#49e29c" />
                    <stop offset="100%" stopColor="#1aa6ff" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage text="No repository-level matches were found in this file." />
          )}
        </ChartCard>

        <ChartCard title="Time Saved by Repository" subtitle="Average minutes saved for each repository with matched events">
          {hasRepoData ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={repoBarData}>
                <CartesianGrid stroke={COLORS.grid} vertical={false} />
                <XAxis dataKey="repo" tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value: number) => `${numberFmt.format(value)} min`} />
                <Bar dataKey="avgTimeSaved" radius={[10, 10, 0, 0]} fill="url(#timeGradient)" />
                <defs>
                  <linearGradient id="timeGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#8f75ff" />
                    <stop offset="100%" stopColor="#39d0ff" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage text="Upload a dataset with workflows and productivity events to populate this chart." />
          )}
        </ChartCard>
      </section>

      <section className="charts-grid two-up">
        <ChartCard title="Manual Effort vs AI Resolution" subtitle="Each point represents one matched productivity event">
          {hasScatterData ? (
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 16, right: 12, bottom: 16, left: 0 }}>
                <CartesianGrid stroke={COLORS.grid} />
                <XAxis type="number" dataKey="manual" name="Manual effort" unit=" min" tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis type="number" dataKey="ai" name="AI resolution" unit=" min" tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ strokeDasharray: '5 5' }} formatter={(value: number) => `${numberFmt.format(value)} min`} />
                <Scatter data={scatterData} fill="#8b7cff" />
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage text="No matched event pairs are available for this scatter view." />
          )}
        </ChartCard>

        <ChartCard title="Confidence Distribution" subtitle="Transparent matching confidence for repository-level analytics">
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie data={confidenceData} dataKey="value" nameKey="name" outerRadius={104} innerRadius={64} paddingAngle={3}>
                {confidenceData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => `${value} events`} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      <section className="charts-grid two-up">
        <ChartCard title="Average Manual Work Composition" subtitle="Where manual effort is typically spent per repository">
          {hasRepoData ? (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={breakdownData}>
                <CartesianGrid stroke={COLORS.grid} vertical={false} />
                <XAxis dataKey="repo" tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value: number) => `${numberFmt.format(value)} min`} />
                <Legend />
                <Bar dataKey="ciTriage" stackId="a" fill="#39d0ff" radius={[0, 0, 0, 0]} />
                <Bar dataKey="buildVerify" stackId="a" fill="#8b7cff" />
                <Bar dataKey="fixImplementation" stackId="a" fill="#3ee089" />
                <Bar dataKey="comprehension" stackId="a" fill="#ffbf5f" />
                <Bar dataKey="rootCause" stackId="a" fill="#ff7bbd" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage text="This chart will appear once repository matches are available." />
          )}
        </ChartCard>

        <ChartCard title="Iterations and Files Modified" subtitle="Average operational intensity by repository">
          {hasRepoData ? (
            <ResponsiveContainer width="100%" height={340}>
              <AreaChart data={areaData}>
                <CartesianGrid stroke={COLORS.grid} vertical={false} />
                <XAxis dataKey="repo" tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value: number) => numberFmt.format(value)} />
                <defs>
                  <linearGradient id="iterGrad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#39d0ff" stopOpacity={0.7} />
                    <stop offset="100%" stopColor="#39d0ff" stopOpacity={0.04} />
                  </linearGradient>
                  <linearGradient id="fileGrad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#8b7cff" stopOpacity={0.7} />
                    <stop offset="100%" stopColor="#8b7cff" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="avgIterations" stroke="#39d0ff" fill="url(#iterGrad)" strokeWidth={3} />
                <Area type="monotone" dataKey="avgFilesModified" stroke="#8b7cff" fill="url(#fileGrad)" strokeWidth={3} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage text="No repository-level data is currently available for this view." />
          )}
        </ChartCard>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Repository drill-down</span>
          <h2>Detailed comparison table</h2>
        </div>
      </section>

      <section className="drilldown-grid">
        <ChartCard title="Repository leaderboard" subtitle="Click a row to inspect averages and manual effort composition">
          {hasRepoData ? (
            <RepoTable
              repos={repoAggregates}
              selectedRepo={selectedRepoData?.repo || null}
              onSelect={(repo) => setSelectedRepo(repo)}
            />
          ) : (
            <EmptyChartMessage text="No repository rows are available for this dataset." />
          )}
        </ChartCard>

        <motion.section
          className="detail-card"
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="card-header">
            <div>
              <h3>{selectedRepoData?.repo || 'No repository selected'}</h3>
              <p>Average performance metrics across matched runs</p>
            </div>
          </div>

          {selectedRepoData ? (
            <div className="detail-grid">
              <div className="detail-metric"><span>Matched runs</span><strong>{selectedRepoData.runs}</strong></div>
              <div className="detail-metric"><span>Avg cost saved</span><strong>{currency.format(selectedRepoData.avgCostSaved)}</strong></div>
              <div className="detail-metric"><span>Avg time saved</span><strong>{numberFmt.format(selectedRepoData.avgTimeSaved)} min</strong></div>
              <div className="detail-metric"><span>Avg AI resolution</span><strong>{numberFmt.format(selectedRepoData.avgAiMinutes)} min</strong></div>
              <div className="detail-metric"><span>Avg manual effort</span><strong>{numberFmt.format(selectedRepoData.avgManualMinutes)} min</strong></div>
              <div className="detail-metric"><span>Efficiency</span><strong>{numberFmt.format(selectedRepoData.efficiencyPercent)}%</strong></div>

              <div className="breakdown-panel">
                <h4>Manual effort profile</h4>
                {renderBreakdownLine('CI triage', selectedRepoData.avgBreakdown.ciTriage)}
                {renderBreakdownLine('Build and verify', selectedRepoData.avgBreakdown.buildVerify)}
                {renderBreakdownLine('Fix implementation', selectedRepoData.avgBreakdown.fixImplementation)}
                {renderBreakdownLine('Codebase comprehension', selectedRepoData.avgBreakdown.codebaseComprehension)}
                {renderBreakdownLine('Root cause diagnosis', selectedRepoData.avgBreakdown.rootCauseDiagnosis)}
              </div>
            </div>
          ) : (
            <div className="empty-state">Upload a valid JSON file or use the bundled sample to populate the drill-down view.</div>
          )}
        </motion.section>
      </section>

      <footer className="footer-note">
        <strong>Methodology:</strong> overall metrics use all productivity events, while repository views use nearest-workflow timestamp matching with high, medium, and unassigned confidence states. This keeps the presentation professional without overstating repository attribution.
      </footer>
    </div>
  );
}

function EmptyChartMessage({ text }: { text: string }) {
  return <div className="empty-chart-message">{text}</div>;
}

function renderBreakdownLine(label: string, value: number) {
  return (
    <div className="breakdown-line" key={label}>
      <div className="breakdown-top">
        <span>{label}</span>
        <strong>{numberFmt.format(value)} min</strong>
      </div>
      <div className="breakdown-bar">
        <div className="breakdown-fill" style={{ width: `${Math.min(100, (value / 90) * 100)}%` }} />
      </div>
    </div>
  );
}

function shortRepo(repo: string) {
  return repo.split('/').pop() || repo;
}

function round(value: number) {
  return Math.round(value * 10) / 10;
}

export default App;
