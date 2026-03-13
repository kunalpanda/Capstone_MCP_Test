// src/components/Layout/Layout.tsx
// Main layout wrapper component

import React, { useState, useCallback } from 'react';
import { Sidebar, ViewMode } from './Sidebar';
import { Header } from './Header';
import { OrchestratorState } from '../../services/types';
import { Theme } from '../../hooks/useTheme';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
  state: OrchestratorState;
  isConnected: boolean;
  theme: Theme;
  onThemeToggle: () => void;
  activeView: ViewMode;
  onViewChange: (view: ViewMode) => void;
  onViewPR?: () => void;
  onEditConfig: () => void;
}

const SIDEBAR_COLLAPSED_KEY = 'orchestrator-sidebar-collapsed';

export const Layout: React.FC<LayoutProps> = ({
  children,
  state,
  isConnected,
  theme,
  onThemeToggle,
  activeView,
  onViewChange,
  onViewPR,
  onEditConfig
}) => {
  // Initialize collapsed state from localStorage
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    return stored === 'true';
  });

  const handleToggleSidebar = useCallback(() => {
    setIsSidebarCollapsed(prev => {
      const newValue = !prev;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(newValue));
      return newValue;
    });
  }, []);

  const hasActivePR = state.prSummary !== null;

  return (
    <div className="layout">
      {/* Sidebar Navigation */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
        activeView={activeView}
        onViewChange={onViewChange}
        hasActivePR={hasActivePR}
        onViewPR={onViewPR}
      />

      {/* Main Content Area */}
      <div className="layout__main">
        {/* Header */}
        <Header
          state={state}
          isConnected={isConnected}
          theme={theme}
          onThemeToggle={onThemeToggle}
          onEditConfig={onEditConfig}
        />

        {/* Content */}
        <main className="layout__content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
