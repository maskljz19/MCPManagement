import { memo } from 'react';
import { MCPTool } from '@/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ToolCardProps {
  tool: MCPTool;
  onClick?: () => void;
}

const statusConfig = {
  DRAFT: { label: '草稿', variant: 'secondary' as const },
  ACTIVE: { label: '活跃', variant: 'default' as const },
  DEPRECATED: { label: '已弃用', variant: 'destructive' as const },
};

/**
 * ToolCard - Optimized with React.memo to prevent unnecessary re-renders
 * Only re-renders when tool data or onClick handler changes
 */
const ToolCard = memo(function ToolCard({ tool, onClick }: ToolCardProps) {
  const status = statusConfig[tool.status];

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-lg hover:border-primary"
      onClick={onClick}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-xl">{tool.name}</CardTitle>
            <CardDescription className="mt-1">
              {tool.slug}
            </CardDescription>
          </div>
          <Badge variant={status.variant}>{status.label}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
          {tool.description}
        </p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>版本 {tool.version}</span>
          <span>
            {formatDistanceToNow(new Date(tool.updated_at), {
              addSuffix: true,
              locale: zhCN,
            })}
          </span>
        </div>
      </CardContent>
    </Card>
  );
});

export default ToolCard;
