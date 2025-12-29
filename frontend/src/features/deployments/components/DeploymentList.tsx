import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import websocketClient from '@/services/websocketClient';
import { DeploymentCard } from './DeploymentCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Plus, Search } from 'lucide-react';
import type { Deployment } from '@/types';

interface DeploymentListProps {
  onViewDetails: (id: string) => void;
  onStop: (id: string) => void;
  onCreateNew: () => void;
}

export function DeploymentList({ onViewDetails, onStop, onCreateNew }: DeploymentListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const queryClient = useQueryClient();

  // Fetch deployments
  const {
    data: deployments,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['deployments'],
    queryFn: () => apiClient.deployments.list(),
  });

  // Set up WebSocket listener for deployment status updates
  // Requirements: 8.4 - WHEN 部署状态变化 THEN THE Frontend_App SHALL 通过 WebSocket 接收通知并更新部署列表
  useEffect(() => {
    const handleDeploymentUpdate = (data: any) => {
      console.log('Deployment status update received:', data);
      // Invalidate deployments query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      
      // Also invalidate specific deployment if we have the ID
      if (data.deployment_id) {
        queryClient.invalidateQueries({ queryKey: ['deployment', data.deployment_id] });
      }
    };

    // Listen for deployment status updates
    websocketClient.on('deployment_status', handleDeploymentUpdate);

    // Cleanup
    return () => {
      websocketClient.off('deployment_status', handleDeploymentUpdate);
    };
  }, [queryClient]);

  // Filter deployments based on search and status
  const filteredDeployments = deployments?.filter((deployment: Deployment) => {
    const matchesSearch =
      searchQuery === '' ||
      deployment.tool_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      deployment.deployment_id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || deployment.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          加载部署列表失败: {error instanceof Error ? error.message : '未知错误'}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索部署..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="状态过滤" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="running">运行中</SelectItem>
              <SelectItem value="starting">启动中</SelectItem>
              <SelectItem value="stopped">已停止</SelectItem>
              <SelectItem value="failed">失败</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button onClick={onCreateNew}>
          <Plus className="mr-2 h-4 w-4" />
          新建部署
        </Button>
      </div>

      {/* Deployments grid */}
      {filteredDeployments && filteredDeployments.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDeployments.map((deployment: Deployment) => (
            <DeploymentCard
              key={deployment.deployment_id}
              deployment={deployment}
              onViewDetails={onViewDetails}
              onStop={onStop}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground">
            {searchQuery || statusFilter !== 'all' ? '没有找到匹配的部署' : '还没有部署'}
          </p>
          {!searchQuery && statusFilter === 'all' && (
            <Button onClick={onCreateNew} className="mt-4">
              <Plus className="mr-2 h-4 w-4" />
              创建第一个部署
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
