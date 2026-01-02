import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import type { Deployment } from '@/types';
import { Activity, AlertCircle, CheckCircle, Clock, ExternalLink, TrendingUp } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { parseDate } from '@/utils/dateUtils';

interface DeploymentCardProps {
  deployment: Deployment;
  onViewDetails: (id: string) => void;
  onStop: (id: string) => void;
}

export function DeploymentCard({ deployment, onViewDetails, onStop }: DeploymentCardProps) {
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
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'UNHEALTHY':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'UNKNOWN':
        return <Clock className="h-4 w-4 text-gray-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-xl">{deployment.tool_name}</CardTitle>
            <CardDescription>ID: {deployment.deployment_id}</CardDescription>
          </div>
          <Badge className={getStatusColor(deployment.status)}>
            {getStatusText(deployment.status)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Health Status */}
        <div className="flex items-center gap-2">
          {getHealthStatusIcon(deployment.health_status)}
          <span className="text-sm">
            健康状态: {getHealthStatusText(deployment.health_status)}
          </span>
        </div>

        {/* Endpoint URL */}
        <div className="flex items-center gap-2">
          <ExternalLink className="h-4 w-4 text-muted-foreground" />
          <a
            href={deployment.endpoint_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline truncate"
          >
            {deployment.endpoint_url}
          </a>
        </div>

        {/* Metrics */}
        {deployment.metrics && (
          <div className="grid grid-cols-3 gap-4 pt-2 border-t">
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-muted-foreground">
                <Activity className="h-3 w-3" />
                <span className="text-xs">请求总数</span>
              </div>
              <p className="text-lg font-semibold">{deployment.metrics.requests_total}</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span className="text-xs">平均响应</span>
              </div>
              <p className="text-lg font-semibold">{deployment.metrics.avg_response_time_ms}ms</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-muted-foreground">
                <TrendingUp className="h-3 w-3" />
                <span className="text-xs">错误率</span>
              </div>
              <p className="text-lg font-semibold">{(deployment.metrics.error_rate * 100).toFixed(2)}%</p>
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="text-xs text-muted-foreground space-y-1">
          <p>
            部署时间: {formatDistanceToNow(parseDate(deployment.deployed_at), { addSuffix: true, locale: zhCN })}
          </p>
          {deployment.last_health_check && (
            <p>
              最后健康检查: {formatDistanceToNow(parseDate(deployment.last_health_check), { addSuffix: true, locale: zhCN })}
            </p>
          )}
        </div>
      </CardContent>
      <CardFooter className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onViewDetails(deployment.deployment_id)}
        >
          查看详情
        </Button>
        {deployment.status === 'RUNNING' && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onStop(deployment.deployment_id)}
          >
            停止部署
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
