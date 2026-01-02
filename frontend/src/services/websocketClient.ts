/**
 * WebSocket Client for real-time communication
 * Handles connection management, event subscriptions, and automatic reconnection
 */

type EventHandler = (data: any) => void;

interface WebSocketMessage {
  action?: string;
  type?: string;
  task_id?: string;
  data?: any;
  [key: string]: any;
}

interface WebSocketClientConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string | null = null;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private heartbeatInterval: number;
  private reconnectAttempts: number = 0;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private isConnecting: boolean = false;
  private isManualClose: boolean = false;
  private subscriptions: Set<string> = new Set();

  constructor(config: WebSocketClientConfig) {
    this.url = config.url;
    this.reconnectInterval = config.reconnectInterval || 3000;
    this.maxReconnectAttempts = config.maxReconnectAttempts || 5;
    this.heartbeatInterval = config.heartbeatInterval || 30000;
  }

  /**
   * Connect to WebSocket server with authentication token
   * Requirements: 8.1 - WHEN 用户登录 THEN THE Frontend_App SHALL 建立 WebSocket 连接
   */
  connect(token: string): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      console.warn('WebSocket is already connected or connecting');
      return;
    }

    this.token = token;
    this.isManualClose = false;
    this.isConnecting = true;

    try {
      // Append token as query parameter
      const wsUrl = `${this.url}?token=${encodeURIComponent(token)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   * Requirements: 8.6 - WHEN 用户登出 THEN THE Frontend_App SHALL 关闭 WebSocket 连接
   */
  disconnect(): void {
    this.isManualClose = true;
    this.clearReconnectTimer();
    this.clearHeartbeatTimer();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.reconnectAttempts = 0;
    this.subscriptions.clear();
  }

  /**
   * Subscribe to a specific task or event
   * Requirements: 8.2 - WHEN WebSocket 连接建立 THEN THE Frontend_App SHALL 订阅相关事件
   */
  subscribe(taskId: string): void {
    this.subscriptions.add(taskId);
    
    if (this.isConnected()) {
      this.send({
        action: 'subscribe',
        task_id: taskId
      });
    }
  }

  /**
   * Unsubscribe from a specific task or event
   */
  unsubscribe(taskId: string): void {
    this.subscriptions.delete(taskId);
    
    if (this.isConnected()) {
      this.send({
        action: 'unsubscribe',
        task_id: taskId
      });
    }
  }

  /**
   * Register an event handler for a specific event type
   */
  on(event: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);
  }

  /**
   * Unregister an event handler
   */
  off(event: string, handler: EventHandler): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.eventHandlers.delete(event);
      }
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection state
   */
  getState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  /**
   * Send a message through WebSocket
   */
  private send(message: WebSocketMessage): void {
    if (this.isConnected() && this.ws) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
      }
    } else {
      console.warn('Cannot send message: WebSocket is not connected');
    }
  }

  /**
   * Handle WebSocket connection open
   */
  private handleOpen(): void {
    console.log('WebSocket connected');
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.clearReconnectTimer();
    
    // Start heartbeat
    this.startHeartbeat();
    
    // Resubscribe to all previous subscriptions
    this.resubscribeAll();

    // Emit connection event
    this.emit('connected', {});
  }

  /**
   * Resubscribe to all previous subscriptions
   */
  private resubscribeAll(): void {
    this.subscriptions.forEach(taskId => {
      this.send({
        action: 'subscribe',
        task_id: taskId
      });
    });
  }

  /**
   * Handle incoming WebSocket messages
   * Requirements: 8.3, 8.4 - Handle task and deployment status updates
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Handle heartbeat response
      if (message.type === 'pong') {
        return;
      }

      // Emit the message to registered handlers
      const eventType = message.type || 'message';
      this.emit(eventType, message.data || message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Handle WebSocket errors
   */
  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
    this.emit('error', { error: 'WebSocket connection error' });
  }

  /**
   * Handle WebSocket connection close
   * Requirements: 8.5 - WHEN WebSocket 连接断开 THEN THE Frontend_App SHALL 尝试自动重连
   */
  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', event.code, event.reason);
    this.isConnecting = false;
    this.clearHeartbeatTimer();
    
    this.emit('disconnected', {
      code: event.code,
      reason: event.reason
    });

    // Don't reconnect if authentication failed (code 1008 = Policy Violation)
    if (event.code === 1008) {
      console.error('WebSocket authentication failed. Please login again.');
      this.emit('auth_failed', {
        code: event.code,
        reason: event.reason
      });
      return;
    }

    // Attempt to reconnect if not manually closed
    if (!this.isManualClose) {
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule automatic reconnection
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('reconnect_failed', {
        attempts: this.reconnectAttempts
      });
      return;
    }

    this.clearReconnectTimer();
    
    const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts);
    console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.emit('reconnecting', {
        attempt: this.reconnectAttempts,
        maxAttempts: this.maxReconnectAttempts
      });
      
      if (this.token) {
        this.connect(this.token);
      }
    }, delay);
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.clearHeartbeatTimer();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          action: 'ping'
        });
      }
    }, this.heartbeatInterval);
  }

  /**
   * Clear reconnection timer
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Clear heartbeat timer
   */
  private clearHeartbeatTimer(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Emit an event to all registered handlers
   */
  private emit(event: string, data: any): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }
}

// Create singleton instance
const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws';
const websocketClient = new WebSocketClient({
  url: wsUrl,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  heartbeatInterval: 30000
});

export default websocketClient;
