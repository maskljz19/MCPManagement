import { useQuery } from '@tanstack/react-query';
import { FileText, Calendar, Tag, Globe } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import apiClient from '@/services/apiClient';

interface DocumentViewerProps {
  documentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function DocumentViewer({
  documentId,
  open,
  onOpenChange,
}: DocumentViewerProps) {
  const { data: document, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => apiClient.knowledge.getDocument(documentId!),
    enabled: !!documentId && open,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : document ? (
          <>
            <DialogHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <DialogTitle className="text-2xl flex items-center gap-2">
                    <FileText className="h-6 w-6" />
                    {document.title}
                  </DialogTitle>
                  <DialogDescription className="mt-2">
                    创建于{' '}
                    {formatDistanceToNow(new Date(document.created_at), {
                      addSuffix: true,
                      locale: zhCN,
                    })}
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-6">
              {/* Metadata */}
              {document.metadata && Object.keys(document.metadata).length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-muted-foreground">
                    元数据
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {document.metadata.source && (
                      <div className="flex items-center gap-2 text-sm">
                        <Globe className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">来源:</span>
                        <span>{document.metadata.source}</span>
                      </div>
                    )}
                    {document.metadata.language && (
                      <div className="flex items-center gap-2 text-sm">
                        <Tag className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">语言:</span>
                        <span>{document.metadata.language}</span>
                      </div>
                    )}
                    {document.metadata.tags && document.metadata.tags.length > 0 && (
                      <div className="flex items-center gap-2 flex-wrap">
                        <Tag className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">标签:</span>
                        {document.metadata.tags.map((tag: string, index: number) => (
                          <Badge key={index} variant="secondary">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Content */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-muted-foreground">
                  内容
                </h3>
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {document.content}
                  </div>
                </div>
              </div>

              {/* Timestamps */}
              <div className="flex items-center gap-4 text-xs text-muted-foreground pt-4 border-t">
                <div className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  <span>创建: {new Date(document.created_at).toLocaleString('zh-CN')}</span>
                </div>
                {document.updated_at && document.updated_at !== document.created_at && (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    <span>更新: {new Date(document.updated_at).toLocaleString('zh-CN')}</span>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="py-12 text-center">
            <p className="text-muted-foreground">文档未找到</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
