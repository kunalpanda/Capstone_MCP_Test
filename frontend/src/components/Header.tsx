import React, { useEffect, useState } from 'react';
import { OrchestratorState } from '../services/types';

interface HeaderProps {
  state: OrchestratorState;
  isConnected: boolean;
  onViewPR?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ state, isConnected, onViewPR }) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  
  useEffect(() => {
    if (state.status !== 'running') return;
    
    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [state.status]);
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };
  
  const progressPercent = state.maxIterations > 0 
    ? (state.currentIteration / state.maxIterations) * 100 
    : 0;
  
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-title">
          🤖 Agentic AI Core - DevOps Automation Dashboard
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <div className={`status-indicator ${isConnected ? '' : 'error'}`}></div>
            <span>{state.status.toUpperCase()}</span>
          </div>
          <div className="stat-item">
            <span>Iteration: <strong>{state.currentIteration}/{state.maxIterations}</strong></span>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progressPercent}%` }}></div>
            </div>
          </div>
          <div className="stat-item">
            <span>⏱️ <strong>{formatTime(elapsedTime)}</strong></span>
          </div>
          {state.status === 'complete' && state.prSummary && (
            <button 
              className="view-pr-button"
              onClick={onViewPR}
            >
              📋 View PR Summary
            </button>
          )}
        </div>
      </div>
    </header>
  );
};