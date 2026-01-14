import { useState } from 'react';
import { Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { usePermissions } from '@/hooks/usePermissions';
import ExecutionModal from './ExecutionModal';

interface ExecuteButtonProps {
  toolId: string;
  toolName: string;
  toolConfig?: Record<string, any>;
  onExecute?: () => void;
  disabled?: boolean;
}

/**
 * ExecuteButton component for MCP tool execution
 * 
 * Features:
 * - Permission-based visibility (only shows for users with execute permission)
 * - Click handler to open execution modal
 * - Loading states during execution
 * - Disabled state support
 * 
 * Requirements: 1.1, 1.2
 */
export default function ExecuteButton({
  toolId,
  toolName,
  toolConfig,
  onExecute,
  disabled = false,
}: ExecuteButtonProps) {
  const { can } = usePermissions();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Check if user has permission to execute tools
  // Using 'mcps' resource with 'create' action as proxy for execute permission
  const canExecute = can('mcps', 'create');

  // Don't render button if user doesn't have permission
  if (!canExecute) {
    return null;
  }

  const handleClick = () => {
    if (disabled) {
      return;
    }

    // Open the execution modal
    setIsModalOpen(true);
    
    // Call the onExecute callback if provided
    if (onExecute) {
      onExecute();
    }
  };

  return (
    <>
      <Button
        onClick={handleClick}
        disabled={disabled}
        className="gap-2"
        data-testid="execute-button"
      >
        <Play className="h-4 w-4" />
        执行
      </Button>

      <ExecutionModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        toolId={toolId}
        toolName={toolName}
        toolConfig={toolConfig}
      />
    </>
  );
}
