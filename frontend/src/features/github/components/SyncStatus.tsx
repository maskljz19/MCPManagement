import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import websocketClient from '@/services/websocketClient';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react';
import type { TaskStatus as TaskStatusType } from '@/types';

interface SyncStatusProps {
  taskId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: (success: boolean) => void;
}

/**
 * SyncStatus - Display sync progress and results
 * Shows real-time sync progress via WebSocket and displays results
 * Validates: Requirements 5.4, 5.5
 */
export function SyncStatus({ taskId, open, onOpenChange, onComplete }: SyncStatusProps) {
  const [taskStatus, setTaskStatus] = useState<TaskStatusType | null>(null);

  // Poll task status
  const { data: polledStatus } = useQuery({
    queryKey: ['task-status', taskId],
    queryFn: () => apiClient.analysis.getTaskStatus(taskId!),
    enabled: !!taskId && open,
    refetchInterval: (query) => {
      // Stop polling if task is completed or failed
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });

  // Update local state when polled status changes
  useEffect(() => {
    if (polledStatus) {
      setTaskStatus(polledStatus);
    }
  }, [polledStatus]);

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (!taskId || !open) return;

    const handleTaskUpdate = (data: any) => {
      if (data.task_id === taskId) {
        setTaskStatus({
          task_id: data.task_id,
          status: data.status,
          progress: data.progress,
          result: data.result,
          error: data.error,
        });

        // Notify parent when task completes
        if (data.status === 'completed' || data.status === 'failed') {
          onComplete?.(data.status === 'completed');
        }
      }
    };

    websocketClient.on('task_update', handleTaskUpdate);

    return () => {
      websocketClient.off('task_update', handleTaskUpdate);
    };
  }, [taskId, open, onComplete]);

  const getStatusIcon = () => {
    if (!taskStatus) return <Loader2 className="h-5 w-5 animate-spin" />;

    switch (taskStatus.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-destructive" />;
      case 'running':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      default:
        return <Loader2 className="h-5 w-5 animate-spin" />;
    }
  };

  const getStatusText = () => {
    if (!taskStatus) return '初始化中...';

    switch (taskStatus.status) {
      case 'pending':
        return '等待中...';
      case 'running':
        return '同步中...';
      case 'completed':
        return '同步完成';
      case 'failed':
        return '同步失败';
      default:
        return '未知状态';
    }
  };

  const getStatusBadgeVariant = () => {
    if (!taskStatus) return 'secondary';

    switch (taskStatus.status) {
      case 'completed':
        return 'default';
      case 'failed':
        return 'destructive';
      case 'running':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getStatusIcon()}
            GitHub 同步状态
          </DialogTitle>
          <DialogDescription>
            正在同步 GitHub 仓库配置到 MCP 工具
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Status Badge */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">状态:</span>
            <Badge variant={getStatusBadgeVariant()}>{getStatusText()}</Badge>
          </div>

          {/* Progress Bar */}
          {taskStatus?.status === 'running' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">进度</span>
                <span className="font-medium">{taskStatus.progress || 0}%</span>
              </div>
              <Progress value={taskStatus.progress || 0} />
            </div>
          )}

          {/* Success Result */}
          {taskStatus?.status === 'completed' && taskStatus.result && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p className="font-medium">同步成功!</p>
                  {taskStatus.result.tools_synced !== undefined && (
                    <p className="text-sm">
                      已同步 {taskStatus.result.tools_synced} 个工具配置
                    </p>
                  )}
                  {taskStatus.result.message && (
                    <p className="text-sm text-muted-foreground">
                      {taskStatus.result.message}
                    </p>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Error Result */}
          {taskStatus?.status === 'failed' && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p className="font-medium">同步失败</p>
                  <p className="text-sm">
                    {taskStatus.error || '发生未知错误,请稍后重试'}
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Task ID */}
          {taskId && (
            <div className="text-xs text-muted-foreground">
              任务 ID: {taskId}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
