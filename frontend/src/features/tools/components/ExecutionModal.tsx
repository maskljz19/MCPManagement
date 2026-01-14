import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Download, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
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
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/services/apiClient';

interface ExecutionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  toolId: string;
  toolName: string;
  toolConfig?: Record<string, any>;
}

// Schema for parameter validation
const executionSchema = z.object({
  arguments: z.string().refine(
    (val) => {
      if (!val.trim()) return true; // Empty is valid (will use {})
      try {
        JSON.parse(val);
        return true;
      } catch {
        return false;
      }
    },
    { message: 'Arguments must be valid JSON' }
  ),
  timeout: z.number().min(1).max(300),
});

type ExecutionFormData = z.infer<typeof executionSchema>;

interface ExecutionResult {
  execution_id: string;
  tool_id: string;
  tool_name: string;
  status: string;
  result: Record<string, any>;
  executed_at: string;
}

/**
 * ExecutionModal component for MCP tool execution
 * 
 * Features:
 * - Parameter input form with JSON validation
 * - Execution submission with loading states
 * - Real-time execution progress display
 * - Results display with formatted output
 * - Download options for results (JSON)
 * - Error handling and display
 * 
 * Requirements: 1.2, 1.3, 1.4, 1.5
 */
export default function ExecutionModal({
  open,
  onOpenChange,
  toolId,
  toolName,
  toolConfig,
}: ExecutionModalProps) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<ExecutionFormData>({
    resolver: zodResolver(executionSchema),
    defaultValues: {
      arguments: '{}',
      timeout: 30,
    },
  });

  // Reset form and state when modal opens/closes
  useEffect(() => {
    if (!open) {
      reset();
      setExecutionResult(null);
      setExecutionError(null);
      setProgress(0);
    } else {
      // Pre-fill with default arguments from tool config if available
      if (toolConfig?.default_arguments) {
        setValue('arguments', JSON.stringify(toolConfig.default_arguments, null, 2));
      }
    }
  }, [open, reset, setValue, toolConfig]);

  // Simulate progress during execution
  useEffect(() => {
    if (isExecuting && progress < 90) {
      const timer = setTimeout(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isExecuting, progress]);

  const onSubmit = async (data: ExecutionFormData) => {
    setIsExecuting(true);
    setExecutionError(null);
    setProgress(10);

    try {
      // Parse arguments
      const parsedArguments = data.arguments.trim()
        ? JSON.parse(data.arguments)
        : {};

      // Execute the tool
      const response = await apiClient.tools.execute(toolId, {
        tool_name: toolName,
        arguments: parsedArguments,
        timeout: data.timeout,
      });

      setProgress(100);
      setExecutionResult(response);
    } catch (error: any) {
      console.error('Execution error:', error);
      setExecutionError(
        error.response?.data?.detail ||
        error.message ||
        'An unexpected error occurred during execution'
      );
    } finally {
      setIsExecuting(false);
    }
  };

  const handleDownloadResult = () => {
    if (!executionResult) return;

    const dataStr = JSON.stringify(executionResult, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `execution-${executionResult.execution_id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadResultText = () => {
    if (!executionResult) return;

    const dataStr = JSON.stringify(executionResult.result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'text/plain' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `result-${executionResult.execution_id}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getStatusIcon = () => {
    if (!executionResult) return null;

    switch (executionResult.status) {
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>执行工具: {toolName}</DialogTitle>
          <DialogDescription>
            配置参数并执行 MCP 工具
          </DialogDescription>
        </DialogHeader>

        {!executionResult && !executionError && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="arguments">
                参数 (JSON 格式)
              </Label>
              <Textarea
                id="arguments"
                placeholder='{"key": "value"}'
                className="font-mono text-sm min-h-[120px]"
                {...register('arguments')}
                disabled={isExecuting}
              />
              {errors.arguments && (
                <p className="text-sm text-red-500">{errors.arguments.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                输入 JSON 格式的参数。留空使用默认参数 {'{}'}.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeout">
                超时时间 (秒)
              </Label>
              <Input
                id="timeout"
                type="number"
                min={1}
                max={300}
                {...register('timeout', { valueAsNumber: true })}
                disabled={isExecuting}
              />
              {errors.timeout && (
                <p className="text-sm text-red-500">{errors.timeout.message}</p>
              )}
            </div>

            {isExecuting && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">执行中...</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isExecuting}
              >
                取消
              </Button>
              <Button type="submit" disabled={isExecuting}>
                {isExecuting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    执行中...
                  </>
                ) : (
                  '执行'
                )}
              </Button>
            </DialogFooter>
          </form>
        )}

        {executionError && (
          <div className="space-y-4">
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-1">执行失败</div>
                <div className="text-sm">{executionError}</div>
              </AlertDescription>
            </Alert>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setExecutionError(null);
                  setProgress(0);
                }}
              >
                重试
              </Button>
              <Button onClick={() => onOpenChange(false)}>
                关闭
              </Button>
            </DialogFooter>
          </div>
        )}

        {executionResult && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
              {getStatusIcon()}
              <div className="flex-1">
                <div className="font-semibold">
                  执行 {executionResult.status === 'success' ? '成功' : '完成'}
                </div>
                <div className="text-sm text-muted-foreground">
                  执行 ID: {executionResult.execution_id}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>执行结果</Label>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleDownloadResultText}
                  >
                    <Download className="mr-2 h-3 w-3" />
                    下载结果
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleDownloadResult}
                  >
                    <Download className="mr-2 h-3 w-3" />
                    下载完整数据
                  </Button>
                </div>
              </div>
              <div className="bg-muted p-4 rounded-lg overflow-auto max-h-[300px]">
                <pre className="text-sm font-mono whitespace-pre-wrap">
                  {JSON.stringify(executionResult.result, null, 2)}
                </pre>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">工具 ID:</span>
                <div className="font-mono text-xs mt-1">{executionResult.tool_id}</div>
              </div>
              <div>
                <span className="text-muted-foreground">执行时间:</span>
                <div className="mt-1">
                  {new Date(executionResult.executed_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setExecutionResult(null);
                  setProgress(0);
                }}
              >
                再次执行
              </Button>
              <Button onClick={() => onOpenChange(false)}>
                关闭
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
