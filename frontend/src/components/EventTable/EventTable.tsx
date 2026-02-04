// src/components/EventTable/EventTable.tsx
// Sortable and filterable table view for events

import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  Filter,
  X,
  CheckCircle2,
  MessageSquare,
  Wrench,
  Play,
  AlertCircle,
  Info,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowDownToLine,
  Pause
} from 'lucide-react';
import { BaseEvent } from '../../services/types';
import './EventTable.css';

interface EventTableProps {
  events: BaseEvent[];
}

type SortField = 'timestamp' | 'type' | 'details';
type SortDirection = 'asc' | 'desc';

interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

const EVENT_TYPE_CONFIG: Record<string, { label: string; icon: React.ReactNode; className: string }> = {
  iteration_start: { label: 'Iteration Start', icon: <Play size={14} />, className: 'type--iteration' },
  iteration_end: { label: 'Iteration End', icon: <Play size={14} />, className: 'type--iteration' },
  claude_response: { label: 'Claude Response', icon: <MessageSquare size={14} />, className: 'type--claude' },
  tool_call: { label: 'Tool Call', icon: <Wrench size={14} />, className: 'type--tool' },
  tool_result: { label: 'Tool Result', icon: <CheckCircle2 size={14} />, className: 'type--result' },
  state_update: { label: 'State Update', icon: <Info size={14} />, className: 'type--state' },
  workflow_start: { label: 'Workflow Start', icon: <Play size={14} />, className: 'type--workflow' },
  workflow_complete: { label: 'Workflow Complete', icon: <CheckCircle2 size={14} />, className: 'type--workflow' },
  pr_summary: { label: 'PR Summary', icon: <Info size={14} />, className: 'type--pr' },
  error: { label: 'Error', icon: <AlertCircle size={14} />, className: 'type--error' },
  log: { label: 'Log', icon: <Info size={14} />, className: 'type--log' },
};

const ITEMS_PER_PAGE_OPTIONS = [10, 25, 50, 100];

