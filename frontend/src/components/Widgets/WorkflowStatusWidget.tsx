// src/components/Widgets/WorkflowStatusWidget.tsx
// Displays workflow status, iteration progress, and elapsed time

import React, { useEffect, useState } from 'react';
import {
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle
} from 'lucide-react';
import { OrchestratorState } from '../../services/types';
import './WorkflowStatusWidget.css';

interface WorkflowStatusWidgetProps {
  state: OrchestratorState;
}

export const WorkflowStatusWidget: React.FC<WorkflowStatusWidgetProps> = ({ state }) => {
  const [elapsedTime, setElapsedTime] = useState(0);

  // Timer for running workflows
  useEffect(() => {
    if (state.status !== 'running') {
      return;
    }

    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [state.status]);

  // Reset timer when workflow starts
  useEffect(() => {
    if (state.status === 'running' && state.currentIteration === 1) {
      setElapsedTime(0);
    }
  }, [state.status, state.currentIteration]);

  const formatTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hrs > 0) {
      return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const progressPercent = state.maxIterations > 0
    ? (state.currentIteration / state.maxIterations) * 100
    : 0;

  const getStatusConfig = () => {
    switch (state.status) {
      case 'idle':
        return {
          icon: <Circle size={20} />,
          label: 'Idle',
          description: 'Waiting for workflow to start',
          className: 'status--idle',
          color: 'var(--text-muted)'
        };
      case 'running':
        return {
          icon: <Loader2 size={20} className="animate-spin" />,
          label: 'Running',
          description: 'Workflow in progress',
          className: 'status--running',
          color: 'var(--color-primary-500)'
        };
      case 'complete':
        return {
          icon: <CheckCircle2 size={20} />,
          label: 'Complete',
          description: 'Workflow finished successfully',
          className: 'status--complete',
          color: 'var(--color-success-500)'
        };
      case 'error':
        return {
          icon: <XCircle size={20} />,
          label: 'Error',
          description: 'Workflow encountered an error',
          className: 'status--error',
          color: 'var(--color-error-500)'
        };
      default:
        return {
          icon: <Circle size={20} />,
          label: 'Unknown',
          description: 'Unknown status',
          className: 'status--idle',
          color: 'var(--text-muted)'
        };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <div className="workflow-status-widget">
      {/* Status Section */}
      <div className="workflow-status__section workflow-status__main">
        <div className={`workflow-status__indicator ${statusConfig.className}`}>
          {statusConfig.icon}
        </div>
        <div className="workflow-status__info">
          <span className="workflow-status__label">{statusConfig.label}</span>
          <span className="workflow-status__description">{statusConfig.description}</span>
        </div>
      </div>

      {/* Progress Section */}
      <div className="workflow-status__section">
        <div className="workflow-status__metric">
          <div className="workflow-status__metric-header">
            <Activity size={16} />
            <span>Iteration Progress</span>
          </div>
          <div className="workflow-status__progress">
            <div className="workflow-status__progress-info">
              <span className="workflow-status__progress-current">
                {state.currentIteration}
              </span>
              <span className="workflow-status__progress-separator">/</span>
              <span className="workflow-status__progress-max">
                {state.maxIterations}
              </span>
            </div>
            <div className="workflow-status__progress-bar">
              <div
                className="workflow-status__progress-fill"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="workflow-status__progress-percent">
              {progressPercent.toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Timer Section */}
      <div className="workflow-status__section">
        <div className="workflow-status__metric">
          <div className="workflow-status__metric-header">
            <Clock size={16} />
            <span>Elapsed Time</span>
          </div>
          <div className="workflow-status__timer">
            <span className="workflow-status__timer-value">
              {formatTime(elapsedTime)}
            </span>
            {state.status === 'running' && (
              <span className="workflow-status__timer-indicator" />
            )}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      {state.status !== 'idle' && (
        <div className="workflow-status__stats">
          <div className="workflow-status__stat">
            <span className="workflow-status__stat-value">
              {state.recentActions.length}
            </span>
            <span className="workflow-status__stat-label">Actions</span>
          </div>
          <div className="workflow-status__stat">
            <span className="workflow-status__stat-value">
              {state.currentIteration}
            </span>
            <span className="workflow-status__stat-label">Iterations</span>
          </div>
          <div className="workflow-status__stat">
            <span className="workflow-status__stat-value">
              {state.prSummary ? '1' : '0'}
            </span>
            <span className="workflow-status__stat-label">PRs</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowStatusWidget;
