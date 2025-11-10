import React from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useOrchestratorState } from './hooks/useOrchestratorState';
import { Header } from './components/Header';
import { OutputStream } from './components/OutputStream';
import { StatePanel } from './components/StatePanel';
import './App.css';

function App() {
  const { isConnected, events } = useWebSocket();
  const state = useOrchestratorState(events);
  
  return (
    <div className="dashboard">
      <Header state={state} isConnected={isConnected} />
      
      <div className="main-content">
        <OutputStream events={events} />
        <StatePanel state={state} />
      </div>
    </div>
  );
}

export default App;