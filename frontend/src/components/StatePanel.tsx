import React from 'react';
import { OrchestratorState } from '../services/types';
import { MetricCard } from './shared/MetricCard';

interface StatePanelProps {
  state: OrchestratorState;
}

export const StatePanel: React.FC<StatePanelProps> = ({ state }) => {
  // Calculate coverage progress percentage
  const getCoverageProgress = (current?: number, target?: number): number => {
    if (!current || !target) return 0;
    return Math.min((current / target) * 100, 100);
  };

  // Format coverage display with status indicator
  const formatCoverage = (current?: number, target?: number): string => {
    if (current === undefined) return 'N/A';
    if (target === undefined) return `${current.toFixed(1)}%`;
    
    const status = current >= target ? '✅' : '⚠️';
    const gap = target - current;
    return `${status} ${current.toFixed(1)}% / ${target}% (${gap > 0 ? '-' : '+'}${Math.abs(gap).toFixed(1)}%)`;
  };

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

        {/* Test Coverage Metrics */}
        {(state.currentCoverage || state.targetCoverage) && (
          <div className="state-section">
            <div className="state-section-title">📈 Test Coverage</div>
            
            {/* Line Coverage */}
            <div className="state-item">
              <span className="state-label">Line:</span>
              <span className="state-value">
                {formatCoverage(
                  state.currentCoverage?.line,
                  state.targetCoverage?.line
                )}
              </span>
            </div>
            {state.currentCoverage?.line && state.targetCoverage?.line && (
              <div className="coverage-bar">
                <div 
                  className="coverage-progress"
                  style={{
                    width: `${getCoverageProgress(
                      state.currentCoverage.line,
                      state.targetCoverage.line
                    )}%`,
                    backgroundColor: state.currentCoverage.line >= state.targetCoverage.line 
                      ? '#4caf50' 
                      : '#ff9800'
                  }}
                />
              </div>
            )}

            {/* Branch Coverage */}
            <div className="state-item">
              <span className="state-label">Branch:</span>
              <span className="state-value">
                {formatCoverage(
                  state.currentCoverage?.branch,
                  state.targetCoverage?.branch
                )}
              </span>
            </div>
            {state.currentCoverage?.branch && state.targetCoverage?.branch && (
              <div className="coverage-bar">
                <div 
                  className="coverage-progress"
                  style={{
                    width: `${getCoverageProgress(
                      state.currentCoverage.branch,
                      state.targetCoverage.branch
                    )}%`,
                    backgroundColor: state.currentCoverage.branch >= state.targetCoverage.branch 
                      ? '#4caf50' 
                      : '#ff9800'
                  }}
                />
              </div>
            )}

            {/* Method Coverage */}
            <div className="state-item">
              <span className="state-label">Method:</span>
              <span className="state-value">
                {formatCoverage(
                  state.currentCoverage?.method,
                  state.targetCoverage?.method
                )}
              </span>
            </div>
            {state.currentCoverage?.method && state.targetCoverage?.method && (
              <div className="coverage-bar">
                <div 
                  className="coverage-progress"
                  style={{
                    width: `${getCoverageProgress(
                      state.currentCoverage.method,
                      state.targetCoverage.method
                    )}%`,
                    backgroundColor: state.currentCoverage.method >= state.targetCoverage.method 
                      ? '#4caf50' 
                      : '#ff9800'
                  }}
                />
              </div>
            )}
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