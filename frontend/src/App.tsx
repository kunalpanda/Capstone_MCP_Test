// src/App.tsx
import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useOrchestratorState } from './hooks/useOrchestratorState';
import { useTheme } from './hooks/useTheme';
import { Layout } from './components/Layout';
import { DashboardView, TableView, LogsView } from './components/Views';
import { PRSummaryModal } from './components/PRSummaryModal/PRSummaryModal';
import { ConfigSetupPage, ConfigModal } from './components/Config';
import type { ViewMode } from './components/Layout/Sidebar';

const WEBHOOK_URL = 'https://webhook-handler-389127668230.us-central1.run.app';

function App() {
  const { isConnected, events } = useWebSocket();
  const state = useOrchestratorState(events);
  const { theme, toggleTheme } = useTheme();

  // null = checking, false = not configured, true = configured
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  useEffect(() => {
    fetch(`${WEBHOOK_URL}/config/status`)
      .then(res => res.json())
      .then(data => setIsConfigured(data.configured === true))
      .catch(() => setIsConfigured(false));
  }, []);

  const [activeView, setActiveView] = useState<ViewMode>('dashboard');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const hasShownModal = useRef(false);
  const [workflowStartTime, setWorkflowStartTime] = useState<number | null>(null);

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('📊 Total events received:', events.length);
      if (events.length > 0) {
        const latestEvent = events[events.length - 1];
        console.log('📨 Latest event:', latestEvent.type, latestEvent.data);
      }
    }
  }, [events]);

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

  useEffect(() => {
    if (state.status === 'complete' && state.prSummary && !hasShownModal.current) {
      setIsModalOpen(true);
      hasShownModal.current = true;
    }
  }, [state.status, state.prSummary]);

  useEffect(() => {
    if (state.status === 'running' && state.currentIteration === 1) {
      hasShownModal.current = false;
      setWorkflowStartTime(Date.now());
    }
  }, [state.status, state.currentIteration]);

  const handleViewPR = () => {
    if (state.prSummary) setIsModalOpen(true);
  };

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardView state={state} events={events} workflowStartTime={workflowStartTime} />;
      case 'table':
        return <TableView events={events} />;
      case 'logs':
        return <LogsView events={events} />;
      default:
        return <DashboardView state={state} events={events} workflowStartTime={workflowStartTime} />;
    }
  };

  // Loading spinner
  if (isConfigured === null) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: 'var(--bg-primary)',
        color: 'var(--text-muted)', fontSize: '0.875rem', gap: '0.75rem'
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ animation: 'spin 0.7s linear infinite' }}>
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        Connecting…
      </div>
    );
  }

  // First-time setup
  if (!isConfigured) {
    return <ConfigSetupPage onConfigured={() => setIsConfigured(true)} />;
  }

  // Normal dashboard
  return (
    <>
      <Layout
        state={state}
        isConnected={isConnected}
        theme={theme}
        onThemeToggle={toggleTheme}
        activeView={activeView}
        onViewChange={setActiveView}
        onViewPR={handleViewPR}
        onEditConfig={() => setIsConfigModalOpen(true)}
      >
        {renderView()}
      </Layout>

      {state.prSummary && (
        <PRSummaryModal
          prSummary={state.prSummary}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        />
      )}

      <ConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
      />
    </>
  );
}

export default App;