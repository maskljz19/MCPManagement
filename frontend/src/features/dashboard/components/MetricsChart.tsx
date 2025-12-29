import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp } from 'lucide-react';
import { useState } from 'react';
import apiClient from '@/services/apiClient';
import { format, subDays } from 'date-fns';
import { zhCN } from 'date-fns/locale';

type MetricType = 'deployments' | 'tools' | 'documents';
type TimeRange = '7d' | '30d' | '90d';

interface MetricData {
  date: string;
  value: number;
}

export default function MetricsChart() {
  const [metricType, setMetricType] = useState<MetricType>('deployments');
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');

  // In a real application, this would fetch actual metrics data from the backend
  // For now, we'll generate mock data based on current data
  const { data: deploymentsData } = useQuery({
    queryKey: ['deployments', 'all'],
    queryFn: () => apiClient.deployments.list(),
    enabled: metricType === 'deployments',
  });

  const { data: toolsData } = useQuery({
    queryKey: ['tools', 'all'],
    queryFn: () => apiClient.tools.list({ limit: 100 }),
    enabled: metricType === 'tools',
  });

  const { data: documentsData } = useQuery({
    queryKey: ['documents', 'all'],
    queryFn: () => apiClient.knowledge.listDocuments({ limit: 100 }),
    enabled: metricType === 'documents',
  });

  // Generate chart data based on time range
  const generateChartData = (): MetricData[] => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const data: MetricData[] = [];

    for (let i = days - 1; i >= 0; i--) {
      const date = subDays(new Date(), i);
      const dateStr = format(date, 'MM/dd', { locale: zhCN });

      let value = 0;

      // Calculate cumulative count up to this date
      if (metricType === 'deployments' && deploymentsData) {
        value = deploymentsData.filter(
          (d) => new Date(d.deployed_at) <= date
        ).length;
      } else if (metricType === 'tools' && toolsData) {
        value = toolsData.items.filter(
          (t) => new Date(t.created_at) <= date
        ).length;
      } else if (metricType === 'documents' && documentsData) {
        value = documentsData.items.filter(
          (d) => new Date(d.created_at) <= date
        ).length;
      }

      data.push({ date: dateStr, value });
    }

    return data;
  };

  const chartData = generateChartData();
  const isLoading = !deploymentsData && !toolsData && !documentsData;

  const getMetricLabel = () => {
    switch (metricType) {
      case 'deployments':
        return '部署数量';
      case 'tools':
        return '工具数量';
      case 'documents':
        return '文档数量';
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            指标趋势
          </CardTitle>
          <div className="flex gap-2">
            <Select value={metricType} onValueChange={(value) => setMetricType(value as MetricType)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="deployments">部署</SelectItem>
                <SelectItem value="tools">工具</SelectItem>
                <SelectItem value="documents">文档</SelectItem>
              </SelectContent>
            </Select>
            <Select value={timeRange} onValueChange={(value) => setTimeRange(value as TimeRange)}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">7天</SelectItem>
                <SelectItem value="30d">30天</SelectItem>
                <SelectItem value="90d">90天</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-[300px] w-full" />
        ) : chartData.length === 0 || chartData.every((d) => d.value === 0) ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>暂无数据</p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="value"
                name={getMetricLabel()}
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
