// src/index.tsx
// Entry point for React application

import React from 'react';
import ReactDOM from 'react-dom/client';
import { initializeTheme } from './hooks/useTheme';

// Import styles in correct order
import './styles/variables.css';
import './styles/globals.css';
import './index.css';

import App from './App';

// Initialize theme before render to prevent flash
initializeTheme();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
