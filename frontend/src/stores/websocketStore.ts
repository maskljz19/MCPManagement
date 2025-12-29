import { create } from 'zustand';

/**
 * WebSocket Store
 * Requirements: 8.1
 * 
 * Manages WebSocket connection state and subscriptions.
 * Does not persist to localStorage as connection state is session-specific.
 */

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

interface WebSocketState {
  // State
  status: ConnectionStatus;
  isConnected: boolean;
  error: string | null;
  reconnectAttempts: number;
  subscriptions: Set<string>;
  
  // Actions
  setStatus: (status: ConnectionStatus) => void;
  setConnected: (connected: boolean) => void;
  setError: (error: string | null) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
  addSubscription: (taskId: string) => void;
  removeSubscription: (taskId: string) => void;
  clearSubscriptions: () => void;
  reset: () => void;
}

export const useWebSocketStore = create<WebSocketState>((set) => ({
  // Initial state
  status: 'disconnected',
  isConnected: false,
  error: null,
  reconnectAttempts: 0,
  subscriptions: new Set(),
  
  // Actions
  setStatus: (status) =>
    set({ status }),
  
  setConnected: (connected) =>
    set({ 
      isConnected: connected,
      status: connected ? 'connected' : 'disconnected',
    }),
  
  setError: (error) =>
    set({ error, status: error ? 'error' : 'disconnected' }),
  
  incrementReconnectAttempts: () =>
    set((state) => ({ 
      reconnectAttempts: state.reconnectAttempts + 1,
      status: 'reconnecting',
    })),
  
  resetReconnectAttempts: () =>
    set({ reconnectAttempts: 0 }),
  
  addSubscription: (taskId) =>
    set((state) => ({
      subscriptions: new Set(state.subscriptions).add(taskId),
    })),
  
  removeSubscription: (taskId) =>
    set((state) => {
      const newSubscriptions = new Set(state.subscriptions);
      newSubscriptions.delete(taskId);
      return { subscriptions: newSubscriptions };
    }),
  
  clearSubscriptions: () =>
    set({ subscriptions: new Set() }),
  
  reset: () =>
    set({
      status: 'disconnected',
      isConnected: false,
      error: null,
      reconnectAttempts: 0,
      subscriptions: new Set(),
    }),
}));
