// src/components/Views/LogsView.tsx
// Dedicated view for logs, test results, and file changes

import React, { useState, useMemo } from 'react';
import {
  Terminal,
  TestTube,
  FileCode,
  XCircle,
  Info,
  AlertTriangle,
  Clock,
  Filter,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Wrench
} from 'lucide-react';
import { BaseEvent } from '../../services/types';
import './LogsView.css';

interface LogsViewProps {
  events: BaseEvent[];
}

type TabId = 'logs' | 'tests' | 'files';

type LogLevel = 'info' | 'warning' | 'error' | 'debug';

interface ExpandableData {
  type: 'claude_response' | 'tool_call' | 'tool_result';
  fullContent?: string;
  toolInput?: Record<string, unknown>;
  resultSummary?: string;
  errorMessage?: string;
}

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  source: string;
  expandable?: ExpandableData;
}

interface TestResult {
  name: string;
  className?: string;
  status: 'passed' | 'failed' | 'skipped';
  duration?: number;
  error?: string;
}

interface TestSummary {
  timestamp: string;
  buildNumber: string | number;
  totalCount: number;
  passCount: number;
  failCount: number;
  skipCount: number;
  duration?: number;
  failedTests: TestResult[];
}

interface FileChange {
  path: string;
  action: 'created' | 'modified' | 'deleted';
  timestamp: string;
}

