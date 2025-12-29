import { useNavigate } from 'react-router-dom';
import { DeploymentForm } from './components/DeploymentForm';
import { useToast } from '@/hooks/use-toast';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DeploymentNew() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSuccess = (deploymentId: string) => {
    toast({
      title: '成功',
      description: '部署已创建',
    });
    navigate(`/deployments/${deploymentId}`);
  };

  const handleCancel = () => {
    navigate('/deployments');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/deployments')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold">新建部署</h1>
      </div>
      <DeploymentForm onSuccess={handleSuccess} onCancel={handleCancel} />
    </div>
  );
}
