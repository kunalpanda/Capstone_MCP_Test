// src/components/Widgets/CoverageWidget.tsx
// Displays test coverage metrics with visual charts

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer
} from 'recharts';
import {
  Target,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { CoverageMetrics } from '../../services/types';
import './CoverageWidget.css';

interface CoverageWidgetProps {
  currentCoverage: CoverageMetrics | null;
  targetCoverage: CoverageMetrics | null;
}

interface CoverageItemProps {
  label: string;
  current?: number;
  target?: number;
}

const CoverageItem: React.FC<CoverageItemProps> = ({ label, current, target }) => {
  if (current === undefined) {
    return (
      <div className="coverage-item coverage-item--empty">
        <div className="coverage-item__header">
          <span className="coverage-item__label">{label}</span>
          <span className="coverage-item__value">N/A</span>
        </div>
      </div>
    );
  }

  const targetValue = target || 0;
  const gap = targetValue - current;
  const isMet = target ? current >= target : true;

  return (
    <div className={`coverage-item ${isMet ? 'coverage-item--met' : 'coverage-item--unmet'}`}>
      <div className="coverage-item__header">
        <span className="coverage-item__label">{label}</span>
        <div className="coverage-item__values">
          <span className="coverage-item__current">{current.toFixed(1)}%</span>
          {target && (
            <>
              <span className="coverage-item__separator">/</span>
              <span className="coverage-item__target">{target}%</span>
            </>
          )}
        </div>
      </div>
      
      <div className="coverage-item__bar">
        <div
          className="coverage-item__bar-fill"
          style={{ width: `${Math.min(current, 100)}%` }}
        />
        {target && (
          <div
            className="coverage-item__bar-target"
            style={{ left: `${Math.min(target, 100)}%` }}
          />
        )}
      </div>

      <div className="coverage-item__footer">
        {isMet ? (
          <span className="coverage-item__status coverage-item__status--met">
            <CheckCircle2 size={12} />
            Target met
          </span>
        ) : (
          <span className="coverage-item__status coverage-item__status--unmet">
            <AlertCircle size={12} />
            {Math.abs(gap).toFixed(1)}% below target
          </span>
        )}
      </div>
    </div>
  );
};

export const CoverageWidget: React.FC<CoverageWidgetProps> = ({
  currentCoverage,
  targetCoverage
}) => {
  // Check if we have any coverage data
  const hasCoverage = currentCoverage && (
    currentCoverage.line !== undefined ||
    currentCoverage.branch !== undefined ||
    currentCoverage.method !== undefined
  );

  if (!hasCoverage) {
    return (
      <div className="coverage-widget coverage-widget--empty">
        <div className="coverage-widget__empty-state">
          <Target size={32} />
          <span className="coverage-widget__empty-title">No Coverage Data</span>
          <span className="coverage-widget__empty-text">
            Coverage metrics will appear here when available
          </span>
        </div>
      </div>
    );
  }

  // Calculate overall coverage
  const coverageValues = [
    currentCoverage?.line,
    currentCoverage?.branch,
    currentCoverage?.method
  ].filter((v): v is number => v !== undefined);
  
  const overallCoverage = coverageValues.length > 0
    ? coverageValues.reduce((a, b) => a + b, 0) / coverageValues.length
    : 0;

  // Donut chart data
  const donutData = [
    { name: 'Covered', value: overallCoverage },
    { name: 'Uncovered', value: 100 - overallCoverage },
  ];

  return (
    <div className="coverage-widget">
      {/* Overview Section */}
      <div className="coverage-widget__overview">
        <div className="coverage-widget__chart">
          <ResponsiveContainer width="100%" height={120}>
            <PieChart>
              <Pie
                data={donutData}
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={50}
                paddingAngle={2}
                dataKey="value"
                startAngle={90}
                endAngle={-270}
              >
                {donutData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={index === 0 ? '#6366f1' : '#e5e7eb'}
                    stroke="none"
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="coverage-widget__chart-label">
            <span className="coverage-widget__chart-value">
              {overallCoverage.toFixed(0)}%
            </span>
            <span className="coverage-widget__chart-text">Overall</span>
          </div>
        </div>

        <div className="coverage-widget__summary">
          <div className="coverage-widget__summary-title">Coverage Summary</div>
          <div className="coverage-widget__summary-items">
            {currentCoverage?.line !== undefined && (
              <div className="coverage-widget__summary-item">
                <span className="coverage-widget__summary-label">Line</span>
                <span className="coverage-widget__summary-value">
                  {currentCoverage.line.toFixed(1)}%
                </span>
              </div>
            )}
            {currentCoverage?.branch !== undefined && (
              <div className="coverage-widget__summary-item">
                <span className="coverage-widget__summary-label">Branch</span>
                <span className="coverage-widget__summary-value">
                  {currentCoverage.branch.toFixed(1)}%
                </span>
              </div>
            )}
            {currentCoverage?.method !== undefined && (
              <div className="coverage-widget__summary-item">
                <span className="coverage-widget__summary-label">Method</span>
                <span className="coverage-widget__summary-value">
                  {currentCoverage.method.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="coverage-widget__details">
        <CoverageItem
          label="Line Coverage"
          current={currentCoverage?.line}
          target={targetCoverage?.line}
        />
        <CoverageItem
          label="Branch Coverage"
          current={currentCoverage?.branch}
          target={targetCoverage?.branch}
        />
        <CoverageItem
          label="Method Coverage"
          current={currentCoverage?.method}
          target={targetCoverage?.method}
        />
      </div>
    </div>
  );
};

export default CoverageWidget;
