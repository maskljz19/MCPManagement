import { useState } from 'react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { Trash2, Clock, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { RevokeAPIKeyDialog } from './RevokeAPIKeyDialog';
import type { APIKey } from '@/types';
import { parseDate } from '@/utils/dateUtils';

interface APIKeyListProps {
  apiKeys: APIKey[];
  isLoading: boolean;
  error: Error | null;
  onRevoke: () => void;
}

/**
 * APIKeyList - Displays list of API keys
 * Shows key information and allows revocation
 * Validates: Requirements 9.1
 */
export function APIKeyList({ apiKeys, isLoading, error, onRevoke }: APIKeyListProps) {
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);

  const handleRevokeClick = (keyId: string) => {
    setSelectedKeyId(keyId);
    setRevokeDialogOpen(true);
  };

  const handleRevokeSuccess = () => {
    setRevokeDialogOpen(false);
    setSelectedKeyId(null);
    onRevoke();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          加载 API 密钥失败: {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  // Empty state
  if (apiKeys.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">
          您还没有创建任何 API 密钥
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          点击上方的"创建密钥"按钮来创建您的第一个 API 密钥
        </p>
      </div>
    );
  }

  // Check if key is expired
  const isExpired = (expiresAt?: string) => {
    if (!expiresAt) return false;
    return parseDate(expiresAt) < new Date();
  };

  // Check if key is revoked
  const isRevoked = (revokedAt?: string) => {
    return !!revokedAt;
  };

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead>最后使用</TableHead>
              <TableHead>过期时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {apiKeys.map((key) => {
              const expired = isExpired(key.expires_at);
              const revoked = isRevoked(key.revoked_at);
              const active = !expired && !revoked;

              return (
                <TableRow key={key.id}>
                  <TableCell className="font-medium">{key.name}</TableCell>
                  <TableCell>
                    {revoked ? (
                      <Badge variant="destructive">已撤销</Badge>
                    ) : expired ? (
                      <Badge variant="secondary">已过期</Badge>
                    ) : (
                      <Badge variant="default">活跃</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center text-sm text-muted-foreground">
                      <Calendar className="h-3 w-3 mr-1" />
                      {format(parseDate(key.created_at), 'PPP', { locale: zhCN })}
                    </div>
                  </TableCell>
                  <TableCell>
                    {key.last_used_at ? (
                      <div className="flex items-center text-sm text-muted-foreground">
                        <Clock className="h-3 w-3 mr-1" />
                        {format(parseDate(key.last_used_at), 'PPP', { locale: zhCN })}
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">从未使用</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {key.expires_at ? (
                      <div className="flex items-center text-sm text-muted-foreground">
                        {format(parseDate(key.expires_at), 'PPP', { locale: zhCN })}
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">永不过期</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRevokeClick(key.id)}
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        撤销
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Revoke Dialog */}
      {selectedKeyId && (
        <RevokeAPIKeyDialog
          open={revokeDialogOpen}
          onOpenChange={setRevokeDialogOpen}
          keyId={selectedKeyId}
          onSuccess={handleRevokeSuccess}
        />
      )}
    </>
  );
}