export const LogsView: React.FC<LogsViewProps> = ({ events }) => {
  const [activeTab, setActiveTab] = useState<TabId>('logs');
  const [logFilter, setLogFilter] = useState<LogLevel | 'all'>('all');
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set());

  const toggleLogExpanded = (index: number) => {
    setExpandedLogs(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  // Extract logs from events
  const logs = useMemo((): LogEntry[] => {
    const logEntries: LogEntry[] = [];

    events.forEach(event => {
      switch (event.type) {
        case 'log':
          logEntries.push({
            timestamp: event.timestamp,
            level: event.data.level || 'info',
            message: event.data.message,
            source: 'system'
          });
          break;

        case 'error':
          logEntries.push({
            timestamp: event.timestamp,
            level: 'error',
            message: `${event.data.error_type}: ${event.data.error_message}`,
            source: 'error'
          });
          break;

        case 'workflow_start':
          logEntries.push({
            timestamp: event.timestamp,
            level: 'info',
            message: `Workflow started: ${event.data.repo_owner}/${event.data.repo_name} on ${event.data.branch}`,
            source: 'workflow'
          });
          break;

        case 'workflow_complete':
          logEntries.push({
            timestamp: event.timestamp,
            level: event.data.success ? 'info' : 'error',
            message: `Workflow ${event.data.success ? 'completed successfully' : 'failed'} after ${event.data.total_iterations} iterations`,
            source: 'workflow'
          });
          break;

        case 'iteration_start':
          logEntries.push({
            timestamp: event.timestamp,
            level: 'debug',
            message: `Iteration ${event.data.iteration} of ${event.data.max_iterations} started`,
            source: 'iteration'
          });
          break;

        case 'state_update':
          logEntries.push({
            timestamp: event.timestamp,
            level: 'debug',
            message: `State update: ${event.data.phase || JSON.stringify(event.data).substring(0, 100)}`,
            source: 'state'
          });
          break;

        case 'tool_call':
          logEntries.push({
            timestamp: event.timestamp,
            level: 'debug',
            message: `Calling tool: ${event.data.tool_name}${event.data.input_preview ? ` - ${event.data.input_preview.substring(0, 80)}` : ''}`,
            source: 'tool',
            expandable: event.data.tool_input && Object.keys(event.data.tool_input).length > 0 ? {
              type: 'tool_call',
              toolInput: event.data.tool_input
            } : undefined
          });
          break;

        case 'tool_result':
          logEntries.push({
            timestamp: event.timestamp,
            level: event.data.success ? 'info' : 'error',
            message: `Tool "${event.data.tool_name}" ${event.data.success ? 'succeeded' : 'failed'}${event.data.result_summary ? `: ${event.data.result_summary.substring(0, 100)}` : ''}`,
            source: 'tool',
            expandable: (event.data.result_summary?.length > 100 || event.data.error_message) ? {
              type: 'tool_result',
              resultSummary: event.data.result_summary,
              errorMessage: event.data.error_message
            } : undefined
          });
          break;

        case 'claude_response':
          if (event.data.text_content) {
            logEntries.push({
              timestamp: event.timestamp,
              level: 'info',
              message: `Claude: ${event.data.text_content.substring(0, 150)}${event.data.text_content.length > 150 ? '...' : ''}`,
              source: 'claude',
              expandable: event.data.text_content.length > 150 ? {
                type: 'claude_response',
                fullContent: event.data.text_content
              } : undefined
            });
          }
          break;

        case 'pr_summary':
          logEntries.push({
            timestamp: event.timestamp,
            level: 'info',
            message: `PR #${event.data.pr_number} created: ${event.data.title}`,
            source: 'pr'
          });
          break;
      }
    });

    // Sort chronologically (oldest first, newest at bottom)
    return logEntries.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [events]);

  // Extract test results from Jenkins get_test_results tool
  const testSummaries = useMemo((): TestSummary[] => {
    const summaries: TestSummary[] = [];

    events.forEach(event => {
      // Look for get_test_results tool results
      if (event.type === 'tool_result' && event.data.tool_name === 'get_test_results') {
        const resultStr: string = String(event.data.result_summary || '');
        
        // Parse the Python dict string format from result_summary
        // Format: {'job_name': '...', 'build_number': 19, 'total_count': 10, ...}
        const parseValue = (key: string): string | null => {
          // Match both 'key': value and "key": value formats
          const regex = new RegExp(`['"]${key}['"]:\s*([^,}]+)`);
          const match = resultStr.match(regex);
          if (match) {
            // Clean up the value (remove quotes, whitespace)
            return match[1].trim().replace(/^['"]|['"]$/g, '');
          }
          return null;
        };

        const totalCount = parseInt(parseValue('total_count') || '0');
        const passCount = parseInt(parseValue('pass_count') || '0');
        const failCount = parseInt(parseValue('fail_count') || '0');
        const skipCount = parseInt(parseValue('skip_count') || '0');
        const buildNumber = parseValue('build_number') || 'N/A';
        const duration = parseFloat(parseValue('duration') || '0');

        // Extract failed tests if present in the result
        const failedTests: TestResult[] = [];
        
        // Try to parse failed_tests array from the string
        // Format: 'failed_tests': [{'name': '...', 'class_name': '...', 'error_message': '...'}, ...]
        const failedTestsMatch = resultStr.match(/'failed_tests':\s*\[([^\]]*)]/);
        if (failedTestsMatch && failedTestsMatch[1].trim()) {
          // Simple extraction of test names and errors from the array string
          const testEntries = failedTestsMatch[1].split('},');
          testEntries.forEach(entry => {
            const nameMatch = entry.match(/'name':\s*['"]([^'"]+)['"]/);
            const classMatch = entry.match(/'class_name':\s*['"]([^'"]+)['"]/);
            const errorMatch = entry.match(/'error_message':\s*['"]([^'"]+)['"]/);
            const durationMatch = entry.match(/'duration':\s*([\d.]+)/);
            
            if (nameMatch) {
              failedTests.push({
                name: nameMatch[1],
                className: classMatch ? classMatch[1] : undefined,
                status: 'failed',
                duration: durationMatch ? Math.round(parseFloat(durationMatch[1]) * 1000) : undefined,
                error: errorMatch ? errorMatch[1] : 'Test failed'
              });
            }
          });
        }

        // Only add if we got valid data
        if (totalCount > 0 || passCount > 0 || failCount > 0) {
          summaries.push({
            timestamp: event.timestamp,
            buildNumber,
            totalCount,
            passCount,
            failCount,
            skipCount,
            duration: duration > 0 ? duration : undefined,
            failedTests
          });
        }
      }
    });

    // Sort by timestamp (newest first for test results)
    return summaries.sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [events]);

  // Get the latest test summary for badge count
  const latestTestSummary = testSummaries[0];

  // Extract file changes
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

    // Sort chronologically
    return changes.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [events]);

  // Filter logs
  const filteredLogs = useMemo(() => {
    if (logFilter === 'all') return logs;
    return logs.filter(log => log.level === logFilter);
  }, [logs, logFilter]);

  // Counts for badges
  const errorCount = logs.filter(l => l.level === 'error').length;

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

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'claude': return <MessageSquare size={14} />;
      case 'tool': return <Wrench size={14} />;
      default: return null;
    }
  };

  const renderExpandedContent = (expandable: ExpandableData) => {
    switch (expandable.type) {
      case 'claude_response':
        return (
          <div className="logs-view__expanded">
            <div className="logs-view__expanded-label">Full Response</div>
            <div className="logs-view__expanded-content">
              {expandable.fullContent}
            </div>
          </div>
        );

      case 'tool_call':
        return (
          <div className="logs-view__expanded">
            <div className="logs-view__expanded-label">Tool Input</div>
            <pre className="logs-view__expanded-code">
              {JSON.stringify(expandable.toolInput, null, 2)}
            </pre>
          </div>
        );

      case 'tool_result':
        return (
          <div className="logs-view__expanded">
            {expandable.resultSummary && (
              <>
                <div className="logs-view__expanded-label">Full Result</div>
                <div className="logs-view__expanded-content">
                  {expandable.resultSummary}
                </div>
              </>
            )}
            {expandable.errorMessage && (
              <>
                <div className="logs-view__expanded-label">Error Details</div>
                <div className="logs-view__expanded-error">
                  {expandable.errorMessage}
                </div>
              </>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="logs-view">
      {/* Tabs */}
      <div className="logs-view__header">
        <div className="logs-view__tabs">
          <button
            className={`logs-view__tab ${activeTab === 'logs' ? 'logs-view__tab--active' : ''}`}
            onClick={() => setActiveTab('logs')}
          >
            <Terminal size={18} />
            <span>Logs</span>
            {errorCount > 0 && (
              <span className="logs-view__tab-badge logs-view__tab-badge--error">{errorCount}</span>
            )}
          </button>
          <button
            className={`logs-view__tab ${activeTab === 'tests' ? 'logs-view__tab--active' : ''}`}
            onClick={() => setActiveTab('tests')}
          >
            <TestTube size={18} />
            <span>Test Results</span>
            {latestTestSummary && (
              <span className={`logs-view__tab-badge ${latestTestSummary.failCount > 0 ? 'logs-view__tab-badge--error' : ''}`}>
                {latestTestSummary.totalCount}
              </span>
            )}
          </button>
          <button
            className={`logs-view__tab ${activeTab === 'files' ? 'logs-view__tab--active' : ''}`}
            onClick={() => setActiveTab('files')}
          >
            <FileCode size={18} />
            <span>File Changes</span>
            {fileChanges.length > 0 && (
              <span className="logs-view__tab-badge">{fileChanges.length}</span>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="logs-view__content">
        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <div className="logs-view__logs">
            <div className="logs-view__toolbar">
              <div className="logs-view__filter-group">
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
              <span className="logs-view__count">{filteredLogs.length} entries</span>
            </div>
            <div className="logs-view__logs-list">
              {filteredLogs.length === 0 ? (
                <div className="logs-view__empty">
                  <Terminal size={32} />
                  <span>No logs to display</span>
                </div>
              ) : (
                filteredLogs.map((log, index) => {
                  const isExpanded = expandedLogs.has(index);
                  return (
                    <div key={index} className={`logs-view__log-entry logs-view__log-entry--${log.level} ${isExpanded ? 'logs-view__log-entry--expanded' : ''}`}>
                      <div className="logs-view__log-row">
                        <span className="logs-view__log-time">{formatTimestamp(log.timestamp)}</span>
                        <span className={`logs-view__log-level logs-view__log-level--${log.level}`}>
                          {getLogIcon(log.level)}
                          {log.level.toUpperCase()}
                        </span>
                        <span className="logs-view__log-source">
                          {getSourceIcon(log.source)}
                          [{log.source}]
                        </span>
                        <span className="logs-view__log-message">{log.message}</span>
                        {log.expandable && (
                          <button
                            className="logs-view__log-expand"
                            onClick={() => toggleLogExpanded(index)}
                            title={isExpanded ? 'Collapse' : 'Expand'}
                          >
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </button>
                        )}
                      </div>
                      {isExpanded && log.expandable && renderExpandedContent(log.expandable)}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Tests Tab */}
        {activeTab === 'tests' && (
          <div className="logs-view__tests">
            {testSummaries.length === 0 ? (
              <div className="logs-view__empty">
                <TestTube size={32} />
                <span>No test results available</span>
                <span className="logs-view__empty-hint">Test results will appear after builds complete</span>
              </div>
            ) : (
              <div className="logs-view__tests-content">
                {testSummaries.map((summary, summaryIndex) => (
                  <div key={summaryIndex} className="logs-view__test-run">
                    {/* Test Run Header */}
                    <div className="logs-view__test-run-header">
                      <div className="logs-view__test-run-title">
                        <span className="logs-view__test-run-build">Build #{summary.buildNumber}</span>
                        <span className="logs-view__test-run-time">{formatTimestamp(summary.timestamp)}</span>
                      </div>
                    </div>

                    {/* Test Summary Cards */}
                    <div className="logs-view__test-summary">
                      <div className="logs-view__test-stat logs-view__test-stat--total">
                        <span className="logs-view__test-stat-value">{summary.totalCount}</span>
                        <span className="logs-view__test-stat-label">Total</span>
                      </div>
                      <div className="logs-view__test-stat logs-view__test-stat--passed">
                        <CheckCircle2 size={16} />
                        <span className="logs-view__test-stat-value">{summary.passCount}</span>
                        <span className="logs-view__test-stat-label">Passed</span>
                      </div>
                      <div className="logs-view__test-stat logs-view__test-stat--failed">
                        <XCircle size={16} />
                        <span className="logs-view__test-stat-value">{summary.failCount}</span>
                        <span className="logs-view__test-stat-label">Failed</span>
                      </div>
                      <div className="logs-view__test-stat logs-view__test-stat--skipped">
                        <AlertCircle size={16} />
                        <span className="logs-view__test-stat-value">{summary.skipCount}</span>
                        <span className="logs-view__test-stat-label">Skipped</span>
                      </div>
                    </div>

                    {/* Failed Tests List */}
                    {summary.failedTests.length > 0 && (
                      <div className="logs-view__failed-tests">
                        <div className="logs-view__failed-tests-header">
                          <XCircle size={14} />
                          <span>Failed Tests ({summary.failedTests.length})</span>
                        </div>
                        <div className="logs-view__failed-tests-list">
                          {summary.failedTests.map((test, testIndex) => (
                            <div key={testIndex} className="logs-view__test-entry logs-view__test-entry--failed">
                              <span className="logs-view__test-icon">
                                <XCircle size={18} />
                              </span>
                              <div className="logs-view__test-details">
                                <span className="logs-view__test-name">{test.name}</span>
                                {test.className && (
                                  <span className="logs-view__test-class">{test.className}</span>
                                )}
                                {test.error && (
                                  <span className="logs-view__test-error">{test.error}</span>
                                )}
                              </div>
                              {test.duration && (
                                <span className="logs-view__test-duration">
                                  <Clock size={14} />
                                  {test.duration}ms
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* All Passed Message */}
                    {summary.failCount === 0 && summary.passCount > 0 && (
                      <div className="logs-view__all-passed">
                        <CheckCircle2 size={20} />
                        <span>All {summary.passCount} tests passed!</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Files Tab */}
        {activeTab === 'files' && (
          <div className="logs-view__files">
            {fileChanges.length === 0 ? (
              <div className="logs-view__empty">
                <FileCode size={32} />
                <span>No file changes detected</span>
                <span className="logs-view__empty-hint">File modifications will be tracked here</span>
              </div>
            ) : (
              <div className="logs-view__files-list">
                {fileChanges.map((file, index) => (
                  <div key={index} className={`logs-view__file-entry logs-view__file-entry--${file.action}`}>
                    <span className={`logs-view__file-action logs-view__file-action--${file.action}`}>
                      {file.action === 'created' ? '+' : file.action === 'deleted' ? '-' : '~'}
                    </span>
                    <span className="logs-view__file-path">{file.path}</span>
                    <span className="logs-view__file-time">{formatTimestamp(file.timestamp)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default LogsView;
