// src/components/Layout/Header.tsx
// Professional header with status indicators, progress, and controls

import React, { useEffect, useState } from 'react';
import {
  Wifi,
  WifiOff,
  Clock,
  GitBranch,
  Activity,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle
} from 'lucide-react';
import { OrchestratorState } from '../../services/types';
import { ThemeToggle } from '../ThemeToggle/ThemeToggle';
import { Theme } from '../../hooks/useTheme';
import './Header.css';

interface HeaderProps {
  state: OrchestratorState;
  isConnected: boolean;
  theme: Theme;
  onThemeToggle: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  state,
  isConnected,
  theme,
  onThemeToggle
}) => {
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
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const progressPercent = state.maxIterations > 0
    ? (state.currentIteration / state.maxIterations) * 100
    : 0;

  const getStatusConfig = () => {
    switch (state.status) {
      case 'idle':
        return {
          icon: <Circle size={14} />,
          label: 'Idle',
          className: 'status--idle'
        };
      case 'running':
        return {
          icon: <Loader2 size={14} className="animate-spin" />,
          label: 'Running',
          className: 'status--running'
        };
      case 'complete':
        return {
          icon: <CheckCircle2 size={14} />,
          label: 'Complete',
          className: 'status--complete'
        };
      case 'error':
        return {
          icon: <XCircle size={14} />,
          label: 'Error',
          className: 'status--error'
        };
      default:
        return {
          icon: <Circle size={14} />,
          label: 'Unknown',
          className: 'status--idle'
        };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <header className="header">
      <div className="header__content">
        {/* Left section - Status and Workflow info */}
        <div className="header__left">
          {/* Connection Status */}
          <div className={`header__connection ${isConnected ? 'header__connection--connected' : 'header__connection--disconnected'}`}>
            {isConnected ? (
              <Wifi size={16} />
            ) : (
              <WifiOff size={16} />
            )}
            <span className="header__connection-text">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Divider */}
          <div className="header__divider" />

          {/* Workflow Status */}
          <div className={`header__status ${statusConfig.className}`}>
            {statusConfig.icon}
            <span>{statusConfig.label}</span>
          </div>

          {/* Repository info */}
          {state.repo && (
            <>
              <div className="header__divider" />
              <div className="header__repo">
                <GitBranch size={14} />
                <span className="header__repo-name">{state.repo}</span>
                {state.branch && (
                  <span className="header__branch-badge">{state.branch}</span>
                )}
              </div>
            </>
          )}
        </div>

        {/* Center section - Progress */}
        <div className="header__center">
          {state.status === 'running' && (
            <div className="header__progress-container">
              <div className="header__progress-info">
                <Activity size={14} />
                <span>Iteration</span>
                <span className="header__progress-count">
                  {state.currentIteration} / {state.maxIterations}
                </span>
              </div>
              <div className="header__progress-bar">
                <div
                  className="header__progress-fill"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <span className="header__progress-percent">
                {progressPercent.toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {/* Right section - Timer and Theme */}
        <div className="header__right">
          {/* Elapsed Time */}
          {state.status === 'running' && (
            <div className="header__timer">
              <Clock size={14} />
              <span className="header__timer-value">{formatTime(elapsedTime)}</span>
            </div>
          )}

          {/* Theme Toggle */}
          <ThemeToggle
            theme={theme}
            onToggle={onThemeToggle}
            size="sm"
          />
        </div>
      </div>
    </header>
  );
};

export default Header;
