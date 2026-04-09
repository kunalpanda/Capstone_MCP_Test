import React, { useEffect, useState, useRef } from 'react';
import {
  Wifi,
  WifiOff,
  Clock,
  GitBranch,
  Activity,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle,
  StopCircle,
  Settings
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
  onEditConfig: () => void;
  workflowStartTime: number | null;
}

export const Header: React.FC<HeaderProps> = ({
  state,
  isConnected,
  theme,
  onThemeToggle,
  onEditConfig,
  workflowStartTime
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [stopping, setStopping] = useState(false);
  const frozenTimeRef = useRef<number | null>(null);

  const handleEmergencyStop = async () => {
  if (!window.confirm(
    '🛑 EMERGENCY STOP\n\n' +
    'Are you sure you want to stop the current workflow?\n\n' +
    'This will:\n' +
    '• Halt the workflow at the next iteration\n' +
    '• Mark it as stopped in the system\n' +
    '• Cannot be undone\n\n' +
    'Continue?'
  )) {
    return;
  }

  setStopping(true);
  try {
    const response = await fetch(
      'https://webhook-handler-389127668230.us-central1.run.app/emergency-stop',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflowId: 'ALL',
          reason: 'User triggered emergency stop from dashboard'
        })
      }
    );
    const data = await response.json();
    if (data.status === 'stopped') {
      alert('✅ Emergency stop initiated!\n\nThe workflow will halt at the next iteration.');
    } else {
      alert('⚠️ Stop command sent but status unclear.\n\nCheck logs for details.');
    }
  } catch (error) {
    alert('❌ Failed to send stop command:\n\n' + error);
  } finally {
    setStopping(false);
  }
};

  // Timer — synchronized with WorkflowStatusWidget via shared workflowStartTime.
  // Uses the same frozen-ref pattern to prevent drift on tab switches.
  useEffect(() => {
    if (!workflowStartTime) {
      setElapsedTime(0);
      frozenTimeRef.current = null;
      return;
    }

    if (state.status === 'running') {
      frozenTimeRef.current = null;
    }

    if (state.status !== 'running' && frozenTimeRef.current === null) {
      frozenTimeRef.current = Math.floor((Date.now() - workflowStartTime) / 1000);
    }

    if (frozenTimeRef.current !== null) {
      setElapsedTime(frozenTimeRef.current);
      return;
    }

    const calculateElapsed = () => Math.floor((Date.now() - workflowStartTime) / 1000);
    setElapsedTime(calculateElapsed());

    const interval = setInterval(() => {
      setElapsedTime(calculateElapsed());
    }, 1000);

    return () => clearInterval(interval);
  }, [workflowStartTime, state.status]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  // Remaining interactions for header pill
  const remaining = Math.max(state.maxInteractions - state.currentInteraction, 0);
  const remainingPercent = state.maxInteractions > 0 ? remaining / state.maxInteractions : 1;

  const getRemainingColor = () => {
    if (remainingPercent > 0.5) return 'header__remaining--ok';
    if (remainingPercent > 0.2) return 'header__remaining--warn';
    return 'header__remaining--critical';
  };

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

        {/* Center section - Remaining interactions pill (large screens only) */}
        <div className="header__center">
          {state.status === 'running' && (
            <div className={`header__remaining ${getRemainingColor()}`}>
              <Activity size={14} />
              <span className="header__remaining-count">{remaining}</span>
              <span className="header__remaining-label">
                of {state.maxInteractions} remaining
              </span>
              <span className="header__remaining-dot" />
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

          {/* Emergency Stop — only visible while workflow is running */}
          {state.status === 'running' && (
            <button
              className={`header__emergency-stop ${stopping ? 'header__emergency-stop--stopping' : ''}`}
              onClick={handleEmergencyStop}
              disabled={stopping}
              title="Emergency stop — halts workflow at next iteration"
            >
              <StopCircle size={14} />
              <span>{stopping ? 'Stopping...' : 'Emergency Stop'}</span>
            </button>
          )}
          
          {/* Edit Config */}
          <button
            className="header__edit-config"
            onClick={onEditConfig}
            title="Edit configuration"
          >
            <Settings size={14} />
            <span>Edit Config</span>
          </button>

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
