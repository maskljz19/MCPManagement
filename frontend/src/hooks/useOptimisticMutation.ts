import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/hooks/use-toast';

/**
 * Custom hook for mutations with optimistic updates
 * Requirements: 12.4, 12.5
 * 
 * This hook provides a standardized way to perform mutations with:
 * - Optimistic updates (immediate UI feedback)
 * - Automatic rollback on error
 * - Cache invalidation on success
 * - Success/error notifications
 */

interface OptimisticMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  queryKey: string[];
  updateCache?: (oldData: any, variables: TVariables) => any;
  successMessage?: string;
  errorMessage?: string;
  onSuccess?: (data: TData, variables: TVariables, context: any) => void;
  onError?: (error: Error, variables: TVariables, context: any) => void;
}

export function useOptimisticMutation<TData = unknown, TVariables = unknown>({
  mutationFn,
  queryKey,
  updateCache,
  successMessage,
  errorMessage,
  onSuccess,
  onError,
}: OptimisticMutationOptions<TData, TVariables>) {
  const queryClient = useQueryClient();

  return useMutation<TData, Error, TVariables, { previousData: any } | undefined>({
    mutationFn,
    
    // Optimistic update
    onMutate: async (variables) => {
      if (!updateCache) return undefined;

      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot the previous value
      const previousData = queryClient.getQueryData(queryKey);

      // Optimistically update the cache
      queryClient.setQueryData(queryKey, (old: any) => updateCache(old, variables));

      // Return context with previous data for rollback
      return { previousData };
    },

    // Rollback on error
    onError: (error, variables, context) => {
      if (context?.previousData !== undefined) {
        queryClient.setQueryData(queryKey, context.previousData);
      }

      // Show error toast
      if (errorMessage) {
        toast({
          title: '操作失败',
          description: errorMessage,
          variant: 'destructive',
        });
      }

      // Call custom error handler
      onError?.(error, variables, context);
    },

    // Success callback
    onSuccess: (data, variables, context) => {
      // Show success toast
      if (successMessage) {
        toast({
          title: '操作成功',
          description: successMessage,
        });
      }

      // Call custom success handler
      onSuccess?.(data, variables, context);
    },

    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/**
 * Example usage:
 * 
 * ```typescript
 * const updateToolMutation = useOptimisticMutation({
 *   mutationFn: (data: UpdateToolData) => apiClient.tools.update(toolId, data),
 *   queryKey: ['tools', toolId],
 *   updateCache: (oldTool, newData) => ({ ...oldTool, ...newData }),
 *   successMessage: '工具更新成功',
 *   errorMessage: '工具更新失败',
 * });
 * 
 * // Use it
 * updateToolMutation.mutate({ name: 'New Name' });
 * ```
 */
