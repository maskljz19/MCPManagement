import { Loader2, AlertTriangle } from 'lucide-react';
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
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/apiClient';

interface DeleteDocumentDialogProps {
  documentId: string | null;
  documentTitle?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function DeleteDocumentDialog({
  documentId,
  documentTitle,
  open,
  onOpenChange,
}: DeleteDocumentDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.knowledge.deleteDocument(id);
    },
    onSuccess: () => {
      toast({
        title: '删除成功',
        description: '文档已从知识库中删除',
      });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      onOpenChange(false);
    },
    onError: (error: any) => {
      toast({
        title: '删除失败',
        description: error.response?.data?.detail || '无法删除文档，请稍后重试',
        variant: 'destructive',
      });
    },
  });

  const handleDelete = () => {
    if (documentId) {
      deleteMutation.mutate(documentId);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            确认删除文档
          </AlertDialogTitle>
          <AlertDialogDescription>
            您确定要删除文档 {documentTitle ? `"${documentTitle}"` : '此文档'} 吗？
            此操作无法撤销。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteMutation.isPending}>
            取消
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleteMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                删除中...
              </>
            ) : (
              '删除'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
