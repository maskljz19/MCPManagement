import { WifiOff } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import { useI18n } from '@/hooks/useI18n';

/**
 * Offline indicator component
 * Validates: Requirements 11.2
 */
export function OfflineIndicator() {
  const isOnline = useNetworkStatus();
  const { t } = useI18n();

  if (isOnline) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:left-auto md:right-4 md:w-96">
      <Alert variant="destructive">
        <WifiOff className="h-4 w-4" />
        <AlertDescription>
          {t('common.offline')}
        </AlertDescription>
      </Alert>
    </div>
  );
}
