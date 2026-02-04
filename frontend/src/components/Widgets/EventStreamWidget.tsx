// src/components/Widgets/EventStreamWidget.tsx
// Displays real-time event stream with expandable cards

import React, { useEffect, useRef, useState } from 'react';
import {
  MessageSquare,
  Wrench,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Play,
  Inbox,
  ArrowDown,
  Pause
} from 'lucide-react';
import { BaseEvent } from '../../services/types';
import './EventStreamWidget.css';

interface EventStreamWidgetProps {
  events: BaseEvent[];
}

interface EventCardProps {
  event: BaseEvent;
  isExpanded: boolean;
  onToggle: () => void;
}

const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return '';
  }
};

const EventCard: React.FC<EventCardProps> = ({ event, isExpanded, onToggle }) => {
  const renderEventContent = () => {
    switch (event.type) {
      case 'iteration_start':
        return (
          <div className="event-card__content event-card__content--iteration">
            <div className="event-card__icon event-card__icon--iteration">
              <Play size={14} />
            </div>
            <div className="event-card__main">
              <span className="event-card__title">Iteration {event.data.iteration}</span>
              <span className="event-card__subtitle">
                Progress: {event.data.progress_percent?.toFixed(0) || 0}%
              </span>
            </div>
          </div>
        );

      case 'claude_response':
        if (!event.data.text_content && !event.data.message_preview) {
          return null;
        }
        return (
          <div className="event-card__content event-card__content--claude">
            <div className="event-card__icon event-card__icon--claude">
              <MessageSquare size={14} />
            </div>
            <div className="event-card__main">
              <span className="event-card__title">Claude Response</span>
              <span className="event-card__preview">
                {event.data.message_preview || event.data.text_content?.substring(0, 100)}
                {(event.data.text_content?.length > 100) && '...'}
              </span>
              {event.data.has_tool_use && (
                <span className="event-card__badge">
                  {event.data.tool_count} tool{event.data.tool_count !== 1 ? 's' : ''} called
                </span>
              )}
            </div>
            {event.data.text_content && event.data.text_content.length > 100 && (
              <button className="event-card__expand" onClick={onToggle}>
                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            )}
          </div>
        );

      case 'tool_call':
        return (
          <div className="event-card__content event-card__content--tool-call">
            <div className="event-card__icon event-card__icon--tool">
              <Wrench size={14} />
            </div>
            <div className="event-card__main">
              <span className="event-card__title">{event.data.tool_name}</span>
              <span className="event-card__preview">
                {event.data.input_preview?.substring(0, 80)}
                {(event.data.input_preview?.length > 80) && '...'}
              </span>
            </div>
            {event.data.tool_input && Object.keys(event.data.tool_input).length > 0 && (
              <button className="event-card__expand" onClick={onToggle}>
                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            )}
          </div>
        );

      case 'tool_result':
        return (
          <div className={`event-card__content event-card__content--tool-result ${event.data.success ? 'event-card__content--success' : 'event-card__content--error'}`}>
            <div className={`event-card__icon ${event.data.success ? 'event-card__icon--success' : 'event-card__icon--error'}`}>
              {event.data.success ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
            </div>
            <div className="event-card__main">
              <span className="event-card__title">
                {event.data.tool_name} - {event.data.success ? 'Success' : 'Failed'}
              </span>
              {event.data.execution_time_ms && (
                <span className="event-card__meta">
                  <Clock size={12} />
                  {event.data.execution_time_ms}ms
                </span>
              )}
              {event.data.result_summary && (
                <span className="event-card__preview">
                  {event.data.result_summary.substring(0, 80)}
                  {event.data.result_summary.length > 80 && '...'}
                </span>
              )}
              {event.data.error_message && (
                <span className="event-card__error">
                  {event.data.error_message}
                </span>
              )}
            </div>
            {(event.data.result_summary?.length > 80 || event.data.error_message) && (
              <button className="event-card__expand" onClick={onToggle}>
                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const renderExpandedContent = () => {
    if (!isExpanded) return null;

    switch (event.type) {
      case 'claude_response':
        return (
          <div className="event-card__expanded">
            <div className="event-card__expanded-label">Full Response</div>
            <div className="event-card__expanded-content">
              {event.data.text_content}
            </div>
          </div>
        );

      case 'tool_call':
        return (
          <div className="event-card__expanded">
            <div className="event-card__expanded-label">Tool Input</div>
            <pre className="event-card__expanded-code">
              {JSON.stringify(event.data.tool_input, null, 2)}
            </pre>
          </div>
        );

      case 'tool_result':
        return (
          <div className="event-card__expanded">
            {event.data.result_summary && (
              <>
                <div className="event-card__expanded-label">Result</div>
                <div className="event-card__expanded-content">
                  {event.data.result_summary}
                </div>
              </>
            )}
            {event.data.error_message && (
              <>
                <div className="event-card__expanded-label">Error Details</div>
                <div className="event-card__expanded-error">
                  {event.data.error_message}
                </div>
              </>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const content = renderEventContent();
  if (!content) return null;

  return (
    <div className={`event-card ${isExpanded ? 'event-card--expanded' : ''}`}>
      <div className="event-card__timestamp">
        {formatTimestamp(event.timestamp)}
      </div>
      {content}
      {renderExpandedContent()}
    </div>
  );
};

export const EventStreamWidget: React.FC<EventStreamWidgetProps> = ({ events }) => {
  const streamRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());

  // Filter to relevant events and sort chronologically (oldest first, newest at bottom)
  const streamEvents = events
    .filter(e => ['iteration_start', 'claude_response', 'tool_call', 'tool_result'].includes(e.type))
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [streamEvents.length, autoScroll]);

  const toggleExpanded = (index: number) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  if (streamEvents.length === 0) {
    return (
      <div className="event-stream-widget event-stream-widget--empty">
        <div className="event-stream-widget__empty-state">
          <Inbox size={32} />
          <span className="event-stream-widget__empty-title">No Events Yet</span>
          <span className="event-stream-widget__empty-text">
            Events will stream here in real-time
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="event-stream-widget">
      {/* Stream */}
      <div className="event-stream-widget__stream" ref={streamRef}>
        {streamEvents.map((event, index) => (
          <EventCard
            key={index}
            event={event}
            isExpanded={expandedEvents.has(index)}
            onToggle={() => toggleExpanded(index)}
          />
        ))}
      </div>

      {/* Controls */}
      <div className="event-stream-widget__controls">
        <span className="event-stream-widget__count">
          {streamEvents.length} events
        </span>
        <button
          className={`event-stream-widget__scroll-btn ${autoScroll ? 'event-stream-widget__scroll-btn--active' : ''}`}
          onClick={() => setAutoScroll(!autoScroll)}
          title={autoScroll ? 'Pause auto-scroll' : 'Resume auto-scroll'}
        >
          {autoScroll ? (
            <>
              <ArrowDown size={14} />
              <span>Auto-scroll</span>
            </>
          ) : (
            <>
              <Pause size={14} />
              <span>Paused</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default EventStreamWidget;
