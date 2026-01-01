import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { useDebounce } from '@/hooks/useDebounce';
import { usePermissions } from '@/hooks/usePermissions';
import ToolCard from './components/ToolCard';

/**
 * ToolList - Optimized with useCallback, useMemo, and debounced search
 * Prevents unnecessary re-renders and function recreations
 * Uses debounced search to reduce API calls
 */
export default function ToolList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { canCreate, canRead } = usePermissions();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const limit = 12;

  // Debounce search to reduce API calls (waits 500ms after user stops typing)
  const debouncedSearch = useDebounce(search, 500);

  // Fetch tools with pagination and filters - only if user has read permission
  const { data, isLoading, error } = useQuery({
    queryKey: ['tools', page, debouncedSearch, statusFilter],
    queryFn: async () => {
      const params: any = {
        page,
        limit,
      };

      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      return apiClient.tools.list(params);
    },
    enabled: canRead('mcps'), // Only fetch if user has read permission
  });

  // Show error toast if query fails - use useEffect to prevent infinite loop
  useEffect(() => {
    if (error) {
      toast({
        title: '加载失败',
        description: '无法加载工具列表，请稍后重试。',
        variant: 'destructive',
      });
    }
  }, [error, toast]);

  // Memoize handlers to prevent recreation on every render
  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    setPage(1); // Reset to first page on search
  }, []);

  const handleStatusChange = useCallback((value: string) => {
    setStatusFilter(value);
    setPage(1); // Reset to first page on filter change
  }, []);

  const handleToolClick = useCallback((id: string) => {
    navigate(`/tools/${id}`);
  }, [navigate]);

  const handleCreateTool = useCallback(() => {
    navigate('/tools/new');
  }, [navigate]);

  const handlePrevPage = useCallback(() => {
    setPage((p) => Math.max(1, p - 1));
  }, []);

  const handleNextPage = useCallback(() => {
    setPage((p) => (data ? Math.min(data.pages, p + 1) : p));
  }, [data]);

  // Memoize skeleton array to prevent recreation
  const skeletonArray = useMemo(() => Array.from({ length: 6 }), []);

  // Show permission denied message if user doesn't have read access
  if (!canRead('mcps')) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">MCP 工具</h1>
          <p className="text-muted-foreground mt-1">
            管理和浏览您的 MCP 工具集合
          </p>
        </div>
        <div className="text-center py-12">
          <p className="text-muted-foreground">您没有权限访问此功能</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">MCP 工具</h1>
          <p className="text-muted-foreground mt-1">
            管理和浏览您的 MCP 工具集合
          </p>
        </div>
        {canCreate('mcps') && (
          <Button onClick={handleCreateTool}>
            <Plus className="mr-2 h-4 w-4" />
            创建工具
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索工具名称、描述或 slug..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="draft">草稿</SelectItem>
            <SelectItem value="active">活跃</SelectItem>
            <SelectItem value="deprecated">已弃用</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tool Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {skeletonArray.map((_, i) => (
            <Skeleton key={i} className="h-[200px] rounded-lg" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.items.map((tool) => (
              <ToolCard
                key={tool.id}
                tool={tool}
                onClick={() => handleToolClick(tool.id)}
              />
            ))}
          </div>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                onClick={handlePrevPage}
                disabled={page === 1}
              >
                上一页
              </Button>
              <span className="text-sm text-muted-foreground">
                第 {page} 页，共 {data.pages} 页
              </span>
              <Button
                variant="outline"
                onClick={handleNextPage}
                disabled={page === data.pages}
              >
                下一页
              </Button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground">
            {search || statusFilter !== 'all'
              ? '没有找到匹配的工具'
              : '还没有工具，创建第一个吧！'}
          </p>
        </div>
      )}
    </div>
  );
}
