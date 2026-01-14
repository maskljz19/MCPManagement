import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ExecutionStatus from '../ExecutionStatus';
import apiClient from '@/services/apiClient';

// Mock the apiClient
vi.mock('@/services/apiClient', () => ({
  default: {
    executions: {
      getStatus: vi.fn(),
    },
  },
}));

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(public url: string) {
    // Simulate connection opening after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(_data: string) {
    // Mock send
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: code || 1000, reason: reason || '' }));
    }
  }
}

// Helper to create a failing WebSocket
class FailingWebSocket extends MockWebSocket {
  constructor(url: string) {
    super(url);
    // Immediately fail the connection
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) {
        this.onclose(new CloseEvent('close', { code: 1006, reason: 'Connection failed' }));
      }
    }, 5);
  }
}

describe('ExecutionStatus', () => {
  const mockExecutionId = 'test-execution-id';
  const mockOnComplete = vi.fn();
  const mockOnError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    
    // Mock localStorage
    Storage.prototype.getItem = vi.fn((key) => {
      if (key === 'auth') {
        return JSON.stringify({ access_token: 'test-token' });
      }
      return null;
    });

    // Mock WebSocket
    (window as any).WebSocket = MockWebSocket;
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('should render execution status card', () => {
    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    expect(screen.getByText('Execution Status')).toBeInTheDocument();
    expect(screen.getByText(/Execution ID:/)).toBeInTheDocument();
    expect(screen.getByText(mockExecutionId)).toBeInTheDocument();
  });

  it('should display queued status initially', () => {
    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    expect(screen.getByText('Queued')).toBeInTheDocument();
  });

  it('should show connecting indicator initially', () => {
    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('should fallback to polling when WebSocket fails', async () => {
    // Mock WebSocket to fail immediately
    (window as any).WebSocket = FailingWebSocket;

    // Mock API response
    vi.mocked(apiClient.executions.getStatus).mockResolvedValue({
      execution_id: mockExecutionId,
      status: 'running',
      progress: 50,
    });

    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    // Fast-forward to trigger WebSocket failure
    await vi.advanceTimersByTimeAsync(10);

    // Wait for polling mode indicator
    await waitFor(() => {
      expect(screen.getByText('Polling mode (2s interval)')).toBeInTheDocument();
    });

    // Verify API was called
    expect(apiClient.executions.getStatus).toHaveBeenCalledWith(mockExecutionId);
  });

  it('should display progress bar when progress is available', async () => {
    // Mock WebSocket to fail and trigger polling
    (window as any).WebSocket = FailingWebSocket;

    // Mock API response with progress
    vi.mocked(apiClient.executions.getStatus).mockResolvedValue({
      execution_id: mockExecutionId,
      status: 'running',
      progress: 75,
    });

    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    // Fast-forward to trigger WebSocket failure and polling
    await vi.advanceTimersByTimeAsync(10);

    // Wait for status to be fetched
    await waitFor(() => {
      expect(screen.getByText('Progress')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });

  it('should call onComplete when execution completes', async () => {
    // Mock WebSocket to fail and trigger polling
    (window as any).WebSocket = FailingWebSocket;

    // Mock API response with completed status
    vi.mocked(apiClient.executions.getStatus).mockResolvedValue({
      execution_id: mockExecutionId,
      status: 'completed',
      result: { output: 'success' },
    });

    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    // Fast-forward to trigger WebSocket failure and polling
    await vi.advanceTimersByTimeAsync(10);

    // Wait for completion callback
    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith('completed', { output: 'success' });
    });
  });

  it('should display error message when execution fails', async () => {
    const errorMessage = 'Execution failed due to timeout';
    
    // Mock WebSocket to fail and trigger polling
    (window as any).WebSocket = FailingWebSocket;

    // Mock API response with failed status
    vi.mocked(apiClient.executions.getStatus).mockResolvedValue({
      execution_id: mockExecutionId,
      status: 'failed',
      error: errorMessage,
    });

    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    // Fast-forward to trigger WebSocket failure and polling
    await vi.advanceTimersByTimeAsync(10);

    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByText('Execution Error')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    // Verify error callback was called
    expect(mockOnError).toHaveBeenCalledWith(errorMessage);
  });

  it('should display different status badges correctly', async () => {
    // Mock WebSocket to fail and trigger polling
    (window as any).WebSocket = FailingWebSocket;

    // Mock running status
    vi.mocked(apiClient.executions.getStatus).mockResolvedValue({
      execution_id: mockExecutionId,
      status: 'running',
      progress: 50,
    });

    render(
      <ExecutionStatus
        executionId={mockExecutionId}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    );

    // Initial queued status
    expect(screen.getByText('Queued')).toBeInTheDocument();

    // Fast-forward to trigger WebSocket failure and polling
    await vi.advanceTimersByTimeAsync(10);

    // Wait for running status
    await waitFor(() => {
      expect(screen.getByText('Running')).toBeInTheDocument();
    });
  });
});
