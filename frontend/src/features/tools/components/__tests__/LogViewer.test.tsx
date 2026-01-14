import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { LogViewer } from '../LogViewer';
import { apiClient } from '../../../../services/apiClient';

vi.mock('../../../../services/apiClient');

describe('LogViewer Component', () => {
  const mockExecutionId = 'test-execution-123';
  const mockLogs = [
    {
      timestamp: '2024-01-15T10:00:00Z',
      level: 'INFO' as const,
      message: 'Execution started',
    },
    {
      timestamp: '2024-01-15T10:00:01Z',
      level: 'DEBUG' as const,
      message: 'Processing input parameters',
    },
    {
      timestamp: '2024-01-15T10:00:02Z',
      level: 'WARNING' as const,
      message: 'High memory usage detected',
    },
    {
      timestamp: '2024-01-15T10:00:03Z',
      level: 'ERROR' as const,
      message: 'Connection timeout',
    },
    {
      timestamp: '2024-01-15T10:00:04Z',
      level: 'INFO' as const,
      message: 'Execution completed',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render loading state initially', () => {
    vi.mocked(apiClient.executions.getLogs).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<LogViewer executionId={mockExecutionId} />);

    expect(screen.getByText('Loading logs...')).toBeInTheDocument();
  });

  it('should fetch and display logs', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    expect(screen.getByText('Processing input parameters')).toBeInTheDocument();
    expect(screen.getByText('High memory usage detected')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    expect(screen.getByText('Execution completed')).toBeInTheDocument();
  });

  it('should display log count', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('5 / 5 entries')).toBeInTheDocument();
    });
  });

  it('should filter logs based on search term', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search logs...');
    fireEvent.change(searchInput, { target: { value: 'timeout' } });

    await waitFor(() => {
      expect(screen.getByText('1 / 5 entries')).toBeInTheDocument();
    });

    // Use a more flexible matcher since text is split by highlight
    expect(screen.getByText(/Connection/)).toBeInTheDocument();
    expect(screen.queryByText('Execution started')).not.toBeInTheDocument();
  });

  it('should highlight search term in logs', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search logs...');
    fireEvent.change(searchInput, { target: { value: 'execution' } });

    await waitFor(() => {
      const highlights = document.querySelectorAll('mark');
      expect(highlights.length).toBeGreaterThan(0);
    });
  });

  it('should download logs when download button is clicked', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    // Mock URL.createObjectURL and URL.revokeObjectURL
    const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
    const mockRevokeObjectURL = vi.fn();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    // Mock document.createElement to track anchor creation
    const mockClick = vi.fn();
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      const element = originalCreateElement(tagName);
      if (tagName === 'a') {
        element.click = mockClick;
      }
      return element;
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    const downloadButton = screen.getByText('Download Logs');
    fireEvent.click(downloadButton);

    expect(mockCreateObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('should display error message when log fetch fails', async () => {
    const errorMessage = 'Failed to fetch logs';
    vi.mocked(apiClient.executions.getLogs).mockRejectedValue(
      new Error(errorMessage)
    );

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Error Loading Logs')).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('should retry fetching logs when retry button is clicked', async () => {
    vi.mocked(apiClient.executions.getLogs)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ logs: mockLogs });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Error Loading Logs')).toBeInTheDocument();
    });

    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });
  });

  it('should toggle auto-scroll', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    const autoScrollCheckbox = screen.getByLabelText('Auto-scroll') as HTMLInputElement;
    expect(autoScrollCheckbox.checked).toBe(true);

    fireEvent.click(autoScrollCheckbox);
    expect(autoScrollCheckbox.checked).toBe(false);

    fireEvent.click(autoScrollCheckbox);
    expect(autoScrollCheckbox.checked).toBe(true);
  });

  it('should display message when no logs match search', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: mockLogs,
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search logs...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    await waitFor(() => {
      expect(screen.getByText('No logs match your search')).toBeInTheDocument();
    });
  });

  it('should display message when no logs are available', async () => {
    vi.mocked(apiClient.executions.getLogs).mockResolvedValue({
      logs: [],
    });

    render(<LogViewer executionId={mockExecutionId} />);

    await waitFor(() => {
      expect(screen.getByText('No logs available')).toBeInTheDocument();
    });
  });

  it('should auto-refresh logs when enabled', async () => {
    const initialLogs = [mockLogs[0]];
    const updatedLogs = mockLogs;

    let callCount = 0;
    vi.mocked(apiClient.executions.getLogs).mockImplementation(async () => {
      callCount++;
      return { logs: callCount === 1 ? initialLogs : updatedLogs };
    });

    render(
      <LogViewer
        executionId={mockExecutionId}
        autoRefresh={true}
        refreshInterval={100} // Short interval for testing
      />
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Execution started')).toBeInTheDocument();
    });

    expect(callCount).toBe(1);

    // Wait for auto-refresh to trigger
    await waitFor(
      () => {
        expect(callCount).toBeGreaterThanOrEqual(2);
      },
      { timeout: 1000 }
    );
  });
});
