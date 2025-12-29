import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient } from '@/services/apiClient';
import websocketClient from '@/services/websocketClient';
import { CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react';
import type { TaskStatus } from '@/types';

interface TaskProgressProps {
  taskId: string;
  onComplete?: (result: any) => void;
}

/**
 * TaskProgress Component
 * Displays real-time progress updates for async tasks
 * Integrates with WebSocket for live updates
 * Requirements: 4.4 - Real-time task progress updates
 */
export function TaskProgress({ taskId, onComplete }: TaskProgressProps) {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);

  // Fetch initial task status
  const { data: initialStatus, isLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => apiClient.analysis.getTaskStatus(taskId),
    refetchInterval: (query) => {
      // Stop polling if task is completed or failed
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      // Poll every 2 seconds for pending/running tasks
      return 2000;
    },
  });

  // Update local state when initial status is fetched
  useEffect(() => {
    if (initialStatus) {
      setTaskStatus(initialStatus);
    }
  }, [initialStatus]);

  // Subscribe to WebSocket updates for this task
  useEffect(() => {
    const handleTaskUpdate = (data: any) => {
      if (data.task_id === taskId) {
        setTaskStatus(data);
        
        // Call onComplete callback when task is completed
        if (data.status === 'completed' && onComplete) {
          onComplete(data.result);
        }
      }
    };

    // Subscribe to task updates
    websocketClient.on('task_update', handleTaskUpdate);
    websocketClient.subscribe(taskId);

    // Cleanup
    return () => {
      websocketClient.off('task_update', handleTaskUpdate);
      websocketClient.unsubscribe(taskId);
    };
  }, [taskId, onComplete]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (!taskStatus) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>无法加载任务</AlertTitle>
        <AlertDescription>任务 ID: {taskId}</AlertDescription>
      </Alert>
    );
  }

  const getStatusIcon = () => {
    switch (taskStatus.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Loader2 className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = () => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      pending: 'secondary',
      running: 'default',
      completed: 'outline',
      failed: 'destructive',
    };

    const labels: Record<string, string> = {
      pending: '等待中',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
    };

    return (
      <Badge variant={variants[taskStatus.status] || 'default'}>
        {labels[taskStatus.status] || taskStatus.status}
      </Badge>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="font-medium">任务状态</span>
        </div>
        {getStatusBadge()}
      </div>

      {(taskStatus.status === 'running' || taskStatus.status === 'pending') && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">进度</span>
            <span className="font-medium">{taskStatus.progress || 0}%</span>
          </div>
          <Progress value={taskStatus.progress || 0} />
        </div>
      )}

      {taskStatus.status === 'completed' && taskStatus.result && (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>分析完成</AlertTitle>
          <AlertDescription>
            <div className="mt-2 space-y-2">
              {taskStatus.result.feasibility_score !== undefined && (
                <div>
                  <span className="font-medium">可行性分数: </span>
                  <span className="text-lg font-bold text-green-600">
                    {taskStatus.result.feasibility_score}/100
                  </span>
                </div>
              )}
              {taskStatus.result.reasoning && (
                <div>
                  <span className="font-medium">推理: </span>
                  <p className="text-sm mt-1">{taskStatus.result.reasoning}</p>
                </div>
              )}
              {taskStatus.result.suggestions && Array.isArray(taskStatus.result.suggestions) && (
                <div>
                  <span className="font-medium">建议:</span>
                  <ul className="list-disc list-inside text-sm mt-1 space-y-1">
                    {taskStatus.result.suggestions.map((suggestion: string, index: number) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
              {taskStatus.result.improvements && Array.isArray(taskStatus.result.improvements) && (
                <div>
                  <span className="font-medium">改进建议:</span>
                  <ul className="list-disc list-inside text-sm mt-1 space-y-1">
                    {taskStatus.result.improvements.map((improvement: string, index: number) => (
                      <li key={index}>{improvement}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {taskStatus.status === 'failed' && taskStatus.error && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>任务失败</AlertTitle>
          <AlertDescription>{taskStatus.error}</AlertDescription>
        </Alert>
      )}

      <div className="text-xs text-muted-foreground">
        任务 ID: {taskId}
      </div>
    </div>
  );
}
