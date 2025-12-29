import { useQuery } from '@tanstack/react-query';
import { Clock, User, GitCommit } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import Editor from '@monaco-editor/react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface ToolHistoryProps {
  toolId: string;
}

export default function ToolHistory({ toolId }: ToolHistoryProps) {
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  // Fetch version history
  const { data: versions, isLoading, error } = useQuery({
    queryKey: ['tool-history', toolId],
    queryFn: () => apiClient.tools.getHistory(toolId),
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>版本历史</CardTitle>
          <CardDescription>工具的所有版本变更记录</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>版本历史</CardTitle>
          <CardDescription>工具的所有版本变更记录</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            无法加载版本历史，请稍后重试。
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>版本历史</CardTitle>
          <CardDescription>工具的所有版本变更记录</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            暂无版本历史记录。
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>版本历史</CardTitle>
        <CardDescription>
          工具的所有版本变更记录（共 {versions.length} 个版本）
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Timeline */}
          <div className="relative space-y-4">
            {/* Timeline line */}
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />

            {versions.map((version, index) => (
              <div key={index} className="relative pl-12">
                {/* Timeline dot */}
                <div className="absolute left-2.5 top-2 h-3 w-3 rounded-full bg-primary ring-4 ring-background" />

                {/* Version card */}
                <div className="border rounded-lg p-4 hover:bg-accent/50 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">
                        <GitCommit className="mr-1 h-3 w-3" />
                        v{version.version}
                      </Badge>
                      <span className="text-sm text-muted-foreground flex items-center">
                        <Clock className="mr-1 h-3 w-3" />
                        {format(new Date(version.created_at), 'PPP HH:mm', {
                          locale: zhCN,
                        })}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setSelectedVersion(
                          selectedVersion === index ? null : index
                        )
                      }
                    >
                      {selectedVersion === index ? '隐藏变更' : '查看变更'}
                    </Button>
                  </div>

                  <div className="text-sm text-muted-foreground flex items-center">
                    <User className="mr-1 h-3 w-3" />
                    作者: {version.author_id}
                  </div>

                  {/* Changes diff */}
                  {selectedVersion === index && (
                    <div className="mt-4 border rounded-lg overflow-hidden">
                      <Editor
                        height="300px"
                        defaultLanguage="json"
                        value={JSON.stringify(version.changes, null, 2)}
                        options={{
                          readOnly: true,
                          minimap: { enabled: false },
                          scrollBeyondLastLine: false,
                          fontSize: 12,
                          lineNumbers: 'off',
                        }}
                        theme="vs-dark"
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
