import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { useApiError } from '@/hooks/useApiError';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import {
  LoadingSpinner,
  ButtonSpinner,
  LoadingOverlay,
  ListSkeleton,
  RateLimitNotice,
} from '@/components/common';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

/**
 * Demo component showcasing error handling and user feedback features
 * This component demonstrates all the error handling capabilities
 */
export function ErrorHandlingDemo() {
  const { success, error, warning, info } = useToast();
  const { handleError } = useApiError();
  const isOnline = useNetworkStatus();
  const [isLoading, setIsLoading] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  const [isRateLimited, setIsRateLimited] = useState(false);

  const simulateSuccess = () => {
    success('Success!', 'Your action was completed successfully.');
  };

  const simulateError = () => {
    error('Error!', 'Something went wrong. Please try again.');
  };

  const simulateWarning = () => {
    warning('Warning!', 'Please review your input before proceeding.');
  };

  const simulateInfo = () => {
    info('Information', 'Here is some helpful information.');
  };

  const simulateLoading = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 3000);
  };

  const simulateSkeleton = () => {
    setShowSkeleton(true);
    setTimeout(() => setShowSkeleton(false), 3000);
  };

  const simulateApiError = (statusCode: number) => {
    const mockError = {
      message: 'Mock API error',
      statusCode,
      isRateLimit: statusCode === 429,
      isNetworkError: statusCode === 0,
      retryAfter: statusCode === 429 ? 60 : undefined,
    };
    handleError(mockError);
  };

  const simulateRateLimit = () => {
    setIsRateLimited(true);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Error Handling & User Feedback Demo</h1>
        <p className="text-muted-foreground mt-2">
          This page demonstrates all error handling and user feedback features.
        </p>
      </div>

      <Tabs defaultValue="toasts" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="toasts">Toasts</TabsTrigger>
          <TabsTrigger value="loading">Loading</TabsTrigger>
          <TabsTrigger value="errors">API Errors</TabsTrigger>
          <TabsTrigger value="network">Network</TabsTrigger>
        </TabsList>

        <TabsContent value="toasts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Toast Notifications</CardTitle>
              <CardDescription>
                Click the buttons below to see different toast variants
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button onClick={simulateSuccess} variant="default">
                Show Success Toast
              </Button>
              <Button onClick={simulateError} variant="destructive">
                Show Error Toast
              </Button>
              <Button onClick={simulateWarning} variant="outline">
                Show Warning Toast
              </Button>
              <Button onClick={simulateInfo} variant="secondary">
                Show Info Toast
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="loading" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Loading States</CardTitle>
              <CardDescription>
                Different loading indicators and skeleton screens
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <h3 className="font-semibold">Loading Spinner</h3>
                <LoadingSpinner text="Loading data..." />
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold">Button with Spinner</h3>
                <Button onClick={simulateLoading} disabled={isLoading}>
                  {isLoading && <ButtonSpinner />}
                  {isLoading ? 'Loading...' : 'Simulate Loading'}
                </Button>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold">Loading Overlay</h3>
                <LoadingOverlay isLoading={isLoading} text="Processing...">
                  <div className="h-32 border rounded-md p-4">
                    <p>This content is covered by a loading overlay when loading.</p>
                  </div>
                </LoadingOverlay>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold">Skeleton Screen</h3>
                <Button onClick={simulateSkeleton}>
                  {showSkeleton ? 'Loading...' : 'Show Skeleton'}
                </Button>
                {showSkeleton && <ListSkeleton count={3} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Error Handling</CardTitle>
              <CardDescription>
                Simulate different API error responses
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button onClick={() => simulateApiError(401)} variant="outline">
                401 Unauthorized
              </Button>
              <Button onClick={() => simulateApiError(403)} variant="outline">
                403 Forbidden
              </Button>
              <Button onClick={() => simulateApiError(404)} variant="outline">
                404 Not Found
              </Button>
              <Button onClick={() => simulateApiError(429)} variant="outline">
                429 Rate Limit
              </Button>
              <Button onClick={() => simulateApiError(500)} variant="outline">
                500 Server Error
              </Button>
              <Button onClick={() => simulateApiError(503)} variant="outline">
                503 Service Unavailable
              </Button>
              <Button onClick={() => simulateApiError(0)} variant="outline">
                Network Error
              </Button>
            </CardContent>
          </Card>

          {isRateLimited && (
            <RateLimitNotice
              retryAfter={30}
              onExpire={() => setIsRateLimited(false)}
            />
          )}

          <Card>
            <CardHeader>
              <CardTitle>Rate Limit Notice</CardTitle>
              <CardDescription>
                Shows a countdown when rate limited
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={simulateRateLimit}>
                Simulate Rate Limit
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="network" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Network Status</CardTitle>
              <CardDescription>
                Current network connection status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <div
                  className={`h-3 w-3 rounded-full ${
                    isOnline ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="font-medium">
                  {isOnline ? 'Online' : 'Offline'}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Try disconnecting your internet to see the offline indicator appear.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
