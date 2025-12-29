import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { Loader2, AlertCircle } from 'lucide-react';
import type { ConnectionData } from '@/types';

// Form validation schema
const connectFormSchema = z.object({
  repository_url: z
    .string()
    .min(1, '仓库 URL 不能为空')
    .url('请输入有效的 URL')
    .refine(
      (url) => url.includes('github.com'),
      '必须是 GitHub 仓库 URL'
    ),
  access_token: z
    .string()
    .min(1, '访问令牌不能为空')
    .min(20, '访问令牌格式不正确'),
  tool_id: z.string().optional(),
});

type ConnectFormData = z.infer<typeof connectFormSchema>;

interface GitHubConnectFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * GitHubConnectForm - Form to connect a GitHub repository
 * Provides form validation and submission for creating GitHub connections
 * Validates: Requirements 5.2, 5.3
 */
export function GitHubConnectForm({ open, onOpenChange, onSuccess }: GitHubConnectFormProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  // Fetch available tools for selection
  const { data: toolsData } = useQuery({
    queryKey: ['tools', { limit: 100 }],
    queryFn: () => apiClient.tools.list({ limit: 100 }),
    enabled: open,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<ConnectFormData>({
    resolver: zodResolver(connectFormSchema),
  });

  const selectedToolId = watch('tool_id');

  // Mutation for creating connection
  const connectMutation = useMutation({
    mutationFn: (data: ConnectionData) => apiClient.github.connect(data),
    onSuccess: () => {
      toast({
        title: '连接成功',
        description: 'GitHub 仓库已成功连接',
      });
      queryClient.invalidateQueries({ queryKey: ['github-connections'] });
      reset();
      setError(null);
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (err: Error) => {
      setError(err.message || '连接失败,请检查您的仓库 URL 和访问令牌');
    },
  });

  const onSubmit = (data: ConnectFormData) => {
    setError(null);
    connectMutation.mutate({
      repository_url: data.repository_url,
      access_token: data.access_token,
      tool_id: data.tool_id || undefined,
    });
  };

  const handleClose = () => {
    if (!connectMutation.isPending) {
      reset();
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>连接 GitHub 仓库</DialogTitle>
          <DialogDescription>
            连接您的 GitHub 仓库以自动同步 MCP 工具配置。您需要提供仓库 URL 和具有读取权限的访问令牌。
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Repository URL */}
          <div className="space-y-2">
            <Label htmlFor="repository_url">
              仓库 URL <span className="text-destructive">*</span>
            </Label>
            <Input
              id="repository_url"
              placeholder="https://github.com/username/repository"
              {...register('repository_url')}
              disabled={connectMutation.isPending}
            />
            {errors.repository_url && (
              <p className="text-sm text-destructive">{errors.repository_url.message}</p>
            )}
          </div>

          {/* Access Token */}
          <div className="space-y-2">
            <Label htmlFor="access_token">
              访问令牌 <span className="text-destructive">*</span>
            </Label>
            <Input
              id="access_token"
              type="password"
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              {...register('access_token')}
              disabled={connectMutation.isPending}
            />
            {errors.access_token && (
              <p className="text-sm text-destructive">{errors.access_token.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              在 GitHub Settings → Developer settings → Personal access tokens 中创建令牌
            </p>
          </div>

          {/* Tool Selection (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="tool_id">关联工具 (可选)</Label>
            <Select
              value={selectedToolId || ''}
              onValueChange={(value) => setValue('tool_id', value || undefined)}
              disabled={connectMutation.isPending}
            >
              <SelectTrigger id="tool_id">
                <SelectValue placeholder="选择要关联的工具" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">不关联工具</SelectItem>
                {toolsData?.items.map((tool) => (
                  <SelectItem key={tool.id} value={tool.id}>
                    {tool.name} ({tool.slug})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              选择一个现有工具以将仓库配置同步到该工具
            </p>
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={connectMutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={connectMutation.isPending}>
              {connectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              连接
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
