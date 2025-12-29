import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/services/apiClient';
import { TaskProgress } from './TaskProgress';
import { Download, Plus, Loader2 } from 'lucide-react';

/**
 * ConfigGenerator Component
 * Generates MCP tool configurations from requirements using AI
 * Provides options to download the generated config or create a tool directly
 */
export function ConfigGenerator() {
  const [requirements, setRequirements] = useState('{\n  "purpose": "数据处理工具",\n  "features": ["数据验证", "格式转换"]\n}');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [generatedConfig, setGeneratedConfig] = useState<Record<string, any> | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  const generateMutation = useMutation({
    mutationFn: async (requirementsData: Record<string, any>) => {
      return apiClient.analysis.generateConfig(requirementsData);
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
      toast({
        title: '生成已提交',
        description: `任务 ID: ${data.task_id}`,
      });
    },
    onError: (error: any) => {
      toast({
        title: '提交失败',
        description: error.response?.data?.detail || '无法提交配置生成',
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = () => {
    try {
      const requirementsData = JSON.parse(requirements);
      generateMutation.mutate(requirementsData);
    } catch (error) {
      toast({
        title: '需求格式错误',
        description: '请输入有效的 JSON 格式需求',
        variant: 'destructive',
      });
    }
  };

  const handleReset = () => {
    setTaskId(null);
    setGeneratedConfig(null);
    setRequirements('{\n  "purpose": "数据处理工具",\n  "features": ["数据验证", "格式转换"]\n}');
  };

  const handleTaskComplete = (result: any) => {
    if (result?.config) {
      setGeneratedConfig(result.config);
    }
  };

  const handleDownload = () => {
    if (!generatedConfig) return;

    const blob = new Blob([JSON.stringify(generatedConfig, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'generated-config.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: '下载成功',
      description: '配置文件已下载',
    });
  };

  const handleCreateTool = () => {
    if (!generatedConfig) return;

    // Navigate to tool creation form with pre-filled config
    navigate('/tools/new', { state: { config: generatedConfig } });
  };

  return (
    <div className="space-y-6">
      {!taskId ? (
        <>
          <div className="space-y-2">
            <Label htmlFor="requirements">需求描述 (JSON)</Label>
            <Textarea
              id="requirements"
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="输入工具需求..."
              className="font-mono min-h-[300px]"
            />
            <p className="text-sm text-muted-foreground">
              描述您想要创建的工具需求（JSON 格式）
            </p>
          </div>

          <Button
            onClick={handleSubmit}
            disabled={generateMutation.isPending || !requirements.trim()}
            className="w-full"
          >
            {generateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            生成配置
          </Button>
        </>
      ) : (
        <div className="space-y-4">
          <TaskProgress taskId={taskId} onComplete={handleTaskComplete} />

          {generatedConfig && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>生成的配置</Label>
                <Textarea
                  value={JSON.stringify(generatedConfig, null, 2)}
                  readOnly
                  className="font-mono min-h-[300px]"
                />
              </div>

              <div className="flex gap-2">
                <Button onClick={handleDownload} variant="outline" className="flex-1">
                  <Download className="mr-2 h-4 w-4" />
                  下载配置
                </Button>
                <Button onClick={handleCreateTool} className="flex-1">
                  <Plus className="mr-2 h-4 w-4" />
                  创建工具
                </Button>
              </div>
            </div>
          )}

          <Button onClick={handleReset} variant="outline" className="w-full">
            生成新配置
          </Button>
        </div>
      )}
    </div>
  );
}
