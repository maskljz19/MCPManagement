import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertCircle, Activity } from 'lucide-react';
import apiClient from '@/services/apiClient';

export default function HealthStatus() {
  const { data: healthData, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.health.check(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            健康
          </Badge>
        );
      case 'unhealthy':
        return (
          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
            不健康
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            未知
          </Badge>
        );
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'border-l-green-500';
      case 'unhealthy':
        return 'border-l-red-500';
      default:
        return 'border-l-yellow-500';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          系统健康状态
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-6 w-20" />
              </div>
            ))}
          </div>
        ) : !healthData ? (
          <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>无法获取健康状态</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Overall Status */}
            <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                {getStatusIcon(healthData.status)}
                <span className="font-medium">总体状态</span>
              </div>
              {getStatusBadge(healthData.status)}
            </div>

            {/* Individual Services */}
            {Object.entries(healthData.services).map(([serviceName, serviceData]) => (
              <div
                key={serviceName}
                className={`flex items-center justify-between p-3 border-l-4 border rounded-lg ${getStatusColor(
                  serviceData.status
                )} ${serviceData.status === 'unhealthy' ? 'bg-red-50' : ''}`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(serviceData.status)}
                    <span className="font-medium capitalize">{serviceName}</span>
                  </div>
                  {serviceData.response_time_ms !== undefined && (
                    <p className="text-xs text-muted-foreground mt-1">
                      响应时间: {serviceData.response_time_ms}ms
                    </p>
                  )}
                  {serviceData.message && (
                    <p className="text-xs text-muted-foreground mt-1">{serviceData.message}</p>
                  )}
                </div>
                {getStatusBadge(serviceData.status)}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
