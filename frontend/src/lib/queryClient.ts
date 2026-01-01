import { QueryClient, MutationCache, QueryCache } from '@tanstack/react-query';
import { toast } from '@/hooks/use-toast';

/**
 * Configure TanStack Query client with default options
 * Requirements: 12.4, 12.5
 * 
 * Features:
 * - Automatic caching with 5-minute stale time
 * - Automatic retry with exponential backoff
 * - Automatic refetch on window focus and reconnect
 * - Optimistic updates support
 * - Global error handling
 */

/**
 * Global error handler for queries
 */
const handleQueryError = (error: Error) => {
  console.error('Query error:', error);
  
  // Don't show toast for 401 errors (handled by axios interceptor)
  if (error.message.includes('401')) {
    return;
  }
  
  toast({
    title: '数据加载失败',
    description: error.message || '请稍后重试',
    variant: 'destructive',
  });
};

/**
 * Global error handler for mutations
 */
const handleMutationError = (error: Error) => {
  console.error('Mutation error:', error);
  
  // Don't show toast for 401 errors (handled by axios interceptor)
  if (error.message.includes('401')) {
    return;
  }
  
  toast({
    title: '操作失败',
    description: error.message || '请稍后重试',
    variant: 'destructive',
  });
};

/**
 * Query client with optimistic updates and cache management
 */
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleQueryError,
  }),
  mutationCache: new MutationCache({
    onError: handleMutationError,
  }),
  defaultOptions: {
    queries: {
      // Cache configuration
      // Data is considered fresh for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Garbage collection time: 10 minutes
      // Unused data is kept in cache for 10 minutes before being garbage collected
      gcTime: 10 * 60 * 1000,
      
      // Retry configuration - DISABLED to prevent multiple failed requests
      retry: false,
      
      // Refetch configuration
      // Automatically refetch when window regains focus
      refetchOnWindowFocus: true,
      // Automatically refetch when network reconnects
      refetchOnReconnect: true,
      // Refetch on component mount if data is stale
      refetchOnMount: true,
      
      // Network mode
      // Only run queries when online
      networkMode: 'online',
      
      // Structural sharing
      // Optimize re-renders by sharing unchanged data structures
      structuralSharing: true,
    },
    mutations: {
      // Retry configuration for mutations - DISABLED
      retry: false,
      
      // Network mode
      // Only run mutations when online
      networkMode: 'online',
      
      // Global mutation callbacks can be added here
      // Individual mutations can override these with their own callbacks
      onSuccess: () => {
        // Optional: Show success toast for all mutations
        // Individual mutations can override this
      },
    },
  },
});

/**
 * Helper function to invalidate related queries after a mutation
 * This ensures the UI stays in sync with the server
 * 
 * Example usage:
 * ```typescript
 * const mutation = useMutation({
 *   mutationFn: apiClient.tools.create,
 *   onSuccess: () => {
 *     invalidateQueries(['tools']);
 *   }
 * });
 * ```
 */
export const invalidateQueries = (queryKeys: string[]) => {
  queryKeys.forEach((key) => {
    queryClient.invalidateQueries({ queryKey: [key] });
  });
};

/**
 * Helper function for optimistic updates
 * Updates the cache immediately before the mutation completes
 * 
 * Example usage:
 * ```typescript
 * const mutation = useMutation({
 *   mutationFn: apiClient.tools.update,
 *   onMutate: async (newTool) => {
 *     return optimisticUpdate(['tools', newTool.id], newTool);
 *   },
 *   onError: (err, newTool, context) => {
 *     // Rollback on error
 *     if (context?.previousData) {
 *       queryClient.setQueryData(['tools', newTool.id], context.previousData);
 *     }
 *   },
 *   onSettled: () => {
 *     queryClient.invalidateQueries({ queryKey: ['tools'] });
 *   }
 * });
 * ```
 */
export const optimisticUpdate = <T,>(queryKey: string[], newData: T) => {
  // Cancel any outgoing refetches
  queryClient.cancelQueries({ queryKey });
  
  // Snapshot the previous value
  const previousData = queryClient.getQueryData<T>(queryKey);
  
  // Optimistically update to the new value
  queryClient.setQueryData<T>(queryKey, newData);
  
  // Return context with previous data for rollback
  return { previousData };
};

/**
 * Helper function to prefetch data
 * Useful for improving perceived performance
 * 
 * Example usage:
 * ```typescript
 * // Prefetch on hover
 * <div onMouseEnter={() => prefetchQuery(['tools', toolId], () => apiClient.tools.get(toolId))}>
 * ```
 */
export const prefetchQuery = async <T,>(
  queryKey: string[],
  queryFn: () => Promise<T>
) => {
  await queryClient.prefetchQuery({
    queryKey,
    queryFn,
  });
};
