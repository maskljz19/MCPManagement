# Caching Strategy

This document explains the data caching and persistence strategy implemented in the MCP Platform frontend application.

## Requirements

- **Requirement 12.3**: Theme preference persistence
- **Requirement 12.4**: Cache data for improved performance
- **Requirement 12.5**: Refresh expired cache data

## Theme Persistence

### Implementation

Theme preferences are persisted using Zustand's persist middleware with localStorage.

**Location**: `frontend/src/stores/uiStore.ts`

**Features**:
- Automatic persistence to localStorage
- Supports light, dark, and system themes
- Respects system theme preferences
- Listens for system theme changes
- Restores theme on page load

**Usage**:
```typescript
import { useTheme } from '@/hooks/useTheme';

function MyComponent() {
  const { theme, setTheme, effectiveTheme } = useTheme();
  
  return (
    <button onClick={() => setTheme('dark')}>
      Switch to Dark Mode
    </button>
  );
}
```

**Components**:
- `ThemeProvider`: Initializes theme on app load
- `ThemeToggle`: UI component for switching themes
- `useTheme`: Hook for accessing theme state

## TanStack Query Caching

### Cache Configuration

**Location**: `frontend/src/lib/queryClient.ts`

**Settings**:
- **Stale Time**: 5 minutes - Data is considered fresh for 5 minutes
- **GC Time**: 10 minutes - Unused data is kept in cache for 10 minutes
- **Retry**: 3 attempts with exponential backoff (1s, 2s, 4s, max 30s)
- **Refetch on Window Focus**: Enabled
- **Refetch on Reconnect**: Enabled
- **Refetch on Mount**: Enabled (if data is stale)

### Cache Invalidation

Cache is automatically invalidated when:
1. Data becomes stale (after 5 minutes)
2. Window regains focus
3. Network reconnects
4. After successful mutations

**Manual Invalidation**:
```typescript
import { invalidateQueries } from '@/lib/queryClient';

// Invalidate specific queries
invalidateQueries(['tools', 'deployments']);
```

### Optimistic Updates

Optimistic updates provide immediate UI feedback before the server responds.

**Implementation**: `frontend/src/hooks/useOptimisticMutation.ts`

**Features**:
- Immediate cache update
- Automatic rollback on error
- Cache invalidation on success
- Success/error notifications

**Example**:
```typescript
import { useOptimisticMutation } from '@/hooks/useOptimisticMutation';
import { apiClient } from '@/services/apiClient';

function ToolEditor({ toolId }) {
  const updateMutation = useOptimisticMutation({
    mutationFn: (data) => apiClient.tools.update(toolId, data),
    queryKey: ['tools', toolId],
    updateCache: (oldTool, newData) => ({ ...oldTool, ...newData }),
    successMessage: '工具更新成功',
    errorMessage: '工具更新失败',
  });

  const handleUpdate = (data) => {
    updateMutation.mutate(data);
    // UI updates immediately, before server responds
  };

  return (
    <form onSubmit={handleUpdate}>
      {/* form fields */}
    </form>
  );
}
```

### Prefetching

Prefetch data to improve perceived performance.

**Example**:
```typescript
import { prefetchQuery } from '@/lib/queryClient';
import { apiClient } from '@/services/apiClient';

function ToolCard({ toolId }) {
  const handleMouseEnter = () => {
    // Prefetch tool details on hover
    prefetchQuery(['tools', toolId], () => apiClient.tools.get(toolId));
  };

  return (
    <div onMouseEnter={handleMouseEnter}>
      {/* card content */}
    </div>
  );
}
```

## Cache Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Action                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Check Cache (TanStack Query)                    │
│  - Is data in cache?                                         │
│  - Is data fresh (< 5 minutes old)?                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    │               │
            Cache Hit           Cache Miss
            (Fresh Data)        (Stale/No Data)
                    │               │
                    ↓               ↓
            ┌───────────┐   ┌──────────────┐
            │  Return   │   │ Fetch from   │
            │  Cached   │   │   Server     │
            │   Data    │   └──────────────┘
            └───────────┘           ↓
                    │       ┌──────────────┐
                    │       │ Update Cache │
                    │       └──────────────┘
                    │               │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │  Render UI    │
                    └───────────────┘
