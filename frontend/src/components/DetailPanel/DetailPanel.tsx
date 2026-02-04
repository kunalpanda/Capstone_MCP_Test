// src/components/DetailPanel/DetailPanel.tsx
// Tabbed detail panel for logs, test results, and file changes

import React, { useState, useMemo } from 'react';
import {
  Terminal,
  TestTube,
  FileCode,
  ChevronUp,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Info,
  AlertTriangle,
  Clock,
  Filter
} from 'lucide-react';
import { BaseEvent } from '../../services/types';
import './DetailPanel.css';

interface DetailPanelProps {
  events: BaseEvent[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

type TabId = 'logs' | 'tests' | 'files';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

type LogLevel = 'info' | 'warning' | 'error' | 'debug';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  source: string;
}

interface TestResult {
  name: string;
  status: 'passed' | 'failed' | 'skipped';
  duration?: number;
  error?: string;
}

interface FileChange {
  path: string;
  action: 'created' | 'modified' | 'deleted';
  timestamp: string;
}

export const DetailPanel: React.FC<DetailPanelProps> = ({
  events,
  isCollapsed,
  onToggleCollapse
}) => {
  const [activeTab, setActiveTab] = useState<TabId>('logs');
  const [logFilter, setLogFilter] = useState<LogLevel | 'all'>('all');

  // Extract logs from events
  const logs = useMemo((): LogEntry[] => {
    const logEntries: LogEntry[] = [];

    events.forEach(event => {
      // Add log events
      if (event.type === 'log') {
        logEntries.push({
          timestamp: event.timestamp,
          level: event.data.level || 'info',
          message: event.data.message,
          source: 'system'
        });
      }

      // Add error events as error logs
      if (event.type === 'error') {
        logEntries.push({
          timestamp: event.timestamp,
          level: 'error',
          message: `${event.data.error_type}: ${event.data.error_message}`,
          source: 'error'
        });
      }

      // Add tool results as logs
      if (event.type === 'tool_result') {
        logEntries.push({
          timestamp: event.timestamp,
          level: event.data.success ? 'info' : 'error',
          message: `Tool "${event.data.tool_name}" ${event.data.success ? 'succeeded' : 'failed'}${event.data.result_summary ? `: ${event.data.result_summary.substring(0, 100)}` : ''}`,
          source: 'tool'
        });
      }

      // Add Claude responses as info
      if (event.type === 'claude_response' && event.data.text_content) {
        logEntries.push({
          timestamp: event.timestamp,
          level: 'info',
          message: `Claude: ${event.data.text_content.substring(0, 150)}...`,
          source: 'claude'
        });
      }
    });

    // Sort chronologically (oldest first, newest at bottom)
    return logEntries.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [events]);

  // Extract test results from events (simulated from tool results)
  const testResults = useMemo((): TestResult[] => {
    const results: TestResult[] = [];

    events.forEach(event => {
      if (event.type === 'tool_result' && event.data.tool_name.toLowerCase().includes('test')) {
        // Parse test results from tool result summaries
        if (event.data.result_summary) {
          const passedMatch = event.data.result_summary.match(/(\d+)\s*(?:tests?)?\s*passed/i);
          const failedMatch = event.data.result_summary.match(/(\d+)\s*(?:tests?)?\s*failed/i);

          if (passedMatch) {
            const count = parseInt(passedMatch[1]);
            for (let i = 0; i < Math.min(count, 5); i++) {
              results.push({
                name: `Test Suite ${results.length + 1}`,
                status: 'passed',
                duration: Math.floor(Math.random() * 1000) + 100
              });
            }
          }

          if (failedMatch) {
            const count = parseInt(failedMatch[1]);
            for (let i = 0; i < Math.min(count, 5); i++) {
              results.push({
                name: `Test Suite ${results.length + 1}`,
                status: 'failed',
                duration: Math.floor(Math.random() * 1000) + 100,
                error: event.data.error_message || 'Assertion failed'
              });
            }
          }
        }
      }
    });

    return results;
  }, [events]);

  // Extract file changes from events
  const fileChanges = useMemo((): FileChange[] => {
    const changes: FileChange[] = [];

    events.forEach(event => {
      if (event.type === 'tool_call') {
        const toolName = event.data.tool_name.toLowerCase();
        const input = event.data.tool_input;

        if (toolName.includes('write') || toolName.includes('create')) {
          const path = input?.path || input?.file_path || input?.filename;
          if (path) {
            changes.push({
              path,
              action: toolName.includes('create') ? 'created' : 'modified',
              timestamp: event.timestamp
            });
          }
        }

        if (toolName.includes('delete') || toolName.includes('remove')) {
          const path = input?.path || input?.file_path || input?.filename;
          if (path) {
            changes.push({
              path,
              action: 'deleted',
              timestamp: event.timestamp
            });
          }
        }
      }
    });

    // Sort chronologically (oldest first, newest at bottom)
    return changes.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [events]);

  // Filter logs
  const filteredLogs = useMemo(() => {
    if (logFilter === 'all') return logs;
    return logs.filter(log => log.level === logFilter);
  }, [logs, logFilter]);

  // Count errors for badge
  const errorCount = logs.filter(l => l.level === 'error').length;

  const tabs: Tab[] = [
    { id: 'logs', label: 'Logs', icon: <Terminal size={16} />, badge: errorCount > 0 ? errorCount : undefined },
    { id: 'tests', label: 'Test Results', icon: <TestTube size={16} />, badge: testResults.length > 0 ? testResults.length : undefined },
    { id: 'files', label: 'File Changes', icon: <FileCode size={16} />, badge: fileChanges.length > 0 ? fileChanges.length : undefined },
  ];

  const formatTimestamp = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return '';
    }
  };

  const getLogIcon = (level: LogLevel) => {
    switch (level) {
      case 'error': return <XCircle size={14} />;
      case 'warning': return <AlertTriangle size={14} />;
      case 'info': return <Info size={14} />;
      case 'debug': return <Terminal size={14} />;
    }
  };

  const renderLogsTab = () => (
    <div className="detail-panel__logs">
      <div className="detail-panel__logs-toolbar">
        <div className="detail-panel__filter-group">
          <Filter size={14} />
          <select
            value={logFilter}
            onChange={(e) => setLogFilter(e.target.value as LogLevel | 'all')}
          >
            <option value="all">All Levels</option>
            <option value="error">Errors</option>
            <option value="warning">Warnings</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
        </div>
        <span className="detail-panel__logs-count">
          {filteredLogs.length} entries
        </span>
      </div>
      <div className="detail-panel__logs-list">
        {filteredLogs.length === 0 ? (
          <div className="detail-panel__empty">
            <Terminal size={24} />
            <span>No logs to display</span>
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} className={`detail-panel__log-entry detail-panel__log-entry--${log.level}`}>
              <span className="detail-panel__log-time">{formatTimestamp(log.timestamp)}</span>
              <span className={`detail-panel__log-level detail-panel__log-level--${log.level}`}>
                {getLogIcon(log.level)}
                {log.level.toUpperCase()}
              </span>
              <span className="detail-panel__log-source">[{log.source}]</span>
              <span className="detail-panel__log-message">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );

  const renderTestsTab = () => (
    <div className="detail-panel__tests">
      {testResults.length === 0 ? (
        <div className="detail-panel__empty">
          <TestTube size={24} />
          <span>No test results available</span>
          <span className="detail-panel__empty-hint">Test results will appear after builds complete</span>
        </div>
      ) : (
        <div className="detail-panel__tests-list">
          {testResults.map((test, index) => (
            <div key={index} className={`detail-panel__test-entry detail-panel__test-entry--${test.status}`}>
              <span className="detail-panel__test-icon">
                {test.status === 'passed' ? <CheckCircle2 size={16} /> : 
                 test.status === 'failed' ? <XCircle size={16} /> : 
                 <AlertCircle size={16} />}
              </span>
              <span className="detail-panel__test-name">{test.name}</span>
              {test.duration && (
                <span className="detail-panel__test-duration">
                  <Clock size={12} />
                  {test.duration}ms
                </span>
              )}
              {test.error && (
                <span className="detail-panel__test-error">{test.error}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderFilesTab = () => (
    <div className="detail-panel__files">
      {fileChanges.length === 0 ? (
        <div className="detail-panel__empty">
          <FileCode size={24} />
          <span>No file changes detected</span>
          <span className="detail-panel__empty-hint">File modifications will be tracked here</span>
        </div>
      ) : (
        <div className="detail-panel__files-list">
          {fileChanges.map((file, index) => (
            <div key={index} className={`detail-panel__file-entry detail-panel__file-entry--${file.action}`}>
              <span className={`detail-panel__file-action detail-panel__file-action--${file.action}`}>
                {file.action === 'created' ? '+' : file.action === 'deleted' ? '-' : '~'}
              </span>
              <span className="detail-panel__file-path">{file.path}</span>
              <span className="detail-panel__file-time">{formatTimestamp(file.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className={`detail-panel ${isCollapsed ? 'detail-panel--collapsed' : ''}`}>
      {/* Header */}
      <div className="detail-panel__header">
        <div className="detail-panel__tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`detail-panel__tab ${activeTab === tab.id ? 'detail-panel__tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span className={`detail-panel__tab-badge ${tab.id === 'logs' && errorCount > 0 ? 'detail-panel__tab-badge--error' : ''}`}>
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        <button
          className="detail-panel__collapse-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          {isCollapsed ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="detail-panel__content">
          {activeTab === 'logs' && renderLogsTab()}
          {activeTab === 'tests' && renderTestsTab()}
          {activeTab === 'files' && renderFilesTab()}
        </div>
      )}
    </div>
  );
};

export default DetailPanel;
