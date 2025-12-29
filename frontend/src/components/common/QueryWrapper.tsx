import { ReactNode } from 'react';
import { UseQueryResult } from '@tanstack/react-query';
import { LoadingSpinner } from './LoadingSpinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface QueryWrapperProps<T> {
  query: UseQueryResult<T, Error>;
  loadingComponent?: ReactNode;
  errorTitle?: string;
  children: (data: T) => ReactNode;
}

/**
 * Wrapper component for React Query that handles loading and error states
 * Validates: Requirements 11.1, 11.3
 */
export function QueryWrapper<T>({
  query,
  loadingComponent,
  errorTitle = 'Error Loading Data',
  children,
}: QueryWrapperProps<T>) {
  const { data, isLoading, isError, error, refetch } = query;

  if (isLoading) {
    return loadingComponent || <LoadingSpinner />;
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>{errorTitle}</AlertTitle>
        <AlertDescription className="mt-2">
          {error?.message || 'An unexpected error occurred'}
        </AlertDescription>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="mt-4"
        >
          Try Again
        </Button>
      </Alert>
    );
  }

  if (!data) {
    return (
      <Alert>
        <AlertDescription>No data available</AlertDescription>
      </Alert>
    );
  }

  return <>{children(data)}</>;
}
