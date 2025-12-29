import { useMutation } from '@tanstack/react-query';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { apiClient } from '@/services/apiClient';
import { useToast } from '@/hooks/use-toast';

interface RevokeAPIKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  keyId: string;
  onSuccess: () => void;
}

/**
 * RevokeAPIKeyDialog - Confirmation dialog for revoking API keys
 * Shows warning and confirms before revoking
 * Validates: Requirements 9.4
 */
export function RevokeAPIKeyDialog({
  open,
  onOpenChange,
  keyId,
  onSuccess,
}: RevokeAPIKeyDialogProps) {
  const { toast } = useToast();

  // Revoke API key mutation
  const revokeMutation = useMutation({
    mutationFn: () => apiClient.apiKeys.revoke(keyId),
    onSuccess: () => {
      toast({
        title: '成功',
        description: 'API 密钥已撤销',
      });
      onSuccess();
    },
    onError: (error: Error) => {
      toast({
        title: '错误',
        description: `撤销 API 密钥失败: ${error.message}`,
        variant: 'destructive',
      });
    },
  });

  const handleRevoke = () => {
    revokeMutation.mutate();
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认撤销 API 密钥</AlertDialogTitle>
          <AlertDialogDescription>
            此操作无法撤销。撤销后,使用此密钥的所有 API 请求都将失败。
            <br />
            <br />
            您确定要撤销此 API 密钥吗?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={revokeMutation.isPending}>
            取消
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleRevoke}
            disabled={revokeMutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {revokeMutation.isPending ? '撤销中...' : '撤销密钥'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
