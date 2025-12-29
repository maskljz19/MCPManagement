import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/services/apiClient';
import { TaskProgress } from './TaskProgress';
import { Loader2 } from 'lucide-react';

/**
 * FeasibilityAnalysis Component
 * Allows users to analyze the feasibility of an MCP tool configuration
 * Submits configuration for AI analysis and displays results
 */
export function FeasibilityAnalysis() {
  const [config, setConfig] = useState('{\n  "name": "example-tool",\n  "version": "1.0.0"\n}');
  const [taskId, setTaskId] = useState<string | null>(null);
  const { toast } = useToast();

  const analyzeMutation = useMutation({
    mutationFn: async (configData: Record<string, any>) => {
      return apiClient.analysis.analyzeFeasibility(configData);
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
      toast({
        title: '分析已提交',
        description: `任务 ID: ${data.task_id}`,
      });
    },
    onError: (error: any) => {
      toast({
        title: '提交失败',
        description: error.response?.data?.detail || '无法提交可行性分析',
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = () => {
    try {
      const configData = JSON.parse(config);
      analyzeMutation.mutate(configData);
    } catch (error) {
      toast({
        title: '配置格式错误',
        description: '请输入有效的 JSON 配置',
        variant: 'destructive',
      });
    }
  };

  const handleReset = () => {
    setTaskId(null);
    setConfig('{\n  "name": "example-tool",\n  "version": "1.0.0"\n}');
  };

  return (
    <div className="space-y-6">
      {!taskId ? (
        <>
          <div className="space-y-2">
            <Label htmlFor="config">工具配置 (JSON)</Label>
            <Textarea
              id="config"
              value={config}
              onChange={(e) => setConfig(e.target.value)}
              placeholder="输入 MCP 工具配置..."
              className="font-mono min-h-[300px]"
            />
            <p className="text-sm text-muted-foreground">
              输入要分析的 MCP 工具配置（JSON 格式）
            </p>
          </div>

          <Button
            onClick={handleSubmit}
            disabled={analyzeMutation.isPending || !config.trim()}
            className="w-full"
          >
            {analyzeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            开始分析
          </Button>
        </>
      ) : (
        <div className="space-y-4">
          <TaskProgress taskId={taskId} onComplete={handleReset} />
          <Button onClick={handleReset} variant="outline" className="w-full">
            开始新的分析
          </Button>
        </div>
      )}
    </div>
  );
}
