import { useCallback } from 'react';
import { useToast } from './use-toast';

interface ApiError extends Error {
  statusCode?: number;
  isRateLimit?: boolean;
  isNetworkError?: boolean;
  retryAfter?: number;
}

/**
 * Hook to handle API errors with appropriate user feedback
 * Validates: Requirements 11.1, 11.6, 11.7
 */
export function useApiError() {
  const { error: showError, warning: showWarning } = useToast();

  const handleError = useCallback(
    (err: unknown, customMessage?: string) => {
      const error = err as ApiError;

      // Handle 401 errors (already handled by axios interceptor, but show message)
      if (error.statusCode === 401) {
        showError(
          'Authentication Required',
          'Your session has expired. Please log in again.'
        );
        return;
      }

      // Handle 429 rate limit errors
      if (error.isRateLimit || error.statusCode === 429) {
        const retryMessage = error.retryAfter
          ? `Please try again in ${error.retryAfter} seconds.`
          : 'Please try again later.';
        
        showWarning(
          'Rate Limit Exceeded',
          `You've made too many requests. ${retryMessage}`
        );
        return;
      }

      // Handle network errors
      if (error.isNetworkError) {
        showError(
          'Network Error',
          'Unable to connect to the server. Please check your internet connection.'
        );
        return;
      }

      // Handle 403 Forbidden
      if (error.statusCode === 403) {
        showError(
          'Access Denied',
          'You do not have permission to perform this action.'
        );
        return;
      }

      // Handle 404 Not Found
      if (error.statusCode === 404) {
        showError(
          'Not Found',
          customMessage || 'The requested resource was not found.'
        );
        return;
      }

      // Handle 500 Server Error
      if (error.statusCode === 500) {
        showError(
          'Server Error',
          'A server error occurred. Please try again later.'
        );
        return;
      }

      // Handle 503 Service Unavailable
      if (error.statusCode === 503) {
        showError(
          'Service Unavailable',
          'The service is temporarily unavailable. Please try again later.'
        );
        return;
      }

      // Generic error handling
      showError(
        'Error',
        customMessage || error.message || 'An unexpected error occurred'
      );
    },
    [showError, showWarning]
  );

  return { handleError };
}
