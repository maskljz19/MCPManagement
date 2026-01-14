import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExecutionHistory from '../ExecutionHistory';
import apiClient from '@/services/apiClient';
import type { ExecutionLog } from '@/types';

// Mock the API client
vi.mock('@/services/apiClient', () => ({
  default: {
    tools: {
      getExecutionHistory: vi.fn(),
    },
  },
}));

const mockExecutions: ExecutionLog[] = [
  {
    id: '1',
    tool_id: 'tool-1',
    user_id: 'user-1',
    tool_name: 'Test Tool',
    arguments: { key: 'value' },
    result: { output: 'success' },
    status: 'success',
    start_time: '2024-01-01T10:00:00Z',
    end_time: '2024-01-01T10:00:05Z',
    duration_ms: 5000,
  },
  {
    id: '2',
    tool_id: 'tool-1',
    user_id: 'user-1',
    tool_name: 'Test Tool',
    arguments: { key: 'value2' },
    status: 'error',
    start_time: '2024-01-01T11:00:00Z',
    end_time: '2024-01-01T11:00:02Z',
    duration_ms: 2000,
    error: 'Test error message',
  },
];

describe('ExecutionHistory', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('should render loading state initially', () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('should render execution history when data is loaded', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(mockExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('执行历史')).toBeInTheDocument();
    });

    // Check that executions are displayed - look for the formatted dates
    await waitFor(() => {
      const dates = screen.getAllByText(/2024/);
      expect(dates.length).toBeGreaterThan(0);
    });
    
    // Check that both executions are in the table
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBeGreaterThan(2); // Header + at least 2 data rows
  });

  it('should display status badges correctly', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(mockExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
      expect(screen.getByText('error')).toBeInTheDocument();
    });
  });

  it('should display duration correctly', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(mockExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('5.00s')).toBeInTheDocument();
      expect(screen.getByText('2.00s')).toBeInTheDocument();
    });
  });

  it('should filter by status', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(mockExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
    });

    // Open status filter and select "success"
    const statusFilter = screen.getByRole('combobox');
    fireEvent.click(statusFilter);

    await waitFor(() => {
      const successOption = screen.getByRole('option', { name: '成功' });
      fireEvent.click(successOption);
    });

    // Only success execution should be visible
    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
      expect(screen.queryByText('error')).not.toBeInTheDocument();
    });
  });

  it('should open detail dialog when row is clicked', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(mockExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
    });

    // Click on the first row
    const rows = screen.getAllByRole('row');
    fireEvent.click(rows[1]); // Skip header row

    // Detail dialog should open
    await waitFor(() => {
      expect(screen.getByText('执行详情')).toBeInTheDocument();
      expect(screen.getByText(/执行 ID:/)).toBeInTheDocument();
    });
  });

  it('should display error message when API fails', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockRejectedValue(
      new Error('API Error')
    );

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('加载失败')).toBeInTheDocument();
      expect(screen.getByText('无法加载执行历史。请稍后重试。')).toBeInTheDocument();
    });
  });

  it('should show empty state when no executions', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue([]);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('暂无执行记录')).toBeInTheDocument();
    });
  });

  it('should paginate when more than 10 entries', async () => {
    const manyExecutions = Array.from({ length: 25 }, (_, i) => ({
      ...mockExecutions[0],
      id: `exec-${i}`,
      start_time: `2024-01-01T${String(i).padStart(2, '0')}:00:00Z`,
      end_time: `2024-01-01T${String(i).padStart(2, '0')}:00:05Z`,
    }));

    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(manyExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText(/第 1 \/ 3 页/)).toBeInTheDocument();
    });

    // Should show pagination controls
    expect(screen.getByText('上一页')).toBeInTheDocument();
    expect(screen.getByText('下一页')).toBeInTheDocument();
  });

  it('should clear filters when clear button is clicked', async () => {
    vi.mocked(apiClient.tools.getExecutionHistory).mockResolvedValue(mockExecutions);

    renderWithClient(
      <ExecutionHistory toolId="tool-1" toolName="Test Tool" />
    );

    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
    });

    // Set a filter
    const statusFilter = screen.getByRole('combobox');
    fireEvent.click(statusFilter);

    await waitFor(() => {
      const successOption = screen.getByRole('option', { name: '成功' });
      fireEvent.click(successOption);
    });

    // Click clear filters
    const clearButton = screen.getByText('清除筛选');
    fireEvent.click(clearButton);

    // All executions should be visible again
    await waitFor(() => {
      expect(screen.getByText('success')).toBeInTheDocument();
      expect(screen.getByText('error')).toBeInTheDocument();
    });
  });
});
