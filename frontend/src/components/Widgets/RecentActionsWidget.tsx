import React from 'react';
import {
  Wrench,
  ChevronRight,
  Inbox,
  GitCommit,
  FileCode,
  Search,
  TestTube,
  GitPullRequest,
  FolderOpen,
  Terminal
} from 'lucide-react';
import './RecentActionsWidget.css';

interface RecentActionsWidgetProps {
  actions: string[];
  totalActions: number;
}

// Map tool names to icons
const getToolIcon = (action: string): React.ReactNode => {
  const actionLower = action.toLowerCase();
  
  if (actionLower.includes('commit') || actionLower.includes('push')) {
    return <GitCommit size={16} />;
  }
  if (actionLower.includes('file') || actionLower.includes('read') || actionLower.includes('write')) {
    return <FileCode size={16} />;
  }
  if (actionLower.includes('search') || actionLower.includes('find')) {
    return <Search size={16} />;
  }
  if (actionLower.includes('test') || actionLower.includes('coverage')) {
    return <TestTube size={16} />;
  }
  if (actionLower.includes('pr') || actionLower.includes('pull')) {
    return <GitPullRequest size={16} />;
  }
  if (actionLower.includes('directory') || actionLower.includes('folder') || actionLower.includes('list')) {
    return <FolderOpen size={16} />;
  }
  if (actionLower.includes('run') || actionLower.includes('execute') || actionLower.includes('build')) {
    return <Terminal size={16} />;
  }
  
  return <Wrench size={16} />;
};

// Parse tool name from action string like "Called tool_name"
const parseToolName = (action: string): string => {
  const match = action.match(/Called\s+(\S+)/i);
  if (match) {
    return match[1].replace(/_/g, ' ');
  }
  return action;
};

export const RecentActionsWidget: React.FC<RecentActionsWidgetProps> = ({ actions, totalActions }) => {
  if (actions.length === 0) {
    return (
      <div className="recent-actions-widget recent-actions-widget--empty">
        <div className="recent-actions-widget__empty-state">
          <Inbox size={32} />
          <span className="recent-actions-widget__empty-title">No Actions Yet</span>
          <span className="recent-actions-widget__empty-text">
            Tool calls will appear here as they happen
          </span>
        </div>
      </div>
    );
  }

  // Reverse actions so oldest is at top, newest at bottom
  const displayActions = [...actions].reverse();

  return (
    <div className="recent-actions-widget">
      <div className="recent-actions-widget__list">
        {displayActions.map((action, index) => {
          const toolName = parseToolName(action);
          const icon = getToolIcon(action);
          const isLatest = index === displayActions.length - 1;
          
          return (
            <div
              key={index}
              className={`recent-actions-widget__item ${isLatest ? 'recent-actions-widget__item--latest' : ''}`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="recent-actions-widget__item-icon">
                {icon}
              </div>
              <div className="recent-actions-widget__item-content">
                <span className="recent-actions-widget__item-name">
                  {toolName}
                </span>
                {isLatest && (
                  <span className="recent-actions-widget__item-badge">Latest</span>
                )}
              </div>
              <ChevronRight size={14} className="recent-actions-widget__item-chevron" />
            </div>
          );
        })}
      </div>

      {/* Stats Footer */}
      <div className="recent-actions-widget__footer">
        <div className="recent-actions-widget__stat">
          <Wrench size={14} />
          <span>{totalActions} tool calls</span>
        </div>
      </div>
    </div>
  );
};

export default RecentActionsWidget;
