import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExecutionModal from '../ExecutionModal';
import apiClient from '@/services/apiClient';

// Mock the apiClient
vi.mock('@/services/apiClient', () => ({
  default: {
    tools: {
      execute: vi.fn(),
    },
  },
}));

describe('ExecutionModal', () => {
  const mockOnOpenChange = vi.fn();
  const defaultProps = {
    open: true,
    onOpenChange: mockOnOpenChange,
    toolId: 'test-tool-id',
    toolName: 'Test Tool',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render modal when open', () => {
    render(<ExecutionModal {...defaultProps} />);
    
    expect(screen.getByText('执行工具: Test Tool')).toBeInTheDocument();
    expect(screen.getByText('配置参数并执行 MCP 工具')).toBeInTheDocument();
  });

  it('should not render modal when closed', () => {
    render(<ExecutionModal {...defaultProps} open={false} />);
    
    expect(screen.queryByText('执行工具: Test Tool')).not.toBeInTheDocument();
  });

  it('should display parameter input form', () => {
    render(<ExecutionModal {...defaultProps} />);
    
    expect(screen.getByLabelText(/参数/)).toBeInTheDocument();
    expect(screen.getByLabelText(/超时时间/)).toBeInTheDocument();
  });

  it('should validate JSON parameters', async () => {
    render(<ExecutionModal {...defaultProps} />);
    
    const argumentsInput = screen.getByLabelText(/参数/);
    const submitButton = screen.getByText('执行');
    
    // Enter invalid JSON
    fireEvent.change(argumentsInput, { target: { value: '{invalid json}' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('Arguments must be valid JSON')).toBeInTheDocument();
    });
  });

  it('should submit execution with valid parameters', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockResolvedValue({
      execution_id: 'exec-123',
      tool_id: 'test-tool-id',
      tool_name: 'Test Tool',
      status: 'success',
      result: { data: 'test result' },
      executed_at: '2024-01-01T00:00:00Z',
    });

    render(<ExecutionModal {...defaultProps} />);
    
    const argumentsInput = screen.getByLabelText(/参数/);
    const submitButton = screen.getByText('执行');
    
    // Enter valid JSON
    fireEvent.change(argumentsInput, { target: { value: '{"key": "value"}' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockExecute).toHaveBeenCalledWith('test-tool-id', {
        tool_name: 'Test Tool',
        arguments: { key: 'value' },
        timeout: 30,
      });
    });
  });

  it('should display execution results on success', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockResolvedValue({
      execution_id: 'exec-123',
      tool_id: 'test-tool-id',
      tool_name: 'Test Tool',
      status: 'success',
      result: { data: 'test result' },
      executed_at: '2024-01-01T00:00:00Z',
    });

    render(<ExecutionModal {...defaultProps} />);
    
    const submitButton = screen.getByText('执行');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/执行成功/)).toBeInTheDocument();
      expect(screen.getByText(/exec-123/)).toBeInTheDocument();
    });
  });

  it('should display error message on failure', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockRejectedValue({
      response: {
        data: {
          detail: 'Execution failed',
        },
      },
    });

    render(<ExecutionModal {...defaultProps} />);
    
    const submitButton = screen.getByText('执行');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('执行失败')).toBeInTheDocument();
      expect(screen.getByText('Execution failed')).toBeInTheDocument();
    });
  });

  it('should show loading indicator during execution', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<ExecutionModal {...defaultProps} />);
    
    const submitButton = screen.getByText('执行');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('执行中...')).toBeInTheDocument();
    });
  });

  it('should provide download options for results', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockResolvedValue({
      execution_id: 'exec-123',
      tool_id: 'test-tool-id',
      tool_name: 'Test Tool',
      status: 'success',
      result: { data: 'test result' },
      executed_at: '2024-01-01T00:00:00Z',
    });

    render(<ExecutionModal {...defaultProps} />);
    
    const submitButton = screen.getByText('执行');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('下载结果')).toBeInTheDocument();
      expect(screen.getByText('下载完整数据')).toBeInTheDocument();
    });
  });

  it('should pre-fill default arguments from tool config', () => {
    const toolConfig = {
      default_arguments: { foo: 'bar' },
    };

    render(<ExecutionModal {...defaultProps} toolConfig={toolConfig} />);
    
    const argumentsInput = screen.getByLabelText(/参数/) as HTMLTextAreaElement;
    expect(argumentsInput.value).toContain('"foo"');
    expect(argumentsInput.value).toContain('"bar"');
  });

  it('should allow retry after error', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockRejectedValue({
      response: {
        data: {
          detail: 'Execution failed',
        },
      },
    });

    render(<ExecutionModal {...defaultProps} />);
    
    const submitButton = screen.getByText('执行');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText('执行失败')).toBeInTheDocument();
    });

    const retryButton = screen.getByText('重试');
    fireEvent.click(retryButton);
    
    // Should show form again
    expect(screen.getByLabelText(/参数/)).toBeInTheDocument();
  });

  it('should allow re-execution after success', async () => {
    const mockExecute = vi.mocked(apiClient.tools.execute);
    mockExecute.mockResolvedValue({
      execution_id: 'exec-123',
      tool_id: 'test-tool-id',
      tool_name: 'Test Tool',
      status: 'success',
      result: { data: 'test result' },
      executed_at: '2024-01-01T00:00:00Z',
    });

    render(<ExecutionModal {...defaultProps} />);
    
    const submitButton = screen.getByText('执行');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/执行成功/)).toBeInTheDocument();
    });

    const reExecuteButton = screen.getByText('再次执行');
    fireEvent.click(reExecuteButton);
    
    // Should show form again
    expect(screen.getByLabelText(/参数/)).toBeInTheDocument();
  });
});
