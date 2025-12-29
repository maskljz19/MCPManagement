import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Plus } from 'lucide-react';
import { GitHubConnectionList } from './components/GitHubConnectionList';
import { GitHubConnectForm } from './components/GitHubConnectForm';
import { SyncStatus } from './components/SyncStatus';
import { DisconnectDialog } from './components/DisconnectDialog';

/**
 * GitHub - GitHub integration page
 * Displays GitHub connections and provides connection management
 * Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
 */
export default function GitHub() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [syncTaskId, setSyncTaskId] = useState<string | null>(null);
  const [showSyncStatus, setShowSyncStatus] = useState(false);
  const [disconnectingConnectionId, setDisconnectingConnectionId] = useState<string | null>(null);

  // Fetch connections to get repository URL for disconnect dialog
  const { data: connections } = useQuery({
    queryKey: ['github-connections'],
    queryFn: () => apiClient.github.listConnections(),
  });

  // Mutation for syncing repository
  const syncMutation = useMutation({
    mutationFn: (connectionId: string) => apiClient.github.sync(connectionId),
    onSuccess: (data) => {
      setSyncTaskId(data.task_id);
      setShowSyncStatus(true);
    },
    onError: (error: Error) => {
      toast({
        title: '同步失败',
        description: error.message || '无法启动同步任务',
        variant: 'destructive',
      });
    },
  });

  const handleSync = (connectionId: string) => {
    syncMutation.mutate(connectionId);
  };

  const handleSyncComplete = (success: boolean) => {
    if (success) {
      toast({
        title: '同步完成',
        description: 'GitHub 仓库已成功同步',
      });
      // Refresh connections list
      queryClient.invalidateQueries({ queryKey: ['github-connections'] });
      // Refresh tools list in case new tools were synced
      queryClient.invalidateQueries({ queryKey: ['tools'] });
    }
  };

  const handleDisconnect = (connectionId: string) => {
    setDisconnectingConnectionId(connectionId);
  };

  // Get repository URL for disconnect dialog
  const disconnectingConnection = connections?.find(
    (c) => c.connection_id === disconnectingConnectionId
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">GitHub 集成</h1>
          <p className="text-muted-foreground mt-2">
            连接 GitHub 仓库以自动同步 MCP 工具配置
          </p>
        </div>
        <Button onClick={() => setShowConnectForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          连接仓库
        </Button>
      </div>

      {/* Connection List */}
      <GitHubConnectionList onSync={handleSync} onDisconnect={handleDisconnect} />

      {/* Connect Form Dialog */}
      <GitHubConnectForm
        open={showConnectForm}
        onOpenChange={setShowConnectForm}
        onSuccess={() => {
          // Connection list will auto-refresh via query invalidation
        }}
      />

      {/* Sync Status Dialog */}
      <SyncStatus
        taskId={syncTaskId}
        open={showSyncStatus}
        onOpenChange={setShowSyncStatus}
        onComplete={handleSyncComplete}
      />

      {/* Disconnect Confirmation Dialog */}
      <DisconnectDialog
        connectionId={disconnectingConnectionId}
        repositoryUrl={disconnectingConnection?.repository_url}
        open={!!disconnectingConnectionId}
        onOpenChange={(open) => {
          if (!open) {
            setDisconnectingConnectionId(null);
          }
        }}
      />
    </div>
  );
}
