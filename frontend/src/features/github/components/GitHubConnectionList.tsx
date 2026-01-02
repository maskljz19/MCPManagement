import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { GitBranch, RefreshCw, Trash2, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { GitHubConnection } from '@/types';

interface GitHubConnectionListProps {
  onSync?: (connectionId: string) => void;
  onDisconnect?: (connectionId: string) => void;
}

/**
 * GitHubConnectionList - Display list of GitHub connections
 * Shows repository connections with status and action buttons
 * Validates: Requirements 5.1
 */
export function GitHubConnectionList({ onSync, onDisconnect }: GitHubConnectionListProps) {
  const {
    data: connections,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['github-connections'],
    queryFn: () => apiClient.github.listConnections(),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-1/2 mt-2" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          加载 GitHub 连接失败: {error instanceof Error ? error.message : '未知错误'}
        </AlertDescription>
      </Alert>
    );
  }

  if (!connections || connections.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <GitBranch className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-lg font-medium mb-2">暂无 GitHub 连接</p>
          <p className="text-sm text-muted-foreground mb-4">
            连接您的 GitHub 仓库以自动同步 MCP 工具
          </p>
        </CardContent>
      </Card>
    );
  }

  const getStatusIcon = (status: GitHubConnection['status']) => {
    switch (status) {
      case 'CONNECTED':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'SYNCING':
        return <RefreshCw className="h-4 w-4 animate-spin" />;
      case 'ERROR':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getStatusVariant = (status: GitHubConnection['status']) => {
    switch (status) {
      case 'CONNECTED':
        return 'default';
      case 'SYNCING':
        return 'secondary';
      case 'ERROR':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusText = (status: GitHubConnection['status']) => {
    switch (status) {
      case 'CONNECTED':
        return '已连接';
      case 'SYNCING':
        return '同步中';
      case 'ERROR':
        return '错误';
      default:
        return '未知';
    }
  };

  return (
    <div className="space-y-4">
      {connections.map((connection) => (
        <Card key={connection.connection_id}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="h-5 w-5" />
                  {connection.repository_url}
                </CardTitle>
                <CardDescription className="mt-2">
                  工具 ID: {connection.tool_id}
                </CardDescription>
              </div>
              <Badge variant={getStatusVariant(connection.status)} className="flex items-center gap-1">
                {getStatusIcon(connection.status)}
                {getStatusText(connection.status)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                {connection.last_sync ? (
                  <>
                    最后同步:{' '}
                    {formatDistanceToNow(new Date(connection.last_sync), {
                      addSuffix: true,
                      locale: zhCN,
                    })}
                  </>
                ) : (
                  '从未同步'
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onSync?.(connection.connection_id)}
                  disabled={connection.status === 'SYNCING'}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  同步
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onDisconnect?.(connection.connection_id)}
                  disabled={connection.status === 'SYNCING'}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  断开
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
