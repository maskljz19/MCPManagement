import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import websocketClient from '@/services/websocketClient';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  ArrowLeft,
  ExternalLink,
  Activity,
  Clock,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  StopCircle,
  RefreshCw,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Deployment } from '@/types';
import { parseDate } from '@/utils/dateUtils';

export default function DeploymentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showStopDialog, setShowStopDialog] = useState(false);

  // Fetch deployment details
  // Requirements: 6.4, 6.5 - Real-time status and health updates
  const {
    data: deployment,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['deployment', id],
    queryFn: () => apiClient.deployments.get(id!),
    enabled: !!id,
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
  });

  // Fetch deployment logs
  const { data: logs, isLoading: isLoadingLogs } = useQuery({
    queryKey: ['deployment-logs', id],
    queryFn: () => apiClient.deployments.getLogs(id!, 100),
    enabled: !!id,
  });

  // Set up WebSocket listener for deployment status updates
  // Requirements: 6.4 - WHEN 部署正在启动 THEN THE Frontend_App SHALL 通过 WebSocket 显示实时状态更新
  useEffect(() => {
    if (!id) return;

    const handleDeploymentUpdate = (data: any) => {
      console.log('Deployment status update received:', data);
      
      // Only update if it's for this deployment
      if (data.deployment_id === id) {
        // Invalidate queries to refetch latest data
        queryClient.invalidateQueries({ queryKey: ['deployment', id] });
        queryClient.invalidateQueries({ queryKey: ['deployment-logs', id] });
        
        // Show toast notification for status changes
        if (data.status) {
          toast({
            title: '部署状态更新',
            description: `状态已更新为: ${getStatusText(data.status)}`,
          });
        }
      }
    };

    // Listen for deployment status updates
    websocketClient.on('deployment_status', handleDeploymentUpdate);

    // Cleanup
    return () => {
      websocketClient.off('deployment_status', handleDeploymentUpdate);
    };
  }, [id, queryClient, toast]);

  // Stop deployment mutation
  const stopMutation = useMutation({
    mutationFn: () => apiClient.deployments.stop(id!),
    onSuccess: () => {
      toast({
        title: '成功',
        description: '部署已停止',
      });
      queryClient.invalidateQueries({ queryKey: ['deployment', id] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      setShowStopDialog(false);
    },
    onError: (error: Error) => {
      toast({
        title: '错误',
        description: `停止部署失败: ${error.message}`,
        variant: 'destructive',
      });
    },
  });

  const getStatusColor = (status: Deployment['status']) => {
    switch (status) {
      case 'RUNNING':
        return 'bg-green-500';
      case 'STARTING':
        return 'bg-blue-500';
      case 'STOPPED':
        return 'bg-gray-500';
      case 'FAILED':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = (status: Deployment['status']) => {
    switch (status) {
      case 'RUNNING':
        return '运行中';
      case 'STARTING':
        return '启动中';
      case 'STOPPED':
        return '已停止';
      case 'FAILED':
        return '失败';
      default:
        return status;
    }
  };

  const getHealthStatusIcon = (healthStatus: Deployment['health_status']) => {
    switch (healthStatus) {
      case 'HEALTHY':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'UNHEALTHY':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'UNKNOWN':
        return <Clock className="h-5 w-5 text-gray-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getHealthStatusText = (healthStatus: Deployment['health_status']) => {
    switch (healthStatus) {
      case 'HEALTHY':
        return '健康';
      case 'UNHEALTHY':
        return '不健康';
      case 'UNKNOWN':
        return '未知';
      default:
        return healthStatus;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-10 w-64" />
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (error || !deployment) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/deployments')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-3xl font-bold">部署详情</h1>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            加载部署详情失败: {error instanceof Error ? error.message : '未知错误'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/deployments')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{deployment.tool_name}</h1>
            <p className="text-sm text-muted-foreground">ID: {deployment.deployment_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          {deployment.status === 'RUNNING' && (
            <Button variant="destructive" size="sm" onClick={() => setShowStopDialog(true)}>
              <StopCircle className="h-4 w-4 mr-2" />
              停止部署
            </Button>
          )}
        </div>
      </div>

      {/* Status and Health */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>状态信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">部署状态</span>
              <Badge className={getStatusColor(deployment.status)}>
                {getStatusText(deployment.status)}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">健康状态</span>
              <div className="flex items-center gap-2">
                {getHealthStatusIcon(deployment.health_status)}
                <span className="text-sm">{getHealthStatusText(deployment.health_status)}</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">端点 URL</span>
              <a
                href={deployment.endpoint_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline flex items-center gap-1"
              >
                访问
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <div className="pt-2 border-t space-y-2">
              <div className="text-xs text-muted-foreground">
                部署时间: {formatDistanceToNow(parseDate(deployment.deployed_at), { addSuffix: true, locale: zhCN })}
              </div>
              {deployment.last_health_check && (
                <div className="text-xs text-muted-foreground">
                  最后健康检查: {formatDistanceToNow(parseDate(deployment.last_health_check), { addSuffix: true, locale: zhCN })}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Metrics */}
        {deployment.metrics && (
          <Card>
            <CardHeader>
              <CardTitle>性能指标</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Activity className="h-4 w-4" />
                    <span className="text-sm">请求总数</span>
                  </div>
                  <span className="text-2xl font-bold">{deployment.metrics.requests_total}</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span className="text-sm">平均响应时间</span>
                  </div>
                  <span className="text-2xl font-bold">{deployment.metrics.avg_response_time_ms}ms</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-sm">错误率</span>
                  </div>
                  <span className="text-2xl font-bold">{(deployment.metrics.error_rate * 100).toFixed(2)}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Logs */}
      <Card>
        <CardHeader>
          <CardTitle>部署日志</CardTitle>
          <CardDescription>最近 100 条日志</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingLogs ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin" />
              加载日志...
            </div>
          ) : logs && logs.length > 0 ? (
            <div className="bg-black text-green-400 p-4 rounded-md font-mono text-xs overflow-x-auto max-h-96 overflow-y-auto">
              {logs.map((log, index) => (
                <div key={index} className="whitespace-pre-wrap">
                  {log}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">暂无日志</p>
          )}
        </CardContent>
      </Card>

      {/* Stop confirmation dialog */}
      <AlertDialog open={showStopDialog} onOpenChange={setShowStopDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认停止部署</AlertDialogTitle>
            <AlertDialogDescription>
              您确定要停止此部署吗？此操作将终止运行中的服务。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => stopMutation.mutate()}>停止</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
