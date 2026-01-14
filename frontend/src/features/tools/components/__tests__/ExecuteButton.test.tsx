import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ExecuteButton from '../ExecuteButton';
import * as usePermissionsModule from '@/hooks/usePermissions';

// Mock the usePermissions hook
vi.mock('@/hooks/usePermissions');

// Mock the ExecutionModal component
vi.mock('../ExecutionModal', () => ({
  default: ({ open, toolId, toolName }: any) => 
    open ? <div data-testid="execution-modal">Modal for {toolName} ({toolId})</div> : null,
}));

describe('ExecuteButton', () => {
  const mockOnExecute = vi.fn();
  const defaultProps = {
    toolId: 'test-tool-id',
    toolName: 'Test Tool',
    onExecute: mockOnExecute,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render button when user has execute permission', () => {
    // Mock user with execute permission
    vi.spyOn(usePermissionsModule, 'usePermissions').mockReturnValue({
      can: () => true,
      canCreate: () => true,
      canRead: () => true,
      canUpdate: () => true,
      canDelete: () => true,
      permissions: {} as any,
      role: 'DEVELOPER',
    });

    render(<ExecuteButton {...defaultProps} />);
    
    const button = screen.getByTestId('execute-button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('执行');
  });

  it('should not render button when user lacks execute permission', () => {
    // Mock user without execute permission
    vi.spyOn(usePermissionsModule, 'usePermissions').mockReturnValue({
      can: () => false,
      canCreate: () => false,
      canRead: () => true,
      canUpdate: () => false,
      canDelete: () => false,
      permissions: {} as any,
      role: 'VIEWER',
    });

    render(<ExecuteButton {...defaultProps} />);
    
    const button = screen.queryByTestId('execute-button');
    expect(button).not.toBeInTheDocument();
  });

  it('should open modal when clicked', () => {
    vi.spyOn(usePermissionsModule, 'usePermissions').mockReturnValue({
      can: () => true,
      canCreate: () => true,
      canRead: () => true,
      canUpdate: () => true,
      canDelete: () => true,
      permissions: {} as any,
      role: 'DEVELOPER',
    });

    render(<ExecuteButton {...defaultProps} />);
    
    const button = screen.getByTestId('execute-button');
    fireEvent.click(button);
    
    // Modal should be visible
    const modal = screen.getByTestId('execution-modal');
    expect(modal).toBeInTheDocument();
    expect(modal).toHaveTextContent('Test Tool');
    expect(modal).toHaveTextContent('test-tool-id');
  });

  it('should call onExecute when clicked', () => {
    vi.spyOn(usePermissionsModule, 'usePermissions').mockReturnValue({
      can: () => true,
      canCreate: () => true,
      canRead: () => true,
      canUpdate: () => true,
      canDelete: () => true,
      permissions: {} as any,
      role: 'DEVELOPER',
    });

    render(<ExecuteButton {...defaultProps} />);
    
    const button = screen.getByTestId('execute-button');
    fireEvent.click(button);
    
    expect(mockOnExecute).toHaveBeenCalledTimes(1);
  });

  it('should be disabled when disabled prop is true', () => {
    vi.spyOn(usePermissionsModule, 'usePermissions').mockReturnValue({
      can: () => true,
      canCreate: () => true,
      canRead: () => true,
      canUpdate: () => true,
      canDelete: () => true,
      permissions: {} as any,
      role: 'DEVELOPER',
    });

    render(<ExecuteButton {...defaultProps} disabled={true} />);
    
    const button = screen.getByTestId('execute-button');
    expect(button).toBeDisabled();
  });

  it('should not open modal when disabled', () => {
    vi.spyOn(usePermissionsModule, 'usePermissions').mockReturnValue({
      can: () => true,
      canCreate: () => true,
      canRead: () => true,
      canUpdate: () => true,
      canDelete: () => true,
      permissions: {} as any,
      role: 'DEVELOPER',
    });

    render(<ExecuteButton {...defaultProps} disabled={true} />);
    
    const button = screen.getByTestId('execute-button');
    fireEvent.click(button);
    
    // Modal should not be visible
    const modal = screen.queryByTestId('execution-modal');
    expect(modal).not.toBeInTheDocument();
  });
});