export const EventTable: React.FC<EventTableProps> = ({ events }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'timestamp', direction: 'asc' });
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);
  const [showFilters, setShowFilters] = useState(false);
  const [autoFollow, setAutoFollow] = useState(true);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Get unique event types from data
  const availableTypes = useMemo(() => {
    const types = new Set(events.map(e => e.type));
    return Array.from(types);
  }, [events]);

  // Extract details string from event
  const getEventDetails = (event: BaseEvent): string => {
    // Defensive check for missing data
    if (!event.data) return 'No data';
    
    switch (event.type) {
      case 'iteration_start':
        return `Iteration ${event.data.iteration ?? '?'} of ${event.data.max_iterations ?? '?'}`;
      case 'claude_response':
        return event.data.message_preview || event.data.text_content?.substring(0, 100) || 'No content';
      case 'tool_call':
        return `${event.data.tool_name || 'Unknown tool'}: ${event.data.input_preview || ''}`;
      case 'tool_result':
        const resultSummary = event.data.result_summary ? `- ${event.data.result_summary.substring(0, 50)}` : '';
        return `${event.data.tool_name || 'Unknown tool'}: ${event.data.success ? 'Success' : 'Failed'} ${resultSummary}`;
      case 'workflow_start':
        return `${event.data.repo_owner || '?'}/${event.data.repo_name || '?'} on ${event.data.branch || '?'}`;
      case 'workflow_complete':
        return `${event.data.success ? 'Completed successfully' : 'Failed'} - ${event.data.total_iterations ?? '?'} iterations`;
      case 'state_update':
        return event.data.phase || 'State updated';
      case 'error':
        return `${event.data.error_type || 'Error'}: ${event.data.error_message || 'Unknown error'}`;
      case 'pr_summary':
        return `PR #${event.data.pr_number ?? '?'}: ${event.data.title || 'No title'}`;
      default:
        try {
          return JSON.stringify(event.data).substring(0, 100);
        } catch {
          return 'Unable to parse data';
        }
    }
  };

  // Filter and sort events
  const filteredAndSortedEvents = useMemo(() => {
    let result = [...events];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(event => {
        const details = getEventDetails(event).toLowerCase();
        const type = event.type.toLowerCase();
        return details.includes(query) || type.includes(query);
      });
    }

    // Apply type filter
    if (typeFilter.length > 0) {
      result = result.filter(event => typeFilter.includes(event.type));
    }

    // Apply sorting
    result.sort((a, b) => {
      let comparison = 0;
      
      switch (sortConfig.field) {
        case 'timestamp':
          comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
          break;
        case 'type':
          comparison = a.type.localeCompare(b.type);
          break;
        case 'details':
          comparison = getEventDetails(a).localeCompare(getEventDetails(b));
          break;
      }

      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [events, searchQuery, typeFilter, sortConfig]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedEvents.length / itemsPerPage);
  const paginatedEvents = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredAndSortedEvents.slice(start, start + itemsPerPage);
  }, [filteredAndSortedEvents, currentPage, itemsPerPage]);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, typeFilter, itemsPerPage]);

  // Auto-follow: jump to last page and scroll to bottom when new events arrive
  useEffect(() => {
    if (autoFollow && totalPages > 0) {
      setCurrentPage(totalPages);
      // Scroll to bottom of table after state updates
      setTimeout(() => {
        if (tableContainerRef.current) {
          tableContainerRef.current.scrollTop = tableContainerRef.current.scrollHeight;
        }
      }, 0);
    }
  }, [autoFollow, totalPages, filteredAndSortedEvents.length]);

  const handleSort = (field: SortField) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const toggleTypeFilter = (type: string) => {
    setTypeFilter(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const clearFilters = () => {
    setSearchQuery('');
    setTypeFilter([]);
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortConfig.field !== field) {
      return <ArrowUpDown size={14} />;
    }
    return sortConfig.direction === 'asc' ? <ArrowUp size={14} /> : <ArrowDown size={14} />;
  };

  return (
    <div className="event-table">
      {/* Toolbar */}
      <div className="event-table__toolbar">
        <div className="event-table__search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="event-table__search-clear" onClick={() => setSearchQuery('')}>
              <X size={14} />
            </button>
          )}
        </div>

        <div className="event-table__toolbar-actions">
          <button
            className={`event-table__filter-btn ${showFilters ? 'event-table__filter-btn--active' : ''}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter size={16} />
            <span>Filters</span>
            {typeFilter.length > 0 && (
              <span className="event-table__filter-count">{typeFilter.length}</span>
            )}
          </button>

          {(searchQuery || typeFilter.length > 0) && (
            <button className="event-table__clear-btn" onClick={clearFilters}>
              <X size={14} />
              <span>Clear</span>
            </button>
          )}

          <button
            className={`event-table__follow-btn ${autoFollow ? 'event-table__follow-btn--active' : ''}`}
            onClick={() => setAutoFollow(!autoFollow)}
            title={autoFollow ? 'Pause auto-follow' : 'Resume auto-follow'}
          >
            {autoFollow ? (
              <>
                <ArrowDownToLine size={16} />
                <span>Following</span>
              </>
            ) : (
              <>
                <Pause size={16} />
                <span>Paused</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="event-table__filters">
          <div className="event-table__filters-label">Filter by type:</div>
          <div className="event-table__filter-chips">
            {availableTypes.map(type => {
              const config = EVENT_TYPE_CONFIG[type] || { label: type, icon: <Info size={14} />, className: '' };
              const isActive = typeFilter.includes(type);
              
              return (
                <button
                  key={type}
                  className={`event-table__filter-chip ${isActive ? 'event-table__filter-chip--active' : ''}`}
                  onClick={() => toggleTypeFilter(type)}
                >
                  {config.icon}
                  <span>{config.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="event-table__container" ref={tableContainerRef}>
        <table>
          <thead>
            <tr>
              <th className="event-table__th--timestamp" onClick={() => handleSort('timestamp')}>
                <span>Timestamp</span>
                {getSortIcon('timestamp')}
              </th>
              <th className="event-table__th--type" onClick={() => handleSort('type')}>
                <span>Type</span>
                {getSortIcon('type')}
              </th>
              <th className="event-table__th--details" onClick={() => handleSort('details')}>
                <span>Details</span>
                {getSortIcon('details')}
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedEvents.length === 0 ? (
              <tr>
                <td colSpan={3} className="event-table__empty">
                  <div className="event-table__empty-content">
                    <Search size={24} />
                    <span>No events found</span>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedEvents.map((event, index) => {
                const config = EVENT_TYPE_CONFIG[event.type] || { label: event.type, icon: <Info size={14} />, className: '' };
                
                return (
                  <tr key={index}>
                    <td className="event-table__td--timestamp">
                      <span className="event-table__timestamp">
                        {formatTimestamp(event.timestamp)}
                      </span>
                    </td>
                    <td className="event-table__td--type">
                      <span className={`event-table__type-badge ${config.className}`}>
                        {config.icon}
                        <span>{config.label}</span>
                      </span>
                    </td>
                    <td className="event-table__td--details">
                      <span className="event-table__details">
                        {getEventDetails(event)}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="event-table__pagination">
        <div className="event-table__pagination-info">
          <span>
            Showing {((currentPage - 1) * itemsPerPage) + 1} - {Math.min(currentPage * itemsPerPage, filteredAndSortedEvents.length)} of {filteredAndSortedEvents.length}
          </span>
        </div>

        <div className="event-table__pagination-controls">
          <select
            value={itemsPerPage}
            onChange={(e) => setItemsPerPage(Number(e.target.value))}
            className="event-table__page-size"
          >
            {ITEMS_PER_PAGE_OPTIONS.map(size => (
              <option key={size} value={size}>{size} / page</option>
            ))}
          </select>

          <div className="event-table__pagination-buttons">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              title="First page"
            >
              <ChevronsLeft size={16} />
            </button>
            <button
              onClick={() => setCurrentPage(prev => prev - 1)}
              disabled={currentPage === 1}
              title="Previous page"
            >
              <ChevronLeft size={16} />
            </button>
            
            <span className="event-table__page-indicator">
              {currentPage} / {totalPages || 1}
            </span>

            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={currentPage >= totalPages}
              title="Next page"
            >
              <ChevronRight size={16} />
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage >= totalPages}
              title="Last page"
            >
              <ChevronsRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventTable;
