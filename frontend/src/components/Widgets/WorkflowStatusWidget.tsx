// src/components/Widgets/WorkflowStatusWidget.tsx
// Displays workflow status, interaction gauge (depleting), and elapsed time

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
  workflowStartTime: number | null;
}

/**
 * SVG gauge component showing remaining interactions.
 * Starts at 100% (all interactions available) and depletes as interactions are consumed.
 * Color shifts: green (>50% remaining), amber (≤50%), red (≤20%)
 */
const InteractionGauge: React.FC<{ current: number; max: number }> = ({ current, max }) => {
  const size = 130;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const remaining = Math.max(max - current, 0);
  const remainingPercent = max > 0 ? remaining / max : 1;
  const strokeDashoffset = circumference * (1 - remainingPercent);

  const getGaugeColor = () => {
    if (remainingPercent > 0.5) return 'var(--color-success-500)';
    if (remainingPercent > 0.2) return 'var(--color-warning-500)';
    return 'var(--color-error-500)';
  };

  const getTrackColor = () => {
    if (remainingPercent > 0.5) return 'var(--bg-tertiary)';
    if (remainingPercent > 0.2) return 'rgba(245, 158, 11, 0.1)';
    return 'rgba(239, 68, 68, 0.1)';
  };

  const gaugeColor = getGaugeColor();

  return (
    <div className="interaction-gauge">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="interaction-gauge__svg"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getTrackColor()}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={gaugeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="interaction-gauge__fill"
        />
      </svg>

      <div className="interaction-gauge__label">
        <span className="interaction-gauge__value" style={{ color: gaugeColor }}>
          {remaining}
        </span>
        <span className="interaction-gauge__subtext">
          of {max} remaining
        </span>
      </div>
    </div>
  );
};

export const WorkflowStatusWidget: React.FC<WorkflowStatusWidgetProps> = ({
  state,
  workflowStartTime
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Calculate elapsed time from start time
  useEffect(() => {
    if (!workflowStartTime) {
      setElapsedSeconds(0);
      return;
    }

    const calculateElapsed = () => {
      return Math.floor((Date.now() - workflowStartTime) / 1000);
    };

    setElapsedSeconds(calculateElapsed());

    // Only keep ticking while running; freeze on complete/error
    if (state.status !== 'running') {
      return;
    }

    const interval = setInterval(() => {
      setElapsedSeconds(calculateElapsed());
    }, 1000);

    return () => clearInterval(interval);
  }, [workflowStartTime, state.status]);

  const formatTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hrs > 0) {
      return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

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
  const showTimer = workflowStartTime !== null && state.status !== 'idle';

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

      {/* Gauge + Timer side by side */}
      <div className="workflow-status__metrics-row">
        {/* Interaction Gauge */}
        <div className="workflow-status__section">
          <div className="workflow-status__metric workflow-status__metric--center">
            <div className="workflow-status__metric-header">
              <Activity size={16} />
              <span>Interaction Cap</span>
            </div>
            <InteractionGauge
              current={state.currentInteraction}
              max={state.maxInteractions}
            />
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
                {showTimer ? formatTime(elapsedSeconds) : '00:00'}
              </span>
              {state.status === 'running' && (
                <span className="workflow-status__timer-indicator" />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      {state.status !== 'idle' && (
        <div className="workflow-status__stats">
          <div className="workflow-status__stat">
            <span className="workflow-status__stat-value">
              {state.totalActions}
            </span>
            <span className="workflow-status__stat-label">Actions</span>
          </div>
          <div className="workflow-status__stat">
            <span className="workflow-status__stat-value">
              {state.currentInteraction}
            </span>
            <span className="workflow-status__stat-label">Interactions</span>
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
