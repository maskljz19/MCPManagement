import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useMutation } from '@tanstack/react-query';
import { Copy, Check, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient } from '@/services/apiClient';
import { useToast } from '@/hooks/use-toast';
import type { CreateKeyData, APIKeyResponse } from '@/types';

// Form validation schema
const createKeySchema = z.object({
  name: z.string().min(1, '请输入密钥名称').max(100, '名称不能超过100个字符'),
  expires_at: z.string().optional(),
});

type CreateKeyFormData = z.infer<typeof createKeySchema>;

interface CreateAPIKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

/**
 * CreateAPIKeyDialog - Dialog for creating new API keys
 * Shows the key value once after creation with copy functionality
 * Validates: Requirements 9.2, 9.3
 */
export function CreateAPIKeyDialog({ open, onOpenChange, onSuccess }: CreateAPIKeyDialogProps) {
  const [createdKey, setCreatedKey] = useState<APIKeyResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CreateKeyFormData>({
    resolver: zodResolver(createKeySchema),
  });

  // Create API key mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateKeyData) => apiClient.apiKeys.create(data),
    onSuccess: (data) => {
      setCreatedKey(data);
      toast({
        title: '成功',
        description: 'API 密钥已创建',
      });
    },
    onError: (error: Error) => {
      toast({
        title: '错误',
        description: `创建 API 密钥失败: ${error.message}`,
        variant: 'destructive',
      });
    },
  });

  const onSubmit = (data: CreateKeyFormData) => {
    const createData: CreateKeyData = {
      name: data.name,
    };

    if (data.expires_at) {
      createData.expires_at = data.expires_at;
    }

    createMutation.mutate(createData);
  };

  const handleCopy = async () => {
    if (createdKey) {
      try {
        await navigator.clipboard.writeText(createdKey.key);
        setCopied(true);
        toast({
          title: '已复制',
          description: 'API 密钥已复制到剪贴板',
        });
        setTimeout(() => setCopied(false), 2000);
      } catch (error) {
        toast({
          title: '错误',
          description: '复制失败,请手动复制',
          variant: 'destructive',
        });
      }
    }
  };

  const handleClose = () => {
    if (createdKey) {
      onSuccess();
      setCreatedKey(null);
      reset();
    } else {
      onOpenChange(false);
      reset();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        {!createdKey ? (
          <>
            <DialogHeader>
              <DialogTitle>创建 API 密钥</DialogTitle>
              <DialogDescription>
                创建一个新的 API 密钥用于程序化访问平台
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">密钥名称 *</Label>
                <Input
                  id="name"
                  placeholder="例如: 生产环境密钥"
                  {...register('name')}
                  disabled={createMutation.isPending}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="expires_at">过期时间 (可选)</Label>
                <Input
                  id="expires_at"
                  type="datetime-local"
                  {...register('expires_at')}
                  disabled={createMutation.isPending}
                />
                <p className="text-xs text-muted-foreground">
                  留空表示永不过期
                </p>
                {errors.expires_at && (
                  <p className="text-sm text-destructive">{errors.expires_at.message}</p>
                )}
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={createMutation.isPending}
                >
                  取消
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? '创建中...' : '创建密钥'}
                </Button>
              </div>
            </form>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>API 密钥已创建</DialogTitle>
              <DialogDescription>
                请立即复制您的 API 密钥。出于安全考虑,此密钥只会显示一次。
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>重要:</strong> 请妥善保管此密钥。关闭此对话框后,您将无法再次查看完整的密钥值。
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label>密钥名称</Label>
                <Input value={createdKey.name} readOnly />
              </div>

              <div className="space-y-2">
                <Label>API 密钥</Label>
                <div className="flex space-x-2">
                  <Input
                    value={createdKey.key}
                    readOnly
                    className="font-mono text-sm"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleCopy}
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <Button onClick={handleClose}>
                  我已保存密钥
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
