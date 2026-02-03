// src/App.tsx
// Main application with redesigned enterprise UI

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useOrchestratorState } from './hooks/useOrchestratorState';
import { useTheme } from './hooks/useTheme';
import { Layout } from './components/Layout';
import { DashboardView, TableView } from './components/Views';
import { PRSummaryModal } from './components/PRSummaryModal/PRSummaryModal';
import type { ViewMode } from './components/Layout/Sidebar';

function App() {
  const { isConnected, events } = useWebSocket();
  const state = useOrchestratorState(events);
  const { theme, toggleTheme } = useTheme();
  
  const [activeView, setActiveView] = useState<ViewMode>('dashboard');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const hasShownModal = useRef(false);
  
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

  // Reset modal flag when a new workflow starts
  useEffect(() => {
    if (state.status === 'running' && state.currentIteration === 1) {
      hasShownModal.current = false;
    }
  }, [state.status, state.currentIteration]);
  
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
        return <DashboardView state={state} events={events} />;
      case 'table':
        return <TableView events={events} />;
      case 'details':
        // Details view could show expanded PR info or selected event details
        // For now, redirect to dashboard
        return <DashboardView state={state} events={events} />;
      default:
        return <DashboardView state={state} events={events} />;
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
