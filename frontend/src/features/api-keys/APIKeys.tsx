import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/services/apiClient';
import { APIKeyList } from './components/APIKeyList';
import { CreateAPIKeyDialog } from './components/CreateAPIKeyDialog';
import { useToast } from '@/hooks/use-toast';

/**
 * APIKeys - API Key management page
 * Displays list of API keys and allows creating new ones
 * Validates: Requirements 9.1
 */
export default function APIKeys() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const { toast } = useToast();

  // Fetch API keys
  const {
    data: apiKeys,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: () => apiClient.apiKeys.list(),
  });

  const handleCreateSuccess = () => {
    setCreateDialogOpen(false);
    refetch();
    toast({
      title: '成功',
      description: 'API 密钥已创建',
    });
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API 密钥</h1>
          <p className="text-muted-foreground mt-2">
            管理您的 API 密钥以进行程序化访问
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          创建密钥
        </Button>
      </div>

      {/* API Keys List */}
      <Card>
        <CardHeader>
          <CardTitle>您的 API 密钥</CardTitle>
          <CardDescription>
            使用这些密钥通过 API 访问平台。请妥善保管您的密钥。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <APIKeyList
            apiKeys={apiKeys || []}
            isLoading={isLoading}
            error={error as Error | null}
            onRevoke={refetch}
          />
        </CardContent>
      </Card>

      {/* Create API Key Dialog */}
      <CreateAPIKeyDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
}
