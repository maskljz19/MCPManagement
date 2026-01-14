import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Filter,
  Calendar,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import apiClient from '@/services/apiClient';
import type { ExecutionLog } from '@/types';

interface ExecutionHistoryProps {
  toolId: string;
  toolName: string;
}

/**
 * ExecutionHistory component for displaying tool execution history
 * 
 * Features:
 * - Fetch and display execution history
 * - Show execution time, status, duration, result summary
 * - Implement pagination for > 10 entries
 * - Add filtering by status and date range
 * - Implement detail view on click
 * 
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
 */
export default function ExecutionHistory({
  toolId,
  toolName,
}: ExecutionHistoryProps) {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [selectedExecution, setSelectedExecution] = useState<ExecutionLog | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const itemsPerPage = 10;

  // Fetch execution history
  const { data: executions = [], isLoading, error, refetch } = useQuery({
    queryKey: ['execution-history', toolId],
    queryFn: () => apiClient.tools.getExecutionHistory(toolId, 200),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Filter executions based on status and date range
  const filteredExecutions = executions.filter((execution) => {
    // Status filter
    if (statusFilter !== 'all' && execution.status !== statusFilter) {
      return false;
    }

    // Date range filter
    if (startDate) {
      const executionDate = new Date(execution.start_time);
      const filterStartDate = new Date(startDate);
      if (executionDate < filterStartDate) {
        return false;
      }
    }

    if (endDate) {
      const executionDate = new Date(execution.start_time);
      const filterEndDate = new Date(endDate);
      filterEndDate.setHours(23, 59, 59, 999); // End of day
      if (executionDate > filterEndDate) {
        return false;
      }
    }

    return true;
  });

  // Pagination
  const totalPages = Math.ceil(filteredExecutions.length / itemsPerPage);
  const startIndex = (page - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedExecutions = filteredExecutions.slice(startIndex, endIndex);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [statusFilter, startDate, endDate]);

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'error':
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusLower = status.toLowerCase();
    const variant =
      statusLower === 'success'
        ? 'default'
        : statusLower === 'error' || statusLower === 'failed'
        ? 'destructive'
        : 'secondary';

    return (
      <Badge variant={variant} className="flex items-center gap-1">
        {getStatusIcon(status)}
        {status}
      </Badge>
    );
  };

  const formatDuration = (durationMs: number) => {
    if (durationMs < 1000) {
      return `${durationMs}ms`;
    }
    const seconds = (durationMs / 1000).toFixed(2);
    return `${seconds}s`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getResultSummary = (execution: ExecutionLog) => {
    if (execution.error) {
      return execution.error.substring(0, 100) + (execution.error.length > 100 ? '...' : '');
    }

    if (execution.result) {
      const resultStr = JSON.stringify(execution.result);
      return resultStr.substring(0, 100) + (resultStr.length > 100 ? '...' : '');
    }

    return 'No result';
  };

  const handleRowClick = (execution: ExecutionLog) => {
    setSelectedExecution(execution);
    setIsDetailOpen(true);
  };

  const handleClearFilters = () => {
    setStatusFilter('all');
    setStartDate('');
    setEndDate('');
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>执行历史</CardTitle>
          <CardDescription>加载中...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>执行历史</CardTitle>
          <CardDescription>加载失败</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-red-500">
            无法加载执行历史。请稍后重试。
          </div>
          <Button onClick={() => refetch()} className="mt-4" variant="outline">
            重试
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>执行历史</CardTitle>
              <CardDescription>
                {toolName} 的最近执行记录 ({filteredExecutions.length} 条)
              </CardDescription>
            </div>
            <Button onClick={() => refetch()} variant="outline" size="sm">
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="status-filter" className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                状态筛选
              </Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger id="status-filter">
                  <SelectValue placeholder="选择状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="success">成功</SelectItem>
                  <SelectItem value="error">错误</SelectItem>
                  <SelectItem value="failed">失败</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="start-date" className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                开始日期
              </Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="end-date" className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                结束日期
              </Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

            <div className="flex items-end">
              <Button
                onClick={handleClearFilters}
                variant="outline"
                className="w-full"
              >
                清除筛选
              </Button>
            </div>
          </div>

          {/* Execution Table */}
          {paginatedExecutions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {executions.length === 0
                ? '暂无执行记录'
                : '没有符合筛选条件的记录'}
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>执行时间</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>持续时间</TableHead>
                      <TableHead>结果摘要</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedExecutions.map((execution) => (
                      <TableRow
                        key={execution.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => handleRowClick(execution)}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                            {formatDate(execution.start_time)}
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(execution.status)}</TableCell>
                        <TableCell>{formatDuration(execution.duration_ms)}</TableCell>
                        <TableCell className="max-w-md truncate">
                          {getResultSummary(execution)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    显示 {startIndex + 1} - {Math.min(endIndex, filteredExecutions.length)} 条，
                    共 {filteredExecutions.length} 条
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      上一页
                    </Button>
                    <div className="text-sm">
                      第 {page} / {totalPages} 页
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      下一页
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>执行详情</DialogTitle>
            <DialogDescription>
              执行 ID: {selectedExecution?.id}
            </DialogDescription>
          </DialogHeader>

          {selectedExecution && (
            <div className="space-y-4">
              {/* Status and Timing */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">状态</Label>
                  <div className="mt-1">{getStatusBadge(selectedExecution.status)}</div>
                </div>
                <div>
                  <Label className="text-muted-foreground">持续时间</Label>
                  <div className="mt-1 font-mono">
                    {formatDuration(selectedExecution.duration_ms)}
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground">开始时间</Label>
                  <div className="mt-1 text-sm">
                    {formatDate(selectedExecution.start_time)}
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground">结束时间</Label>
                  <div className="mt-1 text-sm">
                    {formatDate(selectedExecution.end_time)}
                  </div>
                </div>
              </div>

              {/* Arguments */}
              <div>
                <Label className="text-muted-foreground">参数</Label>
                <div className="mt-1 bg-muted p-3 rounded-lg overflow-auto max-h-[200px]">
                  <pre className="text-sm font-mono whitespace-pre-wrap">
                    {JSON.stringify(selectedExecution.arguments, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Error */}
              {selectedExecution.error && (
                <div>
                  <Label className="text-muted-foreground text-red-500">错误信息</Label>
                  <div className="mt-1 bg-red-50 dark:bg-red-950 p-3 rounded-lg">
                    <pre className="text-sm font-mono whitespace-pre-wrap text-red-700 dark:text-red-300">
                      {selectedExecution.error}
                    </pre>
                  </div>
                </div>
              )}

              {/* Result */}
              {selectedExecution.result && (
                <div>
                  <Label className="text-muted-foreground">执行结果</Label>
                  <div className="mt-1 bg-muted p-3 rounded-lg overflow-auto max-h-[300px]">
                    <pre className="text-sm font-mono whitespace-pre-wrap">
                      {JSON.stringify(selectedExecution.result, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <Label className="text-muted-foreground">工具 ID</Label>
                  <div className="mt-1 text-sm font-mono break-all">
                    {selectedExecution.tool_id}
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground">用户 ID</Label>
                  <div className="mt-1 text-sm font-mono break-all">
                    {selectedExecution.user_id}
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
