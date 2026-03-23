import { BaseEvent } from './types';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private listeners: ((event: BaseEvent) => void)[] = [];
  
  constructor(private url: string = 'wss://backend-websocket-ehv6woqt4q-uc.a.run.app/ws') {}
  
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        console.log('🔌 Connecting to WebSocket:', this.url);
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('✅ WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };
        
        this.ws.onmessage = (message) => {
          try {
            const parsed = JSON.parse(message.data);

            // The event gateway sends a history wrapper on connect:
            //   { type: "history", events: [...] }
            // Unpack and replay each event individually.
            if (parsed.type === 'history' && Array.isArray(parsed.events)) {
              console.log(`📜 Replaying ${parsed.events.length} historical events`);
              for (const event of parsed.events) {
                this.notifyListeners(event as BaseEvent);
              }
              return;
            }

            // Skip echo messages (server keepalive acks)
            if (parsed.type === 'echo') return;

            // Normal real-time event
            this.notifyListeners(parsed as BaseEvent);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
        
        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.handleReconnect();
        };
        
      } catch (error) {
        reject(error);
      }
    });
  }
  
  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }
  
  subscribe(listener: (event: BaseEvent) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }
  
  private notifyListeners(event: BaseEvent) {
    this.listeners.forEach(listener => listener(event));
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
