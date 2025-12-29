import { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface RateLimitNoticeProps {
  retryAfter: number; // seconds
  onExpire?: () => void;
}

/**
 * Rate limit notice component with countdown
 * Validates: Requirements 11.7
 */
export function RateLimitNotice({ retryAfter, onExpire }: RateLimitNoticeProps) {
  const [timeRemaining, setTimeRemaining] = useState(retryAfter);

  useEffect(() => {
    if (timeRemaining <= 0) {
      onExpire?.();
      return;
    }

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          clearInterval(timer);
          onExpire?.();
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeRemaining, onExpire]);

  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds} second${seconds !== 1 ? 's' : ''}`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''}`;
  };

  return (
    <Alert variant="warning">
      <Clock className="h-4 w-4" />
      <AlertTitle>Rate Limit Exceeded</AlertTitle>
      <AlertDescription>
        You've made too many requests. Please wait {formatTime(timeRemaining)} before trying again.
      </AlertDescription>
    </Alert>
  );
}
