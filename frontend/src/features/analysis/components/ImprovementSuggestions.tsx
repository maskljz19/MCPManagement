import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/services/apiClient';
import { TaskProgress } from './TaskProgress';
import { Loader2 } from 'lucide-react';

/**
 * ImprovementSuggestions Component
 * Allows users to get AI-powered improvement suggestions for existing tools
 * Users can select a tool from their collection to analyze
 */
export function ImprovementSuggestions() {
  const [selectedToolId, setSelectedToolId] = useState<string>('');
  const [taskId, setTaskId] = useState<string | null>(null);
  const { toast } = useToast();

  // Fetch tools list
  const { data: toolsData, isLoading: isLoadingTools } = useQuery({
    queryKey: ['tools', 'list'],
    queryFn: () => apiClient.tools.list({ limit: 100 }),
  });

  const improvementMutation = useMutation({
    mutationFn: async (toolId: string) => {
      return apiClient.analysis.getImprovements(toolId);
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
        description: error.response?.data?.detail || '无法提交改进建议分析',
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = () => {
    if (!selectedToolId) {
      toast({
        title: '请选择工具',
        description: '请先选择要分析的工具',
        variant: 'destructive',
      });
      return;
    }
    improvementMutation.mutate(selectedToolId);
  };

  const handleReset = () => {
    setTaskId(null);
    setSelectedToolId('');
  };

  return (
    <div className="space-y-6">
      {!taskId ? (
        <>
          <div className="space-y-2">
            <Label htmlFor="tool-select">选择工具</Label>
            <Select value={selectedToolId} onValueChange={setSelectedToolId}>
              <SelectTrigger id="tool-select">
                <SelectValue placeholder="选择要分析的工具..." />
              </SelectTrigger>
              <SelectContent>
                {isLoadingTools ? (
                  <SelectItem value="loading" disabled>
                    加载中...
                  </SelectItem>
                ) : toolsData?.items && toolsData.items.length > 0 ? (
                  toolsData.items.map((tool) => (
                    <SelectItem key={tool.id} value={tool.id}>
                      {tool.name} (v{tool.version})
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="no-tools" disabled>
                    暂无可用工具
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              选择一个现有工具以获取改进建议
            </p>
          </div>

          <Button
            onClick={handleSubmit}
            disabled={improvementMutation.isPending || !selectedToolId || isLoadingTools}
            className="w-full"
          >
            {improvementMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            获取改进建议
          </Button>
        </>
      ) : (
        <div className="space-y-4">
          <TaskProgress taskId={taskId} onComplete={handleReset} />
          <Button onClick={handleReset} variant="outline" className="w-full">
            分析其他工具
          </Button>
        </div>
      )}
    </div>
  );
}
