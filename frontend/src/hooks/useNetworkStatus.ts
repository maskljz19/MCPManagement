import { useState, useEffect } from 'react';
import { networkDetector } from '@/lib/networkDetector';

/**
 * Hook to monitor network status
 * Validates: Requirements 11.2
 */
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(networkDetector.getStatus());

  useEffect(() => {
    const unsubscribe = networkDetector.subscribe((status) => {
      setIsOnline(status);
    });

    return unsubscribe;
  }, []);

  return isOnline;
}
