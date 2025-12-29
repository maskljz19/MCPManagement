import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
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
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';

interface DisconnectDialogProps {
  connectionId: string | null;
  repositoryUrl?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * DisconnectDialog - Confirmation dialog for disconnecting GitHub repository
 * Provides confirmation and handles disconnection logic
 * Validates: Requirements 5.6
 */
export function DisconnectDialog({
  connectionId,
  repositoryUrl,
  open,
  onOpenChange,
}: DisconnectDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Mutation for disconnecting repository
  const disconnectMutation = useMutation({
    mutationFn: (id: string) => apiClient.github.disconnect(id),
    onSuccess: () => {
      toast({
        title: '断开成功',
        description: 'GitHub 仓库连接已断开',
      });
      queryClient.invalidateQueries({ queryKey: ['github-connections'] });
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast({
        title: '断开失败',
        description: error.message || '无法断开 GitHub 连接',
        variant: 'destructive',
      });
    },
  });

  const handleDisconnect = () => {
    if (connectionId) {
      disconnectMutation.mutate(connectionId);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认断开连接</AlertDialogTitle>
          <AlertDialogDescription>
            您确定要断开与以下 GitHub 仓库的连接吗?
            {repositoryUrl && (
              <span className="block mt-2 font-medium text-foreground">{repositoryUrl}</span>
            )}
            <span className="block mt-2">
              断开后,将不再自动同步该仓库的配置。您可以随时重新连接。
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={disconnectMutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDisconnect}
            disabled={disconnectMutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {disconnectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            断开连接
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
