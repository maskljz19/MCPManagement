import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertCircle } from 'lucide-react';
import type { DeploymentData } from '@/types';

const deploymentSchema = z.object({
  tool_id: z.string().min(1, '请选择一个工具'),
  config: z.string().optional(),
});

type DeploymentFormData = z.infer<typeof deploymentSchema>;

interface DeploymentFormProps {
  onSuccess: (deploymentId: string) => void;
  onCancel: () => void;
}

export function DeploymentForm({ onSuccess, onCancel }: DeploymentFormProps) {
  const [configError, setConfigError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<DeploymentFormData>({
    resolver: zodResolver(deploymentSchema),
  });

  const selectedToolId = watch('tool_id');

  // Fetch available tools
  const { data: toolsResponse, isLoading: isLoadingTools } = useQuery({
    queryKey: ['tools', { status: 'ACTIVE' }],
    queryFn: () => apiClient.tools.list({ status: 'ACTIVE' }),
  });

  // Create deployment mutation
  const createMutation = useMutation({
    mutationFn: (data: DeploymentData) => apiClient.deployments.create(data),
    onSuccess: (deployment) => {
      onSuccess(deployment.deployment_id);
    },
  });

  const onSubmit = (data: DeploymentFormData) => {
    setConfigError(null);

    // Parse config if provided
    let config: Record<string, any> | undefined;
    if (data.config && data.config.trim()) {
      try {
        config = JSON.parse(data.config);
      } catch (error) {
        setConfigError('配置必须是有效的 JSON 格式');
        return;
      }
    }

    const deploymentData: DeploymentData = {
      tool_id: data.tool_id,
      config,
    };

    createMutation.mutate(deploymentData);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>创建新部署</CardTitle>
        <CardDescription>选择一个工具并配置部署参数</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Tool Selection */}
          <div className="space-y-2">
            <Label htmlFor="tool_id">选择工具 *</Label>
            {isLoadingTools ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载工具列表...
              </div>
            ) : (
              <Select
                value={selectedToolId}
                onValueChange={(value) => setValue('tool_id', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择一个工具" />
                </SelectTrigger>
                <SelectContent>
                  {toolsResponse?.items.map((tool) => (
                    <SelectItem key={tool.id} value={tool.id}>
                      {tool.name} (v{tool.version})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {errors.tool_id && (
              <p className="text-sm text-destructive">{errors.tool_id.message}</p>
            )}
          </div>

          {/* Configuration (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="config">部署配置 (可选)</Label>
            <Textarea
              id="config"
              {...register('config')}
              placeholder='{"port": 8080, "env": "production"}'
              rows={8}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              可选的 JSON 配置，用于自定义部署参数
            </p>
            {configError && (
              <p className="text-sm text-destructive">{configError}</p>
            )}
          </div>

          {/* Error Alert */}
          {createMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {createMutation.error instanceof Error
                  ? createMutation.error.message
                  : '创建部署失败'}
              </AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onCancel}>
              取消
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              创建部署
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
