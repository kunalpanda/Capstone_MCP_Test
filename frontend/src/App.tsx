import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useOrchestratorState } from './hooks/useOrchestratorState';
import { Header } from './components/Header';
import { OutputStream } from './components/OutputStream';
import { StatePanel } from './components/StatePanel';
import { PRSummaryModal } from './components/PRSummaryModal';
import './App.css';

function App() {
  const { isConnected, events } = useWebSocket();
  const state = useOrchestratorState(events);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const hasShownModal = useRef(false);
  
  // Debug: Log all events
  useEffect(() => {
    console.log('📊 Total events received:', events.length);
    if (events.length > 0) {
      const latestEvent = events[events.length - 1];
      console.log('📨 Latest event:', latestEvent.type, latestEvent.data);
    }
  }, [events]);
  
  // Debug: Log state changes
  useEffect(() => {
    console.log('🔄 State update:', {
      status: state.status,
      hasPrSummary: !!state.prSummary,
      prNumber: state.prSummary?.pr_number,
      isModalOpen,
      hasShownModal: hasShownModal.current
    });
  }, [state.status, state.prSummary, isModalOpen]);
  
  // Auto-open modal when workflow completes with PR summary
  useEffect(() => {
    console.log('🎯 Modal effect check:', {
      status: state.status,
      hasPrSummary: !!state.prSummary,
      hasShownModal: hasShownModal.current
    });
    
    if (state.status === 'complete' && state.prSummary && !hasShownModal.current) {
      console.log('✅ Opening modal!');
      setIsModalOpen(true);
      hasShownModal.current = true;
    }
  }, [state.status, state.prSummary]);
  
  const handleViewPR = () => {
    console.log('👆 View PR button clicked');
    setIsModalOpen(true);
  };
  
  const handleCloseModal = () => {
    console.log('❌ Closing modal');
    setIsModalOpen(false);
  };
  
  return (
    <div className="dashboard">
      <Header 
        state={state} 
        isConnected={isConnected}
        onViewPR={handleViewPR}
      />
      
      <div className="main-content">
        <OutputStream events={events} />
        <StatePanel state={state} />
      </div>

      <PRSummaryModal 
        summary={state.prSummary}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </div>
  );
}

export default App;
