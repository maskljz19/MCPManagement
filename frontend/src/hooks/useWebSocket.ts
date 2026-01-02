import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useWebSocketStore } from '@/stores/websocketStore';
import websocketClient from '@/services/websocketClient';

/**
 * useWebSocket Hook
 * Manages WebSocket connection lifecycle based on authentication state
 * Requirements: 8.1, 8.2, 8.5, 8.6
 * 
 * - Establishes connection when user is authenticated
 * - Disconnects when user logs out
 * - Updates WebSocket store with connection state
 * - Handles reconnection attempts
 */
export function useWebSocket() {
  const { isAuthenticated, accessToken } = useAuthStore();
  const {
    setStatus,
    setConnected,
    setError,
    incrementReconnectAttempts,
    resetReconnectAttempts,
  } = useWebSocketStore();

  useEffect(() => {
    // Only connect if user is authenticated and has a token
    if (!isAuthenticated || !accessToken) {
      return;
    }

    // Set up event handlers
    const handleConnected = () => {
      setStatus('connected');
      setConnected(true);
      setError(null);
      resetReconnectAttempts();
    };

    const handleDisconnected = () => {
      setStatus('disconnected');
      setConnected(false);
    };

    const handleReconnecting = (_data: { attempt: number; maxAttempts: number }) => {
      setStatus('reconnecting');
      incrementReconnectAttempts();
    };

    const handleReconnectFailed = () => {
      setStatus('error');
      setError('无法连接到服务器，请刷新页面重试');
    };

    const handleError = (data: { error: string }) => {
      setStatus('error');
      setError(data.error);
    };

    // Register event handlers
    websocketClient.on('connected', handleConnected);
    websocketClient.on('disconnected', handleDisconnected);
    websocketClient.on('reconnecting', handleReconnecting);
    websocketClient.on('reconnect_failed', handleReconnectFailed);
    websocketClient.on('error', handleError);

    // Connect to WebSocket if not already connected
    if (!websocketClient.isConnected()) {
      setStatus('connecting');
      websocketClient.connect(accessToken);
    } else {
      // Already connected, update store
      setStatus('connected');
      setConnected(true);
    }

    // Cleanup function
    return () => {
      websocketClient.off('connected', handleConnected);
      websocketClient.off('disconnected', handleDisconnected);
      websocketClient.off('reconnecting', handleReconnecting);
      websocketClient.off('reconnect_failed', handleReconnectFailed);
      websocketClient.off('error', handleError);
    };
  }, [
    isAuthenticated,
    accessToken,
    setStatus,
    setConnected,
    setError,
    incrementReconnectAttempts,
    resetReconnectAttempts,
  ]);

  return {
    isConnected: websocketClient.isConnected(),
    status: useWebSocketStore((state) => state.status),
    error: useWebSocketStore((state) => state.error),
  };
}
