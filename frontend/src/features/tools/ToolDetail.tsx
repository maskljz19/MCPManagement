import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Edit, Trash2, Clock } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import Editor from '@monaco-editor/react';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import ToolHistory from './components/ToolHistory';

const statusConfig = {
  draft: { label: '草稿', variant: 'secondary' as const },
  active: { label: '活跃', variant: 'default' as const },
  deprecated: { label: '已弃用', variant: 'destructive' as const },
};

export default function ToolDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch tool details
  const { data: tool, isLoading, error } = useQuery({
    queryKey: ['tool', id],
    queryFn: () => apiClient.tools.get(id!),
    enabled: !!id,
  });

  // Handle delete
  const handleDelete = async () => {
    if (!id) return;

    setIsDeleting(true);
    try {
      await apiClient.tools.delete(id);
      toast({
        title: '删除成功',
        description: '工具已成功删除。',
      });
      navigate('/tools');
    } catch (error) {
      toast({
        title: '删除失败',
        description: '无法删除工具，请稍后重试。',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  // Handle edit
  const handleEdit = () => {
    navigate(`/tools/${id}/edit`);
  };

  // Handle back
  const handleBack = () => {
    navigate('/tools');
  };

  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回列表
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              无法加载工具详情，请稍后重试。
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-[600px]" />
      </div>
    );
  }

  if (!tool) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回列表
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">工具不存在。</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const status = statusConfig[tool.status];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回列表
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleEdit}>
            <Edit className="mr-2 h-4 w-4" />
            编辑
          </Button>
          <Button
            variant="destructive"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            删除
          </Button>
        </div>
      </div>

      {/* Tool Info Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-3xl">{tool.name}</CardTitle>
              <CardDescription className="text-base mt-2">
                {tool.slug}
              </CardDescription>
            </div>
            <Badge variant={status.variant} className="text-sm">
              {status.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-medium mb-2">描述</h3>
            <p className="text-muted-foreground">{tool.description}</p>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium mb-2">版本</h3>
              <p className="text-muted-foreground">{tool.version}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2">作者 ID</h3>
              <p className="text-muted-foreground">{tool.author_id}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2 flex items-center">
                <Clock className="mr-2 h-4 w-4" />
                创建时间
              </h3>
              <p className="text-muted-foreground">
                {format(new Date(tool.created_at), 'PPP HH:mm', {
                  locale: zhCN,
                })}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2 flex items-center">
                <Clock className="mr-2 h-4 w-4" />
                更新时间
              </h3>
              <p className="text-muted-foreground">
                {format(new Date(tool.updated_at), 'PPP HH:mm', {
                  locale: zhCN,
                })}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Card */}
      <Card>
        <CardHeader>
          <CardTitle>配置</CardTitle>
          <CardDescription>工具的 JSON 配置</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-hidden">
            <Editor
              height="400px"
              defaultLanguage="json"
              value={JSON.stringify(tool.config, null, 2)}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
              }}
              theme="vs-dark"
            />
          </div>
        </CardContent>
      </Card>

      {/* Version History */}
      {id && <ToolHistory toolId={id} />}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              您确定要删除工具 "{tool.name}" 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={isDeleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
