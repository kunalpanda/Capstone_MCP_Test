// src/App.tsx
// Main application with redesigned enterprise UI

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useOrchestratorState } from './hooks/useOrchestratorState';
import { useTheme } from './hooks/useTheme';
import { Layout } from './components/Layout';
import { DashboardView, TableView, LogsView } from './components/Views';
import { PRSummaryModal } from './components/PRSummaryModal/PRSummaryModal';
import type { ViewMode } from './components/Layout/Sidebar';

function App() {
  const { isConnected, events } = useWebSocket();
  const state = useOrchestratorState(events);
  const { theme, toggleTheme } = useTheme();

  const [activeView, setActiveView] = useState<ViewMode>('dashboard');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const hasShownModal = useRef(false);

  const [workflowStartTime, setWorkflowStartTime] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Debug: Log all events (keep for development)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('📊 Total events received:', events.length);
      if (events.length > 0) {
        const latestEvent = events[events.length - 1];
        console.log('📨 Latest event:', latestEvent.type, latestEvent.data);
      }
    }
  }, [events]);

  // Debug: Log state changes (keep for development)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔄 State update:', {
        status: state.status,
        hasPrSummary: !!state.prSummary,
        prNumber: state.prSummary?.pr_number,
        isModalOpen,
        hasShownModal: hasShownModal.current
      });
    }
  }, [state.status, state.prSummary, isModalOpen]);

  // Auto-open modal when workflow completes with PR summary
  useEffect(() => {
    if (state.status === 'complete' && state.prSummary && !hasShownModal.current) {
      setIsModalOpen(true);
      hasShownModal.current = true;
    }
  }, [state.status, state.prSummary]);

  // Detect the start of a new workflow
  useEffect(() => {
    if (state.status === 'running' && state.currentInteraction === 1) {
      hasShownModal.current = false;
      setWorkflowStartTime(Date.now());
      setElapsedSeconds(0);
    }
  }, [state.status, state.currentInteraction]);

  // Clear timer when workflow returns to idle
  useEffect(() => {
    if (state.status === 'idle') {
      setWorkflowStartTime(null);
      setElapsedSeconds(0);
    }
  }, [state.status]);

  // Shared elapsed timer for header + widget
  // It only ticks while running and stays frozen on complete/error
  useEffect(() => {
    if (!workflowStartTime || state.status !== 'running') {
      return;
    }

    const updateElapsed = () => {
      setElapsedSeconds(Math.floor((Date.now() - workflowStartTime) / 1000));
    };

    updateElapsed();

    const interval = window.setInterval(updateElapsed, 1000);

    return () => window.clearInterval(interval);
  }, [workflowStartTime, state.status]);

  const handleViewPR = () => {
    if (state.prSummary) {
      setIsModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleViewChange = (view: ViewMode) => {
    setActiveView(view);
  };

  // Render the active view
  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return (
          <DashboardView
            state={state}
            events={events}
            workflowStartTime={workflowStartTime}
            elapsedSeconds={elapsedSeconds}
          />
        );
      case 'table':
        return <TableView events={events} />;
      case 'logs':
        return <LogsView events={events} />;
      default:
        return (
          <DashboardView
            state={state}
            events={events}
            workflowStartTime={workflowStartTime}
            elapsedSeconds={elapsedSeconds}
          />
        );
    }
  };

  return (
    <>
      <Layout
        state={state}
        isConnected={isConnected}
        theme={theme}
        onThemeToggle={toggleTheme}
        activeView={activeView}
        onViewChange={handleViewChange}
        onViewPR={handleViewPR}
        workflowStartTime={workflowStartTime}
        elapsedSeconds={elapsedSeconds}
      >
        {renderView()}
      </Layout>

      {state.prSummary && (
        <PRSummaryModal
          prSummary={state.prSummary}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
        />
      )}
    </>
  );
}

export default App;