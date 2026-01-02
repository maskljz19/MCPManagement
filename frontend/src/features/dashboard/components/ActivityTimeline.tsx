import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { Package, Rocket, Database, GitBranch, Clock } from 'lucide-react';
import apiClient from '@/services/apiClient';
import { parseDate } from '@/utils/dateUtils';

interface Activity {
  id: string;
  type: 'tool' | 'deployment' | 'document' | 'github';
  title: string;
  description: string;
  timestamp: string;
}

export default function ActivityTimeline() {
  // Fetch recent tools
  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ['tools', 'recent'],
    queryFn: () => apiClient.tools.list({ limit: 3, sort_by: 'created_at', order: 'desc' }),
  });

  // Fetch recent deployments
  const { data: deploymentsData, isLoading: deploymentsLoading } = useQuery({
    queryKey: ['deployments', 'recent'],
    queryFn: () => apiClient.deployments.list({ limit: 3 }),
  });

  // Fetch recent documents
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => apiClient.knowledge.listDocuments({ limit: 3, sort_by: 'created_at', order: 'desc' }),
  });

  const isLoading = toolsLoading || deploymentsLoading || documentsLoading;

  // Combine and sort activities
  const activities: Activity[] = [];

  if (toolsData?.items) {
    toolsData.items.forEach((tool) => {
      activities.push({
        id: `tool-${tool.id}`,
        type: 'tool',
        title: '创建了新工具',
        description: tool.name,
        timestamp: tool.created_at,
      });
    });
  }

  if (deploymentsData) {
    deploymentsData.forEach((deployment) => {
      activities.push({
        id: `deployment-${deployment.deployment_id}`,
        type: 'deployment',
        title: '部署了工具',
        description: deployment.tool_name,
        timestamp: deployment.deployed_at,
      });
    });
  }

  if (documentsData?.items) {
    documentsData.items.forEach((doc) => {
      activities.push({
        id: `doc-${doc.document_id}`,
        type: 'document',
        title: '上传了文档',
        description: doc.title,
        timestamp: doc.created_at,
      });
    });
  }

  // Sort by timestamp (most recent first)
  activities.sort((a, b) => parseDate(b.timestamp).getTime() - parseDate(a.timestamp).getTime());

  // Take only the 10 most recent
  const recentActivities = activities.slice(0, 10);

  const getActivityIcon = (type: Activity['type']) => {
    switch (type) {
      case 'tool':
        return Package;
      case 'deployment':
        return Rocket;
      case 'document':
        return Database;
      case 'github':
        return GitBranch;
      default:
        return Clock;
    }
  };

  const getActivityColor = (type: Activity['type']) => {
    switch (type) {
      case 'tool':
        return 'text-blue-600 bg-blue-100';
      case 'deployment':
        return 'text-green-600 bg-green-100';
      case 'document':
        return 'text-purple-600 bg-purple-100';
      case 'github':
        return 'text-orange-600 bg-orange-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>最近活动</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-start gap-3">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : recentActivities.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>暂无活动记录</p>
          </div>
        ) : (
          <div className="space-y-4">
            {recentActivities.map((activity) => {
              const Icon = getActivityIcon(activity.type);
              const colorClass = getActivityColor(activity.type);

              return (
                <div key={activity.id} className="flex items-start gap-3">
                  <div className={`p-2 rounded-full ${colorClass}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{activity.title}</p>
                    <p className="text-sm text-muted-foreground truncate">{activity.description}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(parseDate(activity.timestamp), {
                        addSuffix: true,
                        locale: zhCN,
                      })}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
