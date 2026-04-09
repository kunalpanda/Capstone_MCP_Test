import React from 'react';
import {
  LayoutDashboard,
  GitPullRequest,
  ChevronLeft,
  ChevronRight,
  Bot,
  Table,
  Terminal
} from 'lucide-react';
import './Sidebar.css';

export type ViewMode = 'dashboard' | 'table' | 'logs';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  activeView: ViewMode;
  onViewChange: (view: ViewMode) => void;
  hasActivePR: boolean;
  onViewPR?: () => void;
}

interface NavItem {
  id: ViewMode | 'pr';
  label: string;
  icon: React.ReactNode;
  onClick?: () => void;
  badge?: string | number;
  disabled?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  activeView,
  onViewChange,
  hasActivePR,
  onViewPR
}) => {
  const navItems: NavItem[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <LayoutDashboard size={20} />
    },
    {
      id: 'table',
      label: 'Event Table',
      icon: <Table size={20} />
    },
    {
      id: 'logs',
      label: 'Logs & Results',
      icon: <Terminal size={20} />
    }
  ];

  const actionItems: NavItem[] = [
    {
      id: 'pr',
      label: 'View PR',
      icon: <GitPullRequest size={20} />,
      onClick: onViewPR,
      disabled: !hasActivePR,
      badge: hasActivePR ? '1' : undefined
    }
  ];

  const handleNavClick = (item: NavItem) => {
    if (item.onClick) {
      item.onClick();
    } else if (item.id !== 'pr') {
      onViewChange(item.id as ViewMode);
    }
  };

  return (
    <aside className={`sidebar ${isCollapsed ? 'sidebar--collapsed' : ''}`}>
      {/* Logo / Brand */}
      <div className="sidebar__header">
        <div className="sidebar__brand">
          <div className="sidebar__logo">
            <Bot size={24} />
          </div>
          {!isCollapsed && (
            <div className="sidebar__brand-text">
              <span className="sidebar__brand-name">AI Core</span>
              <span className="sidebar__brand-tagline">DevOps Automation</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar__nav">
        <div className="sidebar__nav-section">
          {!isCollapsed && <div className="sidebar__nav-label">Navigation</div>}
          <ul className="sidebar__nav-list">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  className={`sidebar__nav-item ${activeView === item.id ? 'sidebar__nav-item--active' : ''}`}
                  onClick={() => handleNavClick(item)}
                  title={isCollapsed ? item.label : undefined}
                  disabled={item.disabled}
                >
                  <span className="sidebar__nav-icon">{item.icon}</span>
                  {!isCollapsed && (
                    <span className="sidebar__nav-text">{item.label}</span>
                  )}
                  {item.badge && !isCollapsed && (
                    <span className="sidebar__nav-badge">{item.badge}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="sidebar__nav-section">
          {!isCollapsed && <div className="sidebar__nav-label">Actions</div>}
          <ul className="sidebar__nav-list">
            {actionItems.map((item) => (
              <li key={item.id}>
                <button
                  className={`sidebar__nav-item ${item.disabled ? 'sidebar__nav-item--disabled' : ''}`}
                  onClick={() => handleNavClick(item)}
                  title={isCollapsed ? item.label : undefined}
                  disabled={item.disabled}
                >
                  <span className="sidebar__nav-icon">{item.icon}</span>
                  {!isCollapsed && (
                    <span className="sidebar__nav-text">{item.label}</span>
                  )}
                  {item.badge && !isCollapsed && (
                    <span className="sidebar__nav-badge sidebar__nav-badge--accent">
                      {item.badge}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* Footer with collapse toggle */}
      <div className="sidebar__footer">
        <button
          className="sidebar__collapse-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!isCollapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
