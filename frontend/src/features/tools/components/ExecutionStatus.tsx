import { useState, useEffect, useCallback, useRef } from 'react';
import { Loader2, CheckCircle2, XCircle, AlertCircle, Clock, Zap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/services/apiClient';

interface ExecutionStatusProps {
  executionId: string;
  onComplete?: (status: string, result?: any) => void;
  onError?: (error: string) => void;
}

interface ExecutionStatusData {
  execution_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'timeout';
  progress?: number;
  metadata?: Record<string, any>;
  result?: Record<string, any>;
  error?: string;
  timestamp?: string;
}

interface WebSocketMessage {
  type: 'status_update' | 'log_entry' | 'execution_complete' | 'connected' | 'subscribed' | 'error' | 'pong';
  execution_id?: string;
  status?: string;
  progress?: number;
  metadata?: Record<string, any>;
  result?: Record<string, any>;
  error?: string;
  message?: string;
  timestamp?: string;
}

/**
 * ExecutionStatus component for real-time execution status display
 * 
 * Features:
 * - WebSocket connection for real-time updates
 * - Subscribe to execution updates
 * - Display real-time status changes
 * - Show progress bar when available
 * - Implement fallback to polling on WebSocket failure
 * 
 * Requirements: 3.1, 3.2, 3.4, 3.5
 */
export default function ExecutionStatus({
  executionId,
  onComplete,
  onError,
}: ExecutionStatusProps) {
  const [status, setStatus] = useState<ExecutionStatusData>({
    execution_id: executionId,
    status: 'queued',
    progress: 0,
  });
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [usePolling, setUsePolling] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;

  /**
   * Get authentication token from localStorage
   */
  const getAuthToken = useCallback((): string | null => {
    const authData = localStorage.getItem('auth');
    if (authData) {
      try {
        const parsed = JSON.parse(authData);
        return parsed.access_token || null;
      } catch {
        return null;
      }
    }
    return null;
  }, []);

  /**
   * Fetch execution status via polling (fallback)
   * Validates: Requirements 3.5
   */
  const fetchExecutionStatus = useCallback(async () => {
    try {
      const response = await apiClient.executions.getStatus(executionId);
      
      const newStatus: ExecutionStatusData = {
        execution_id: executionId,
        status: response.status as ExecutionStatusData['status'],
        progress: response.progress,
        metadata: response.metadata,
        result: response.result,
        error: response.error,
      };

      setStatus(newStatus);

      // Check if execution is complete
      if (['completed', 'failed', 'cancelled', 'timeout'].includes(response.status)) {
        if (onComplete) {
          onComplete(response.status, response.result);
        }
        if (response.status === 'failed' && onError && response.error) {
          onError(response.error);
        }
        // Stop polling when complete
        stopPolling();
      }
    } catch (error: any) {
      console.error('Failed to fetch execution status:', error);
      setConnectionError('Failed to fetch status');
    }
  }, [executionId, onComplete, onError]);

  /**
   * Start polling for status updates (fallback mechanism)
   * Validates: Requirements 3.5
   */
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      return; // Already polling
    }

    console.log('Starting polling fallback for execution:', executionId);
    setUsePolling(true);

    // Initial fetch
    fetchExecutionStatus();

    // Poll every 2 seconds
    pollingIntervalRef.current = window.setInterval(() => {
      fetchExecutionStatus();
    }, 2000);
  }, [executionId, fetchExecutionStatus]);

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setUsePolling(false);
  }, []);

  /**
   * Handle incoming WebSocket messages
   * Validates: Requirements 3.1, 3.2
   */
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      // Handle different message types
      switch (message.type) {
        case 'connected':
          console.log('WebSocket connected, subscribing to execution:', executionId);
          // Subscribe to execution updates
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              action: 'subscribe',
              execution_id: executionId,
            }));
          }
          break;

        case 'subscribed':
          console.log('Subscribed to execution updates:', message.execution_id);
          break;

        case 'status_update':
          if (message.execution_id === executionId && message.status) {
            const newStatus: ExecutionStatusData = {
              execution_id: executionId,
              status: message.status as ExecutionStatusData['status'],
              progress: message.progress,
              metadata: message.metadata,
              timestamp: message.timestamp,
            };
            setStatus(newStatus);
          }
          break;

        case 'execution_complete':
          if (message.execution_id === executionId && message.status) {
            const finalStatus: ExecutionStatusData = {
              execution_id: executionId,
              status: message.status as ExecutionStatusData['status'],
              result: message.result,
              error: message.error,
              timestamp: message.timestamp,
            };
            setStatus(finalStatus);

            // Notify parent component
            if (onComplete) {
              onComplete(message.status, message.result);
            }
            if (message.status === 'failed' && onError && message.error) {
              onError(message.error);
            }

            // Close WebSocket connection
            if (wsRef.current) {
              wsRef.current.close();
            }
          }
          break;

        case 'error':
          console.error('WebSocket error message:', message.message);
          setConnectionError(message.message || 'Unknown error');
          break;

        case 'pong':
          // Heartbeat response, ignore
          break;

        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, [executionId, onComplete, onError]);

  /**
   * Connect to WebSocket for real-time updates
   * Validates: Requirements 3.1, 3.2
   */
  const connectWebSocket = useCallback(() => {
    const token = getAuthToken();
    if (!token) {
      console.error('No authentication token available');
      setConnectionError('Authentication required');
      startPolling(); // Fallback to polling
      return;
    }

    try {
      // Get WebSocket URL from environment or default
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = import.meta.env.VITE_WS_HOST || window.location.host;
      const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws/executions?token=${encodeURIComponent(token)}`;

      console.log('Connecting to WebSocket:', wsUrl);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connection opened');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        stopPolling(); // Stop polling if it was active
      };

      ws.onmessage = handleWebSocketMessage;

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Don't reconnect if authentication failed (code 1008)
        if (event.code === 1008) {
          console.error('WebSocket authentication failed');
          setConnectionError('Authentication failed');
          startPolling(); // Fallback to polling
          return;
        }

        // Don't reconnect if execution is complete
        if (['completed', 'failed', 'cancelled', 'timeout'].includes(status.status)) {
          return;
        }

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            reconnectAttemptsRef.current++;
            connectWebSocket();
          }, delay);
        } else {
          console.error('Max reconnection attempts reached, falling back to polling');
          setConnectionError('WebSocket connection failed, using polling');
          startPolling(); // Fallback to polling
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError('Failed to connect');
      startPolling(); // Fallback to polling
    }
  }, [getAuthToken, handleWebSocketMessage, startPolling, stopPolling, status.status]);

  /**
   * Initialize connection on mount
   */
  useEffect(() => {
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      stopPolling();
    };
  }, [connectWebSocket, stopPolling]);

  /**
   * Get status icon based on current status
   */
  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
      case 'timeout':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'queued':
        return <Clock className="h-5 w-5 text-gray-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  /**
   * Get status badge variant
   */
  const getStatusBadge = () => {
    const statusText = status.status.charAt(0).toUpperCase() + status.status.slice(1);
    
    let variant: 'default' | 'secondary' | 'destructive' | 'outline' = 'secondary';
    
    switch (status.status) {
      case 'completed':
        variant = 'default';
        break;
      case 'failed':
      case 'timeout':
        variant = 'destructive';
        break;
      case 'running':
        variant = 'default';
        break;
      case 'queued':
      case 'cancelled':
        variant = 'secondary';
        break;
    }

    return (
      <Badge variant={variant} className="flex items-center gap-1">
        {getStatusIcon()}
        {statusText}
      </Badge>
    );
  };

  /**
   * Get connection status indicator
   */
  const getConnectionIndicator = () => {
    if (usePolling) {
      return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
          <span>Polling mode (2s interval)</span>
        </div>
      );
    }

    if (isConnected) {
      return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-green-500" />
          <span>Real-time updates</span>
          <Zap className="h-3 w-3" />
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <div className="h-2 w-2 rounded-full bg-gray-400 animate-pulse" />
        <span>Connecting...</span>
      </div>
    );
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Connection Error Alert */}
          {connectionError && !usePolling && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {connectionError}
              </AlertDescription>
            </Alert>
          )}

          {/* Status Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-sm font-medium text-muted-foreground">
                Execution Status
              </div>
              {getStatusBadge()}
            </div>
            {getConnectionIndicator()}
          </div>

          {/* Progress Bar */}
          {status.progress !== undefined && status.progress > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium">{status.progress}%</span>
              </div>
              <Progress value={status.progress} className="h-2" />
            </div>
          )}

          {/* Execution ID */}
          <div className="text-xs text-muted-foreground">
            <span className="font-medium">Execution ID:</span>{' '}
            <span className="font-mono">{executionId}</span>
          </div>

          {/* Error Message */}
          {status.error && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-1">Execution Error</div>
                <div className="text-sm">{status.error}</div>
              </AlertDescription>
            </Alert>
          )}

          {/* Metadata */}
          {status.metadata && Object.keys(status.metadata).length > 0 && (
            <div className="text-xs">
              <div className="font-medium text-muted-foreground mb-1">Metadata:</div>
              <pre className="bg-muted p-2 rounded text-xs overflow-auto max-h-20">
                {JSON.stringify(status.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
