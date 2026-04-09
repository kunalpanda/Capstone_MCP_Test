import React from 'react';
import {
  TrendingUp,
  Clock,
  DollarSign,
  Zap,
  FileCode,
  GitPullRequest,
  Search,
  Bug,
  Hammer,
  RotateCcw,
  CheckCircle2,
  BarChart3
} from 'lucide-react';
import { ProductivityAnalysis } from '../../services/types';
import './ProductivityWidget.css';

interface ProductivityWidgetProps {
  analysis: ProductivityAnalysis | null;
}

// Friendly labels and icons for breakdown categories
const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ReactNode }> = {
  codebase_comprehension: { label: 'Codebase analysis', icon: <Search size={14} /> },
  ci_triage: { label: 'CI/CD triage & log analysis', icon: <Bug size={14} /> },
  root_cause_diagnosis: { label: 'Root cause diagnosis', icon: <Zap size={14} /> },
  fix_implementation: { label: 'Fix implementation', icon: <Hammer size={14} /> },
  build_verify_cycles: { label: 'Build-verify cycles', icon: <RotateCcw size={14} /> },
  pr_creation: { label: 'PR creation & docs', icon: <GitPullRequest size={14} /> },
  change_verification: { label: 'Change verification', icon: <CheckCircle2 size={14} /> },
  diff_inspections: { label: 'Diff inspections', icon: <FileCode size={14} /> },
};

const formatMinutes = (minutes: number): string => {
  if (minutes < 60) return `${Math.round(minutes)}m`;
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
};

export const ProductivityWidget: React.FC<ProductivityWidgetProps> = ({ analysis }) => {
  if (!analysis) {
    return (
      <div className="productivity-widget productivity-widget--empty">
        <div className="productivity-widget__empty-state">
          <BarChart3 size={32} />
          <span className="productivity-widget__empty-title">No Analysis Yet</span>
          <span className="productivity-widget__empty-text">
            Productivity metrics will appear after a workflow completes
          </span>
        </div>
      </div>
    );
  }

  const { breakdown, total_manual_minutes, ai_resolution_minutes, time_saved_minutes, cost_saved, hourly_rate } = analysis;

  // Build the sorted breakdown items (only non-zero)
  const breakdownItems = Object.entries(breakdown)
    .filter(([, item]) => item.minutes > 0)
    .sort(([, a], [, b]) => b.minutes - a.minutes);

  const maxMinutes = breakdownItems.length > 0
    ? Math.max(...breakdownItems.map(([, item]) => item.minutes))
    : 1;

  return (
    <div className="productivity-widget">
      {/* Hero metrics */}
      <div className="productivity-widget__hero">
        <div className="productivity-widget__hero-card productivity-widget__hero-card--savings">
          <div className="productivity-widget__hero-icon">
            <Clock size={18} />
          </div>
          <div className="productivity-widget__hero-content">
            <span className="productivity-widget__hero-value">
              {formatMinutes(time_saved_minutes)}
            </span>
            <span className="productivity-widget__hero-label">Time saved</span>
          </div>
        </div>

        <div className="productivity-widget__hero-card productivity-widget__hero-card--cost">
          <div className="productivity-widget__hero-icon">
            <DollarSign size={18} />
          </div>
          <div className="productivity-widget__hero-content">
            <span className="productivity-widget__hero-value">
              ${Math.round(cost_saved).toLocaleString()}
            </span>
            <span className="productivity-widget__hero-label">Cost saved</span>
          </div>
        </div>
      </div>

      {/* Comparison bar */}
      <div className="productivity-widget__comparison">
        <div className="productivity-widget__comparison-row">
          <span className="productivity-widget__comparison-label">Manual effort</span>
          <div className="productivity-widget__comparison-bar">
            <div
              className="productivity-widget__comparison-fill productivity-widget__comparison-fill--manual"
              style={{ width: '100%' }}
            />
          </div>
          <span className="productivity-widget__comparison-value">
            {formatMinutes(total_manual_minutes)}
          </span>
        </div>
        <div className="productivity-widget__comparison-row">
          <span className="productivity-widget__comparison-label">AI resolution</span>
          <div className="productivity-widget__comparison-bar">
            <div
              className="productivity-widget__comparison-fill productivity-widget__comparison-fill--ai"
              style={{ width: `${Math.max((ai_resolution_minutes / total_manual_minutes) * 100, 2)}%` }}
            />
          </div>
          <span className="productivity-widget__comparison-value">
            {formatMinutes(ai_resolution_minutes)}
          </span>
        </div>
      </div>

      {/* Breakdown */}
      <div className="productivity-widget__breakdown">
        <div className="productivity-widget__breakdown-header">
          <TrendingUp size={14} />
          <span>Effort breakdown</span>
        </div>
        <div className="productivity-widget__breakdown-list">
          {breakdownItems.map(([key, item]) => {
            const config = CATEGORY_CONFIG[key] || { label: key, icon: <Zap size={14} /> };
            const barWidth = (item.minutes / maxMinutes) * 100;

            return (
              <div key={key} className="productivity-widget__breakdown-item">
                <div className="productivity-widget__breakdown-item-header">
                  <span className="productivity-widget__breakdown-item-icon">{config.icon}</span>
                  <span className="productivity-widget__breakdown-item-label">{config.label}</span>
                  <span className="productivity-widget__breakdown-item-value">{formatMinutes(item.minutes)}</span>
                </div>
                <div className="productivity-widget__breakdown-item-bar">
                  <div
                    className="productivity-widget__breakdown-item-fill"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="productivity-widget__footer">
        <span className="productivity-widget__footer-note">
          Based on industry benchmarks @ ${hourly_rate}/hr loaded cost
        </span>
      </div>
    </div>
  );
};

export default ProductivityWidget;
