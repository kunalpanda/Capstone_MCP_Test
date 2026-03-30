import { useState, useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from "recharts";

// ============================================================
// EMBEDDED DATA — exported from Firestore via export_firestore_data.py
// ============================================================
const RAW_DATA = {
  workflows: {
    "6b7f11353d9bc4fb": { repo: "kunalpanda/cargo-tracker-test", status: "completed", iteration: 48, completedAt: "2026-03-29T05:26:42.663000+00:00", createdAt: "2026-03-29T05:06:15.506651+00:00" },
    "8a0afe43108358ec": { repo: "kunalpanda/space-rover-test", status: "completed", iteration: 27, completedAt: "2026-03-26T20:20:37.788000+00:00", createdAt: "2026-03-26T20:13:30.713474+00:00" },
    "8b9999a64d3752fd": { repo: "kunalpanda/pet-clinic-test", status: "completed", iteration: 16, completedAt: "2026-03-29T04:03:20.465000+00:00", createdAt: "2026-03-29T03:55:19.768749+00:00" },
    "ac7a3ea77ce843e2": { repo: "kunalpanda/Liberty-bikes-test", status: "completed", iteration: 30, completedAt: "2026-03-29T04:54:49.606000+00:00", createdAt: "2026-03-29T04:43:59.757760+00:00" },
    "f41e8fc77f31ab25": { repo: "kunalpanda/daytrader-test", status: "completed", iteration: 29, completedAt: "2026-03-29T04:37:25.324000+00:00", createdAt: "2026-03-29T04:30:26.710455+00:00" },
  },
  events: [
    { timestamp: "2026-03-26T20:11:58.473020", data: { cost_saved: 294.0, total_manual_minutes: 235, ai_resolution_minutes: 5.4, time_saved_minutes: 229.6, total_manual_hours: 3.92, iteration_count: 21, files_modified: 5, hourly_rate: 75, breakdown: { codebase_comprehension: { minutes: 30, classification: "medium" }, ci_triage: { minutes: 45, components: { coverage_analysis: 15, test_result_analysis: 20, build_status_check: 10 } }, root_cause_diagnosis: { minutes: 20, classification: "simple" }, fix_implementation: { minutes: 75, classification: "both" }, build_verify_cycles: { minutes: 30, count: 1 }, pr_creation: { minutes: 20, created: true }, change_verification: { minutes: 15, files_verified: 3 }, diff_inspections: { minutes: 0, count: 0 } } } },
    { timestamp: "2026-03-26T20:20:37.618498", data: { cost_saved: 399.75, total_manual_minutes: 320, ai_resolution_minutes: 6.6, time_saved_minutes: 313.4, total_manual_hours: 5.33, iteration_count: 27, files_modified: 5, hourly_rate: 75, breakdown: { codebase_comprehension: { minutes: 30, classification: "medium" }, ci_triage: { minutes: 75, components: { test_result_analysis: 20, coverage_analysis: 15, console_log_analysis: 30, build_status_check: 10 } }, root_cause_diagnosis: { minutes: 20, classification: "simple" }, fix_implementation: { minutes: 75, classification: "both" }, build_verify_cycles: { minutes: 90, count: 3 }, pr_creation: { minutes: 20, created: true }, change_verification: { minutes: 10, files_verified: 2 }, diff_inspections: { minutes: 0, count: 0 } } } },
    { timestamp: "2026-03-29T04:03:20.330046", data: { cost_saved: 162.75, total_manual_minutes: 130, ai_resolution_minutes: 5.7, time_saved_minutes: 124.3, total_manual_hours: 2.17, iteration_count: 16, files_modified: 6, hourly_rate: 75, breakdown: { codebase_comprehension: { minutes: 45, classification: "large" }, ci_triage: { minutes: 0, components: {} }, root_cause_diagnosis: { minutes: 0, classification: "none" }, fix_implementation: { minutes: 60, classification: "create_new" }, build_verify_cycles: { minutes: 0, count: 0 }, pr_creation: { minutes: 20, created: true }, change_verification: { minutes: 5, files_verified: 1 }, diff_inspections: { minutes: 0, count: 0 } } } },
    { timestamp: "2026-03-29T04:37:25.210149", data: { cost_saved: 437.25, total_manual_minutes: 350, ai_resolution_minutes: 6.2, time_saved_minutes: 343.8, total_manual_hours: 5.83, iteration_count: 29, files_modified: 3, hourly_rate: 75, breakdown: { codebase_comprehension: { minutes: 30, classification: "medium" }, ci_triage: { minutes: 60, components: { test_result_analysis: 20, console_log_analysis: 30, build_status_check: 10 } }, root_cause_diagnosis: { minutes: 60, classification: "moderate" }, fix_implementation: { minutes: 75, classification: "both" }, build_verify_cycles: { minutes: 90, count: 3 }, pr_creation: { minutes: 20, created: true }, change_verification: { minutes: 15, files_verified: 3 }, diff_inspections: { minutes: 0, count: 0 } } } },
    { timestamp: "2026-03-29T04:54:49.475920", data: { cost_saved: 468.75, total_manual_minutes: 375, ai_resolution_minutes: 10.2, time_saved_minutes: 364.8, total_manual_hours: 6.25, iteration_count: 30, files_modified: 5, hourly_rate: 75, breakdown: { codebase_comprehension: { minutes: 45, classification: "large" }, ci_triage: { minutes: 75, components: { test_result_analysis: 20, coverage_analysis: 15, console_log_analysis: 30, build_status_check: 10 } }, root_cause_diagnosis: { minutes: 60, classification: "moderate" }, fix_implementation: { minutes: 75, classification: "both" }, build_verify_cycles: { minutes: 90, count: 3 }, pr_creation: { minutes: 20, created: true }, change_verification: { minutes: 10, files_verified: 2 }, diff_inspections: { minutes: 0, count: 0 } } } },
    { timestamp: "2026-03-29T05:26:42.541733", data: { cost_saved: 531.0, total_manual_minutes: 425, ai_resolution_minutes: 18.9, time_saved_minutes: 406.1, total_manual_hours: 7.08, iteration_count: 48, files_modified: 6, hourly_rate: 75, breakdown: { codebase_comprehension: { minutes: 45, classification: "large" }, ci_triage: { minutes: 75, components: { test_result_analysis: 20, coverage_analysis: 15, console_log_analysis: 30, build_status_check: 10 } }, root_cause_diagnosis: { minutes: 60, classification: "moderate" }, fix_implementation: { minutes: 75, classification: "both" }, build_verify_cycles: { minutes: 120, count: 4 }, pr_creation: { minutes: 20, created: true }, change_verification: { minutes: 20, files_verified: 4 }, diff_inspections: { minutes: 10, count: 1 } } } },
  ],
};

// Repo short names for display
const repoShortName = (full) => full.split("/")[1]?.replace(/-test$/, "").replace(/-/g, " ") || full;

// Match events to workflows by timestamp proximity
const WORKFLOW_ORDER = ["space-rover-test", "space-rover-test", "pet-clinic-test", "daytrader-test", "Liberty-bikes-test", "cargo-tracker-test"];
const REPO_LABELS = ["Space Rover (R1)", "Space Rover (R2)", "Pet Clinic", "DayTrader", "Liberty Bikes", "Cargo Tracker"];

// ============================================================
// COMPUTED DATA
// ============================================================
const computeMetrics = () => {
  const events = RAW_DATA.events;
  const totalTimeSaved = events.reduce((s, e) => s + e.data.time_saved_minutes, 0);
  const totalCostSaved = events.reduce((s, e) => s + e.data.cost_saved, 0);
  const totalManualMin = events.reduce((s, e) => s + e.data.total_manual_minutes, 0);
  const totalAiMin = events.reduce((s, e) => s + e.data.ai_resolution_minutes, 0);
  const avgTimeSaved = totalTimeSaved / events.length;
  const avgEfficiency = ((totalTimeSaved / totalManualMin) * 100);

  return { totalTimeSaved, totalCostSaved, totalManualMin, totalAiMin, avgTimeSaved, avgEfficiency, runCount: events.length };
};

const COLORS = {
  primary: "#3b82f6",
  primaryLight: "#60a5fa",
  success: "#10b981",
  successLight: "#34d399",
  warning: "#f59e0b",
  danger: "#ef4444",
  purple: "#8b5cf6",
  pink: "#ec4899",
  cyan: "#06b6d4",
  orange: "#f97316",
  teal: "#14b8a6",
  indigo: "#6366f1",
  slate: "#64748b",
};

const EFFORT_COLORS = [COLORS.primary, COLORS.cyan, COLORS.purple, COLORS.success, COLORS.warning, COLORS.pink, COLORS.orange, COLORS.teal];

const CATEGORY_LABELS = {
  codebase_comprehension: "Codebase Analysis",
  ci_triage: "CI/CD Triage",
  root_cause_diagnosis: "Root Cause Diagnosis",
  fix_implementation: "Fix Implementation",
  build_verify_cycles: "Build & Verify Cycles",
  pr_creation: "PR Creation",
  change_verification: "Change Verification",
  diff_inspections: "Diff Inspections",
};

// ============================================================
// COMPONENTS
// ============================================================

const KPICard = ({ label, value, subtitle, icon, accent = COLORS.primary }) => (
  <div style={{
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 12,
    padding: "24px 28px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
    position: "relative",
    overflow: "hidden",
  }}>
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${accent}, transparent)` }} />
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "rgba(255,255,255,0.5)" }}>{label}</span>
    </div>
    <div style={{ fontSize: 36, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em", lineHeight: 1.1 }}>{value}</div>
    {subtitle && <div style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", marginTop: 2 }}>{subtitle}</div>}
  </div>
);

const SectionTitle = ({ children, subtitle }) => (
  <div style={{ marginBottom: 20 }}>
    <h2 style={{ fontSize: 18, fontWeight: 600, color: "#e2e8f0", margin: 0, letterSpacing: "-0.01em" }}>{children}</h2>
    {subtitle && <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", margin: "4px 0 0" }}>{subtitle}</p>}
  </div>
);

const ChartCard = ({ children, style = {} }) => (
  <div style={{
    background: "rgba(255,255,255,0.02)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 12,
    padding: 24,
    ...style,
  }}>
    {children}
  </div>
);

const CustomTooltip = ({ active, payload, label, formatter }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#1e293b",
      border: "1px solid rgba(255,255,255,0.15)",
      borderRadius: 8,
      padding: "12px 16px",
      boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
    }}>
      <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 600, color: "#94a3b8" }}>{label}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ margin: "4px 0", fontSize: 13, color: entry.color || "#e2e8f0" }}>
          {entry.name}: <strong>{formatter ? formatter(entry.value) : entry.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ============================================================
// MAIN DASHBOARD
// ============================================================
export default function ProductivityDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const metrics = useMemo(computeMetrics, []);
  const events = RAW_DATA.events;

  // Chart data: Human vs AI time per workflow
  const comparisonData = events.map((e, i) => ({
    name: REPO_LABELS[i],
    "Human Estimate (min)": e.data.total_manual_minutes,
    "AI Resolution (min)": e.data.ai_resolution_minutes,
  }));

  // Effort breakdown aggregated
  const effortAggregated = useMemo(() => {
    const totals = {};
    events.forEach((e) => {
      Object.entries(e.data.breakdown).forEach(([key, val]) => {
        totals[key] = (totals[key] || 0) + (val.minutes || 0);
      });
    });
    return Object.entries(totals)
      .filter(([_, v]) => v > 0)
      .map(([key, value]) => ({ name: CATEGORY_LABELS[key] || key, value, key }))
      .sort((a, b) => b.value - a.value);
  }, []);

  // Trend data
  const trendData = events.map((e, i) => ({
    name: REPO_LABELS[i],
    "Time Saved (min)": Math.round(e.data.time_saved_minutes),
    "Cost Saved ($)": e.data.cost_saved,
    "AI Time (min)": e.data.ai_resolution_minutes,
  }));

  // Cumulative savings
  const cumulativeData = events.reduce((acc, e, i) => {
    const prev = acc[acc.length - 1] || { cumTime: 0, cumCost: 0 };
    acc.push({
      name: REPO_LABELS[i],
      cumTime: Math.round(prev.cumTime + e.data.time_saved_minutes),
      cumCost: Math.round((prev.cumCost + e.data.cost_saved) * 100) / 100,
    });
    return acc;
  }, []);

  // Per-workflow detail
  const detailData = events.map((e, i) => ({
    repo: REPO_LABELS[i],
    iterations: e.data.iteration_count,
    filesModified: e.data.files_modified,
    manualMin: e.data.total_manual_minutes,
    aiMin: e.data.ai_resolution_minutes,
    savedMin: Math.round(e.data.time_saved_minutes),
    costSaved: e.data.cost_saved,
    diagnosis: e.data.breakdown.root_cause_diagnosis?.classification || "—",
    buildCycles: e.data.breakdown.build_verify_cycles?.count || 0,
  }));

  // Efficiency ratio per run
  const efficiencyData = events.map((e, i) => ({
    name: REPO_LABELS[i],
    ratio: Math.round(e.data.total_manual_minutes / e.data.ai_resolution_minutes),
  }));

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "breakdown", label: "Effort Breakdown" },
    { id: "trends", label: "Trends" },
    { id: "details", label: "Run Details" },
  ];

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0f172a",
      color: "#e2e8f0",
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      padding: 0,
      margin: 0,
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        padding: "24px 40px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: "rgba(255,255,255,0.01)",
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18,
            }}>⚡</div>
            <div>
              <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, letterSpacing: "-0.02em" }}>
                AI CI/CD Productivity Dashboard
              </h1>
              <p style={{ margin: 0, fontSize: 12, color: "rgba(255,255,255,0.4)" }}>
                Autonomous test repair & generation — powered by Claude
              </p>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 12, color: "rgba(255,255,255,0.4)" }}>
          <span>{events.length} workflow runs analyzed</span>
          <span style={{
            background: "rgba(16,185,129,0.15)", color: "#10b981",
            padding: "4px 12px", borderRadius: 20, fontWeight: 600, fontSize: 11,
          }}>LIVE DATA</span>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", gap: 2, padding: "0 40px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        background: "rgba(255,255,255,0.01)",
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "14px 24px",
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
              color: activeTab === tab.id ? "#e2e8f0" : "rgba(255,255,255,0.4)",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid #3b82f6" : "2px solid transparent",
              cursor: "pointer",
              transition: "all 0.15s ease",
              fontFamily: "inherit",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ padding: "32px 40px", maxWidth: 1280, margin: "0 auto" }}>
        {/* ==================== OVERVIEW TAB ==================== */}
        {activeTab === "overview" && (
          <>
            {/* KPI Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
              <KPICard
                icon="⏱"
                label="Total Time Saved"
                value={`${Math.round(metrics.totalTimeSaved / 60 * 10) / 10} hrs`}
                subtitle={`${Math.round(metrics.totalTimeSaved)} min across ${metrics.runCount} runs`}
                accent={COLORS.success}
              />
              <KPICard
                icon="💰"
                label="Total Cost Savings"
                value={`$${metrics.totalCostSaved.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                subtitle={`At $75/hr loaded developer rate`}
                accent={COLORS.primary}
              />
              <KPICard
                icon="🚀"
                label="Speed Advantage"
                value={`${Math.round(metrics.totalManualMin / metrics.totalAiMin)}x faster`}
                subtitle={`${Math.round(metrics.totalAiMin)} min AI vs ${Math.round(metrics.totalManualMin)} min manual`}
                accent={COLORS.purple}
              />
              <KPICard
                icon="📈"
                label="Avg Efficiency"
                value={`${Math.round(metrics.avgEfficiency)}%`}
                subtitle={`Avg ${Math.round(metrics.avgTimeSaved)} min saved per run`}
                accent={COLORS.warning}
              />
            </div>

            {/* Human vs AI comparison */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
              <ChartCard>
                <SectionTitle subtitle="Estimated manual effort vs actual AI resolution time per workflow">
                  Human vs AI Resolution Time
                </SectionTitle>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={comparisonData} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} angle={-20} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "Minutes", angle: -90, position: "insideLeft", fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip formatter={(v) => `${v} min`} />} />
                    <Legend wrapperStyle={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }} />
                    <Bar dataKey="Human Estimate (min)" fill={COLORS.slate} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="AI Resolution (min)" fill={COLORS.success} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard>
                <SectionTitle subtitle="How many times faster AI resolved each workflow vs manual estimate">
                  Efficiency Multiplier per Run
                </SectionTitle>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={efficiencyData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "× faster", position: "insideBottom", offset: -5, fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} width={100} />
                    <Tooltip content={<CustomTooltip formatter={(v) => `${v}× faster`} />} />
                    <Bar dataKey="ratio" radius={[0, 6, 6, 0]}>
                      {efficiencyData.map((_, i) => (
                        <Cell key={i} fill={[COLORS.primary, COLORS.primaryLight, COLORS.cyan, COLORS.purple, COLORS.indigo, COLORS.teal][i % 6]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            {/* Cumulative savings */}
            <ChartCard>
              <SectionTitle subtitle="Running total of developer time and cost recovered across all workflow runs">
                Cumulative Savings Over Time
              </SectionTitle>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={cumulativeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} />
                  <YAxis yAxisId="time" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "Minutes", angle: -90, position: "insideLeft", fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
                  <YAxis yAxisId="cost" orientation="right" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "USD ($)", angle: 90, position: "insideRight", fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }} />
                  <Line yAxisId="time" type="monotone" dataKey="cumTime" stroke={COLORS.success} strokeWidth={2.5} dot={{ r: 5, fill: COLORS.success }} name="Cumulative Time Saved (min)" />
                  <Line yAxisId="cost" type="monotone" dataKey="cumCost" stroke={COLORS.primary} strokeWidth={2.5} dot={{ r: 5, fill: COLORS.primary }} name="Cumulative Cost Saved ($)" />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </>
        )}

        {/* ==================== BREAKDOWN TAB ==================== */}
        {activeTab === "breakdown" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
              <ChartCard>
                <SectionTitle subtitle="Where developer time would be spent — aggregated across all runs">
                  Effort Distribution by Category
                </SectionTitle>
                <ResponsiveContainer width="100%" height={360}>
                  <PieChart>
                    <Pie
                      data={effortAggregated}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={130}
                      dataKey="value"
                      paddingAngle={3}
                      stroke="none"
                    >
                      {effortAggregated.map((_, i) => (
                        <Cell key={i} fill={EFFORT_COLORS[i % EFFORT_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload;
                        const total = effortAggregated.reduce((s, x) => s + x.value, 0);
                        return (
                          <div style={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, padding: "10px 14px", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
                            <p style={{ margin: "0 0 4px", fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{d.name}</p>
                            <p style={{ margin: 0, fontSize: 12, color: "#94a3b8" }}>{d.value} min ({Math.round(d.value / total * 100)}%)</p>
                          </div>
                        );
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard>
                <SectionTitle subtitle="Total minutes per effort category across all workflows">
                  Effort Category Ranking
                </SectionTitle>
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={effortAggregated} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "Minutes", position: "insideBottom", offset: -5, fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} width={140} />
                    <Tooltip content={<CustomTooltip formatter={(v) => `${v} min`} />} />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]} name="Total Minutes">
                      {effortAggregated.map((_, i) => (
                        <Cell key={i} fill={EFFORT_COLORS[i % EFFORT_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            {/* Per-run breakdown stacked bar */}
            <ChartCard>
              <SectionTitle subtitle="How each workflow's manual effort estimate breaks down by category">
                Per-Workflow Effort Composition
              </SectionTitle>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={events.map((e, i) => {
                  const row = { name: REPO_LABELS[i] };
                  Object.entries(e.data.breakdown).forEach(([key, val]) => {
                    row[CATEGORY_LABELS[key] || key] = val.minutes || 0;
                  });
                  return row;
                })}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} angle={-20} textAnchor="end" height={60} />
                  <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "Minutes", angle: -90, position: "insideLeft", fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip formatter={(v) => `${v} min`} />} />
                  <Legend wrapperStyle={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }} />
                  {effortAggregated.map((cat, i) => (
                    <Bar key={cat.name} dataKey={cat.name} stackId="a" fill={EFFORT_COLORS[i % EFFORT_COLORS.length]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </>
        )}

        {/* ==================== TRENDS TAB ==================== */}
        {activeTab === "trends" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
              <ChartCard>
                <SectionTitle subtitle="Time savings trajectory across sequential workflow runs">
                  Time Saved per Run
                </SectionTitle>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} angle={-20} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }} />
                    <Line type="monotone" dataKey="Time Saved (min)" stroke={COLORS.success} strokeWidth={2.5} dot={{ r: 5, fill: COLORS.success }} />
                    <Line type="monotone" dataKey="AI Time (min)" stroke={COLORS.warning} strokeWidth={2} dot={{ r: 4, fill: COLORS.warning }} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard>
                <SectionTitle subtitle="Dollar value recovered per workflow run">
                  Cost Savings per Run
                </SectionTitle>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} angle={-20} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
                    <Tooltip content={<CustomTooltip formatter={(v) => `$${v}`} />} />
                    <Bar dataKey="Cost Saved ($)" radius={[6, 6, 0, 0]}>
                      {trendData.map((_, i) => (
                        <Cell key={i} fill={[COLORS.primary, COLORS.primaryLight, COLORS.cyan, COLORS.purple, COLORS.indigo, COLORS.teal][i % 6]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            <ChartCard>
              <SectionTitle subtitle="Iteration count and files modified per workflow — indicators of workflow complexity">
                Workflow Complexity Indicators
              </SectionTitle>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={events.map((e, i) => ({ name: REPO_LABELS[i], Iterations: e.data.iteration_count, "Files Modified": e.data.files_modified }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} angle={-20} textAnchor="end" height={60} />
                  <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }} />
                  <Bar dataKey="Iterations" fill={COLORS.purple} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Files Modified" fill={COLORS.cyan} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </>
        )}

        {/* ==================== DETAILS TAB ==================== */}
        {activeTab === "details" && (
          <ChartCard>
            <SectionTitle subtitle="Per-workflow breakdown with key metrics and classifications">
              Workflow Run Details
            </SectionTitle>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                    {["Repository", "Iterations", "Files", "Manual (min)", "AI (min)", "Saved (min)", "Cost Saved", "Diagnosis", "Build Cycles"].map((h) => (
                      <th key={h} style={{ padding: "12px 14px", textAlign: "left", fontWeight: 600, color: "rgba(255,255,255,0.5)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detailData.map((row, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", transition: "background 0.15s" }}
                      onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
                      onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
                      <td style={{ padding: "14px", fontWeight: 600, color: "#e2e8f0" }}>{row.repo}</td>
                      <td style={{ padding: "14px", color: "#94a3b8" }}>{row.iterations}</td>
                      <td style={{ padding: "14px", color: "#94a3b8" }}>{row.filesModified}</td>
                      <td style={{ padding: "14px", color: "#94a3b8" }}>{row.manualMin}</td>
                      <td style={{ padding: "14px" }}>
                        <span style={{ color: COLORS.success, fontWeight: 600 }}>{row.aiMin}</span>
                      </td>
                      <td style={{ padding: "14px" }}>
                        <span style={{ color: COLORS.success, fontWeight: 600 }}>{row.savedMin}</span>
                      </td>
                      <td style={{ padding: "14px", fontWeight: 600, color: COLORS.primary }}>${row.costSaved}</td>
                      <td style={{ padding: "14px" }}>
                        <span style={{
                          padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 600,
                          background: row.diagnosis === "moderate" ? "rgba(245,158,11,0.15)" : row.diagnosis === "simple" ? "rgba(16,185,129,0.15)" : "rgba(100,116,139,0.15)",
                          color: row.diagnosis === "moderate" ? COLORS.warning : row.diagnosis === "simple" ? COLORS.success : COLORS.slate,
                        }}>{row.diagnosis}</span>
                      </td>
                      <td style={{ padding: "14px", color: "#94a3b8" }}>{row.buildCycles}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Summary row */}
            <div style={{
              marginTop: 20, padding: "16px 20px", borderRadius: 8,
              background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)",
              display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13,
            }}>
              <span style={{ color: "rgba(255,255,255,0.6)" }}>
                <strong style={{ color: "#e2e8f0" }}>Totals across {detailData.length} runs:</strong>
              </span>
              <div style={{ display: "flex", gap: 32 }}>
                <span style={{ color: "#94a3b8" }}>Manual: <strong style={{ color: "#e2e8f0" }}>{detailData.reduce((s, r) => s + r.manualMin, 0)} min</strong></span>
                <span style={{ color: "#94a3b8" }}>AI: <strong style={{ color: COLORS.success }}>{Math.round(detailData.reduce((s, r) => s + r.aiMin, 0) * 10) / 10} min</strong></span>
                <span style={{ color: "#94a3b8" }}>Saved: <strong style={{ color: COLORS.success }}>{detailData.reduce((s, r) => s + r.savedMin, 0)} min</strong></span>
                <span style={{ color: "#94a3b8" }}>Cost: <strong style={{ color: COLORS.primary }}>${detailData.reduce((s, r) => s + r.costSaved, 0).toLocaleString()}</strong></span>
              </div>
            </div>
          </ChartCard>
        )}

        {/* Footer */}
        <div style={{
          marginTop: 40, paddingTop: 20,
          borderTop: "1px solid rgba(255,255,255,0.06)",
          display: "flex", justifyContent: "space-between",
          fontSize: 11, color: "rgba(255,255,255,0.25)",
        }}>
          <span>Time estimates based on published research (Xia et al., Incredibuild, Gloria Mark/UC Irvine, Graphite 2024). See productivity_rubric_research.md for citations.</span>
          <span>Exported {new Date().toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
