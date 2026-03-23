import { useEffect, useState, useRef } from 'react';
import { WebSocketService } from '../services/websocket';
import { BaseEvent } from '../services/types';

export const useWebSocket = (url?: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<BaseEvent[]>([]);
  const wsRef = useRef<WebSocketService | null>(null);
  
  useEffect(() => {
    const ws = new WebSocketService(url);
    wsRef.current = ws;
    
    // Connect
    ws.connect()
      .then(() => setIsConnected(true))
      .catch(console.error);
    
    // Subscribe to events
    const unsubscribe = ws.subscribe((event) => {
      // Clear stale events when a new workflow begins so
      // Logs, Table, and other views start with a clean slate.
      if (event.type === 'workflow_start') {
        setEvents([event]);
        return;
      }
      setEvents(prev => [...prev, event]);
    });
    
    // Cleanup
    return () => {
      unsubscribe();
      ws.disconnect();
    };
  }, [url]);
  
  return {
    isConnected,
    events,
    clearEvents: () => setEvents([])
  };
};