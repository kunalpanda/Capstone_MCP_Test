import React from 'react';
import { OrchestratorState } from '../services/types';
import { MetricCard } from './shared/MetricCard';

interface StatePanelProps {
  state: OrchestratorState;
}

export const StatePanel: React.FC<StatePanelProps> = ({ state }) => {
  return (
    <div className="column">
      <div className="column-header">📊 Current State</div>
      <div className="column-content">
        
        {/* Repository Info */}
        <div className="state-section">
          <div className="state-section-title">🗂️ Repository</div>
          <div className="state-item">
            <span className="state-label">Repository:</span>
            <span className="state-value">{state.repo || 'N/A'}</span>
          </div>
          <div className="state-item">
            <span className="state-label">Branch:</span>
            <span className="state-value">{state.branch || 'N/A'}</span>
          </div>
        </div>
        
        {/* Test Metrics */}
        <div className="state-section">
          <div className="state-section-title">🧪 Test Metrics</div>
          <div className="metrics-grid">
            <MetricCard label="Total" value={state.testMetrics.total} />
            <MetricCard label="Passing" value={state.testMetrics.passing} type="success" />
            <MetricCard label="Failing" value={state.testMetrics.failing} type="error" />
            <MetricCard label="Skipped" value={state.testMetrics.skipped} />
          </div>
        </div>
        
        {/* Build Info */}
        {state.buildInfo.number && (
          <div className="state-section">
            <div className="state-section-title">🏗️ Build Info</div>
            <div className="state-item">
              <span className="state-label">Build Number:</span>
              <span className="state-value">#{state.buildInfo.number}</span>
            </div>
            <div className="state-item">
              <span className="state-label">Status:</span>
              <span className={`state-value ${state.buildInfo.status?.toLowerCase()}`}>
                {state.buildInfo.status}
              </span>
            </div>
          </div>
        )}
        
        {/* Recent Actions */}
        <div className="state-section">
          <div className="state-section-title">📝 Recent Actions</div>
          {state.recentActions.map((action, index) => (
            <div key={index} className="action-item">
              <span className="action-icon">🔧</span>
              <span className="action-text">{action}</span>
            </div>
          ))}
        </div>
        
      </div>
    </div>
  );
};