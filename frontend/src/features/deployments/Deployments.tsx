import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DeploymentList } from './components/DeploymentList';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';
import { useToast } from '@/hooks/use-toast';
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

export default function Deployments() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deploymentToStop, setDeploymentToStop] = useState<string | null>(null);

  // Stop deployment mutation
  const stopMutation = useMutation({
    mutationFn: (id: string) => apiClient.deployments.stop(id),
    onSuccess: () => {
      toast({
        title: '成功',
        description: '部署已停止',
      });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      setDeploymentToStop(null);
    },
    onError: (error: Error) => {
      toast({
        title: '错误',
        description: `停止部署失败: ${error.message}`,
        variant: 'destructive',
      });
    },
  });

  const handleViewDetails = (id: string) => {
    navigate(`/deployments/${id}`);
  };

  const handleStop = (id: string) => {
    setDeploymentToStop(id);
  };

  const handleConfirmStop = () => {
    if (deploymentToStop) {
      stopMutation.mutate(deploymentToStop);
    }
  };

  const handleCreateNew = () => {
    navigate('/deployments/new');
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">部署管理</h1>
      <DeploymentList
        onViewDetails={handleViewDetails}
        onStop={handleStop}
        onCreateNew={handleCreateNew}
      />

      {/* Stop confirmation dialog */}
      <AlertDialog open={!!deploymentToStop} onOpenChange={() => setDeploymentToStop(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认停止部署</AlertDialogTitle>
            <AlertDialogDescription>
              您确定要停止此部署吗？此操作将终止运行中的服务。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmStop}>停止</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
