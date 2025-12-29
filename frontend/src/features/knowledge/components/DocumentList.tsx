import { FileText, Trash2, Eye } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Document } from '@/types';

interface DocumentListProps {
  documents: Document[];
  onDocumentClick?: (documentId: string) => void;
  onDeleteClick?: (documentId: string) => void;
  isLoading?: boolean;
}

export default function DocumentList({
  documents,
  onDocumentClick,
  onDeleteClick,
  isLoading = false,
}: DocumentListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader>
              <div className="h-5 bg-muted rounded w-3/4"></div>
              <div className="h-4 bg-muted rounded w-1/2 mt-2"></div>
            </CardHeader>
          </Card>
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">暂无文档</p>
          <p className="text-sm text-muted-foreground mt-1">
            上传您的第一个文档开始使用知识库
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => (
        <Card key={doc.document_id} className="hover:bg-accent/50 transition-colors">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  {doc.title}
                </CardTitle>
                <CardDescription className="mt-1">
                  创建于{' '}
                  {formatDistanceToNow(new Date(doc.created_at), {
                    addSuffix: true,
                    locale: zhCN,
                  })}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                {onDocumentClick && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDocumentClick(doc.document_id)}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                )}
                {onDeleteClick && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDeleteClick(doc.document_id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground line-clamp-2">{doc.content}</p>
            {doc.metadata && (
              <div className="flex flex-wrap gap-2 mt-3">
                {doc.metadata.source && (
                  <Badge variant="outline" className="text-xs">
                    来源: {doc.metadata.source}
                  </Badge>
                )}
                {doc.metadata.language && (
                  <Badge variant="outline" className="text-xs">
                    {doc.metadata.language}
                  </Badge>
                )}
                {doc.metadata.tags &&
                  doc.metadata.tags.map((tag: string, index: number) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
