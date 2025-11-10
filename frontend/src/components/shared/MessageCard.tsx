import React from 'react';
import { BaseEvent } from '../../services/types';

interface MessageCardProps {
  event: BaseEvent;
}

export const MessageCard: React.FC<MessageCardProps> = ({ event }) => {
  const renderContent = () => {
    switch (event.type) {
      case 'iteration_start':
        return (
          <div className="output-message iteration-marker">
            <div className="message-header">
              <span>[{new Date(event.timestamp).toLocaleTimeString()}] Iteration {event.data.iteration}</span>
            </div>
          </div>
        );
        
      case 'claude_response':
        // Only show if there's actual text content
        if (!event.data.text_content && !event.data.message_preview) {
          return null;
        }
        return (
          <div className="output-message">
            <div className="message-content claude">
              💬 <strong>Claude:</strong><br/>
              {event.data.message_preview || event.data.text_content}
            </div>
          </div>
        );
        
      case 'tool_call':
        return (
          <div className="output-message tool-call-simple">
            <span className="tool-icon">⚙️</span>
            <span className="tool-text">Called tool: <strong>{event.data.tool_name}</strong></span>
          </div>
        );
        
      case 'tool_result':
        return (
          <div className="output-message tool-result-simple">
            <span className={event.data.success ? 'result-icon-success' : 'result-icon-error'}>
              {event.data.success ? '✅' : '❌'}
            </span>
            <span className="result-text">
              <strong>{event.data.tool_name}</strong> {event.data.success ? 'succeeded' : 'failed'}
              {event.data.execution_time_ms && (
                <span className="execution-time"> ({event.data.execution_time_ms}ms)</span>
              )}
            </span>
          </div>
        );
        
      default:
        return null;
    }
  };
  
  return <>{renderContent()}</>;
};