```

## Optimistic Update Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  User Submits Form                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              1. onMutate (Optimistic Update)                 │
│  - Cancel outgoing queries                                   │
│  - Snapshot current cache                                    │
│  - Update cache with new data                                │
│  - UI updates immediately                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              2. Send Request to Server                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    │               │
                Success           Error
                    │               │
                    ↓               ↓
        ┌───────────────┐   ┌──────────────┐
        │  3. onSuccess │   │  3. onError  │
        │  - Show toast │   │  - Rollback  │
        │               │   │  - Show error│
        └───────────────┘   └──────────────┘
                    │               │
                    └───────┬───────┘
                            ↓
                ┌───────────────────────┐
                │  4. onSettled         │
                │  - Invalidate queries │
                │  - Refetch from server│
                └───────────────────────┘
```

## Best Practices

### 1. Use Optimistic Updates for Better UX

Optimistic updates make the UI feel instant and responsive.

**Good for**:
- Updating existing data (edit tool, update status)
- Deleting items
- Toggling states

**Not good for**:
- Creating new items (need server-generated IDs)
- Complex operations with validation

### 2. Invalidate Related Queries

When mutating data, invalidate all related queries to keep the UI in sync.

```typescript
const deleteMutation = useMutation({
  mutationFn: apiClient.tools.delete,
  onSuccess: () => {
    // Invalidate both list and detail queries
    queryClient.invalidateQueries({ queryKey: ['tools'] });
    queryClient.invalidateQueries({ queryKey: ['tools', toolId] });
  },
});
```

### 3. Use Prefetching for Better Performance

Prefetch data that users are likely to need next.

```typescript
// Prefetch next page on pagination
const { data } = useQuery(['tools', page]);

useEffect(() => {
  if (page < totalPages) {
    prefetchQuery(['tools', page + 1], () => 
      apiClient.tools.list({ page: page + 1 })
    );
  }
}, [page, totalPages]);
```

### 4. Configure Stale Time Based on Data Volatility

- **Frequently changing data**: Lower stale time (1-2 minutes)
- **Rarely changing data**: Higher stale time (10-15 minutes)
- **Static data**: Very high stale time (1 hour+)

```typescript
// Override default stale time for specific queries
useQuery(['static-config'], fetchConfig, {
  staleTime: 60 * 60 * 1000, // 1 hour
});
```

### 5. Handle Loading and Error States

Always handle loading and error states for better UX.

```typescript
const { data, isLoading, error } = useQuery(['tools'], apiClient.tools.list);

if (isLoading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} />;
return <ToolList tools={data} />;
```

## Monitoring Cache Performance

### React Query Devtools

Enable React Query Devtools in development to monitor cache behavior:

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

function App() {
  return (
    <>
      <YourApp />
      <ReactQueryDevtools initialIsOpen={false} />
    </>
  );
}
```

### Cache Metrics

Monitor these metrics to optimize cache performance:
- Cache hit rate
- Average query time
- Number of refetches
- Cache size

## Troubleshooting

### Data Not Updating

**Problem**: UI shows stale data after mutation.

**Solution**: Ensure you're invalidating queries after mutations:
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['tools'] });
}
```

### Too Many Refetches

**Problem**: Queries refetch too frequently.

**Solution**: Increase stale time or disable refetch on window focus:
```typescript
useQuery(['tools'], fetchTools, {
  staleTime: 10 * 60 * 1000, // 10 minutes
  refetchOnWindowFocus: false,
});
```

### Optimistic Update Flicker

**Problem**: UI flickers when optimistic update is replaced by server data.

**Solution**: Ensure optimistic update matches server response structure:
```typescript
updateCache: (oldData, newData) => {
  // Match server response structure exactly
  return { ...oldData, ...newData, updated_at: new Date().toISOString() };
}
```

## References

- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [Zustand Persist Middleware](https://docs.pmnd.rs/zustand/integrations/persisting-store-data)
- [Optimistic Updates Guide](https://tanstack.com/query/latest/docs/react/guides/optimistic-updates)
