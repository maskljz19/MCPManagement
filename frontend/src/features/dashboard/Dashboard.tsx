import { useQuery } from '@tanstack/react-query';
import { Package, Rocket, Activity, Database } from 'lucide-react';
import apiClient from '@/services/apiClient';
import StatsCard from './components/StatsCard';
import ActivityTimeline from './components/ActivityTimeline';
import HealthStatus from './components/HealthStatus';
import MetricsChart from './components/MetricsChart';
import { Skeleton } from '@/components/ui/skeleton';
import { useAnnouncer } from '@/components/common';
import { useEffect } from 'react';

/**
 * Dashboard - Main dashboard page
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 10.5
 * 
 * Accessibility Features:
 * - Semantic HTML with proper heading hierarchy
 * - ARIA labels for sections
 * - Live region announcements for data loading
 */
export default function Dashboard() {
  const announce = useAnnouncer();

  // Fetch tools count
  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ['tools', 'stats'],
    queryFn: () => apiClient.tools.list({ limit: 1 }),
  });

  // Fetch deployments count
  const { data: deploymentsData, isLoading: deploymentsLoading } = useQuery({
    queryKey: ['deployments', 'stats'],
    queryFn: () => apiClient.deployments.list({ limit: 1 }),
  });

  // Fetch documents count
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: () => apiClient.knowledge.listDocuments({ limit: 1 }),
  });

  // Calculate running deployments
  const runningDeployments = deploymentsData?.filter((d) => d.status === 'RUNNING').length || 0;

  const isLoading = toolsLoading || deploymentsLoading || documentsLoading;

  // Announce when data is loaded - Requirement 10.5
  useEffect(() => {
    if (!isLoading && toolsData && deploymentsData && documentsData) {
      announce('仪表板数据已加载');
    }
  }, [isLoading, toolsData, deploymentsData, documentsData, announce]);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <header>
        <h1 className="text-3xl font-bold mb-2">仪表板</h1>
        <p className="text-muted-foreground">欢迎回到 MCP 平台</p>
      </header>

      {/* Stats Cards - Requirement 7.1 */}
      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">统计概览</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {isLoading ? (
            <>
              <Skeleton className="h-32" aria-label="加载中" />
              <Skeleton className="h-32" aria-label="加载中" />
              <Skeleton className="h-32" aria-label="加载中" />
              <Skeleton className="h-32" aria-label="加载中" />
            </>
          ) : (
            <>
              <StatsCard
                title="MCP 工具"
                value={toolsData?.total || 0}
                icon={Package}
                description="总工具数"
              />
              <StatsCard
                title="活跃部署"
                value={runningDeployments}
                icon={Rocket}
                description="运行中的部署"
              />
              <StatsCard
                title="知识库文档"
                value={documentsData?.total || 0}
                icon={Database}
                description="总文档数"
              />
              <StatsCard
                title="总部署"
                value={deploymentsData?.length || 0}
                icon={Activity}
                description="所有部署"
              />
            </>
          )}
        </div>
      </section>

      {/* Metrics Chart - Requirement 7.5 */}
      <section aria-labelledby="metrics-heading">
        <h2 id="metrics-heading" className="sr-only">性能指标</h2>
        <MetricsChart />
      </section>

      {/* Activity Timeline and Health Status - Requirements 7.2, 7.3, 7.4 */}
      <div className="grid gap-4 md:grid-cols-2">
        <section aria-labelledby="activity-heading">
          <h2 id="activity-heading" className="sr-only">最近活动</h2>
          <ActivityTimeline />
        </section>
        <section aria-labelledby="health-heading">
          <h2 id="health-heading" className="sr-only">系统健康状态</h2>
          <HealthStatus />
        </section>
      </div>
    </div>
  );
}
