import React, { useEffect, useRef } from 'react';
import { BaseEvent } from '../services/types';
import { MessageCard } from './shared/MessageCard';

interface OutputStreamProps {
  events: BaseEvent[];
}

export const OutputStream: React.FC<OutputStreamProps> = ({ events }) => {
  const streamRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = React.useState(true);
  
  useEffect(() => {
    if (autoScroll && streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [events, autoScroll]);
  
  // Filter to only show relevant events in stream
  const streamEvents = events.filter(e => 
    ['iteration_start', 'claude_response', 'tool_call', 'tool_result'].includes(e.type)
  );
  
  return (
    <div className="column output-column">
      <div className="column-header">💬 Claude's Actions</div>
      <div className="column-content" ref={streamRef}>
        {streamEvents.map((event, index) => (
          <MessageCard key={index} event={event} />
        ))}
      </div>
      <button 
        className="auto-scroll"
        onClick={() => setAutoScroll(!autoScroll)}
      >
        Auto-scroll {autoScroll ? '↓' : '(off)'}
      </button>
    </div>
  );
};