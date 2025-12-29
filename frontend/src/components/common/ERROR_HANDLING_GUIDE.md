# Error Handling and User Feedback Guide

This guide demonstrates how to use the error handling and user feedback components in the MCP Platform Frontend.

## Table of Contents

1. [Error Boundary](#error-boundary)
2. [Toast Notifications](#toast-notifications)
3. [Loading States](#loading-states)
4. [Form Validation](#form-validation)
5. [API Error Handling](#api-error-handling)
6. [Network Status](#network-status)

## Error Boundary

Wrap your application or specific components with ErrorBoundary to catch React errors:

```tsx
import ErrorBoundary from '@/components/common/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <YourApp />
    </ErrorBoundary>
  );
}

// With custom fallback
<ErrorBoundary fallback={<CustomErrorPage />}>
  <YourComponent />
</ErrorBoundary>
```

## Toast Notifications

Use the toast hook for user feedback:

```tsx
import { useToast } from '@/hooks/use-toast';

function MyComponent() {
  const { success, error, warning, info } = useToast();

  const handleSuccess = () => {
    success('Success!', 'Your action was completed successfully.');
  };

  const handleError = () => {
    error('Error!', 'Something went wrong.');
  };

  const handleWarning = () => {
    warning('Warning!', 'Please be careful.');
  };

  const handleInfo = () => {
    info('Info', 'Here is some information.');
  };

  return (
    <div>
      <button onClick={handleSuccess}>Show Success</button>
      <button onClick={handleError}>Show Error</button>
      <button onClick={handleWarning}>Show Warning</button>
      <button onClick={handleInfo}>Show Info</button>
    </div>
  );
}
```

## Loading States

### Loading Spinner

```tsx
import { LoadingSpinner, LoadingPage, ButtonSpinner } from '@/components/common';

// Inline spinner
<LoadingSpinner size="md" text="Loading..." />

// Full page loading
<LoadingPage text="Loading application..." />

// Button with spinner
<Button disabled={isLoading}>
  {isLoading && <ButtonSpinner />}
  Submit
</Button>
```

### Loading Overlay

```tsx
import { LoadingOverlay } from '@/components/common';

<LoadingOverlay isLoading={isLoading} text="Saving...">
  <YourContent />
</LoadingOverlay>
```

### Skeleton Screens

```tsx
import {
  CardSkeleton,
  ListSkeleton,
  TableSkeleton,
  FormSkeleton,
  DetailSkeleton,
  DashboardSkeleton,
} from '@/components/common';

function MyComponent() {
  const { data, isLoading } = useQuery(...);

  if (isLoading) {
    return <ListSkeleton count={5} />;
  }

  return <YourContent data={data} />;
}
```

## Form Validation

### Using Form Components

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { FormErrorSummary } from '@/components/common';

const formSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
});

function MyForm() {
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: '',
      email: '',
    },
  });

  const onSubmit = (data) => {
    console.log(data);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        {/* Show all errors at the top */}
        <FormErrorSummary errors={form.formState.errors} />

        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit">Submit</Button>
      </form>
    </Form>
  );
}
```

## API Error Handling

### Using useApiError Hook

```tsx
import { useApiError } from '@/hooks/useApiError';
import { useMutation } from '@tanstack/react-query';

function MyComponent() {
  const { handleError } = useApiError();

  const mutation = useMutation({
    mutationFn: createTool,
    onSuccess: () => {
      // Handle success
    },
    onError: (error) => {
      handleError(error, 'Failed to create tool');
    },
  });

  return (
    <Button onClick={() => mutation.mutate(data)}>
      Create Tool
    </Button>
  );
}
```

### Using QueryWrapper

```tsx
import { QueryWrapper } from '@/components/common';
import { useQuery } from '@tanstack/react-query';
import { ListSkeleton } from '@/components/common';

function MyComponent() {
  const query = useQuery({
    queryKey: ['tools'],
    queryFn: fetchTools,
  });

  return (
    <QueryWrapper
      query={query}
      loadingComponent={<ListSkeleton count={5} />}
      errorTitle="Failed to load tools"
    >
      {(data) => (
        <div>
          {data.map((tool) => (
            <ToolCard key={tool.id} tool={tool} />
          ))}
        </div>
      )}
    </QueryWrapper>
  );
}
```

### Rate Limit Handling

```tsx
import { RateLimitNotice } from '@/components/common';
import { useState } from 'react';

function MyComponent() {
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [retryAfter, setRetryAfter] = useState(0);

  const handleApiCall = async () => {
    try {
      await apiCall();
    } catch (error) {
      if (error.isRateLimit) {
        setIsRateLimited(true);
        setRetryAfter(error.retryAfter || 60);
      }
    }
  };

  if (isRateLimited) {
    return (
      <RateLimitNotice
        retryAfter={retryAfter}
        onExpire={() => setIsRateLimited(false)}
      />
    );
  }

  return <Button onClick={handleApiCall}>Make API Call</Button>;
}
```

## Network Status

### Using Offline Indicator

The OfflineIndicator is automatically included in the App component and will show when the user goes offline.

### Using useNetworkStatus Hook

```tsx
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

function MyComponent() {
  const isOnline = useNetworkStatus();

  return (
    <div>
      {!isOnline && (
        <Alert variant="destructive">
          You are offline. Some features may not be available.
        </Alert>
      )}
      <Button disabled={!isOnline}>
        Submit
      </Button>
    </div>
  );
}
```

## Best Practices

1. **Always handle errors**: Use try-catch blocks and error callbacks
2. **Show loading states**: Use skeletons for better UX
3. **Provide clear feedback**: Use appropriate toast variants
4. **Validate forms**: Use Zod schemas with React Hook Form
5. **Handle network errors**: Check online status before critical operations
6. **Rate limit awareness**: Handle 429 errors gracefully
7. **Accessibility**: Ensure error messages are accessible to screen readers

## Error Handling Flow

```
User Action
    ↓
API Call
    ↓
Error? ──No──→ Success Toast → Update UI
    ↓
   Yes
    ↓
Check Error Type
    ↓
├─ 401 → Token Refresh (automatic) → Retry or Redirect to Login
├─ 429 → Show Rate Limit Notice
├─ Network Error → Show Offline Indicator
└─ Other → Show Error Toast with useApiError
```

## Requirements Validation

- **11.1**: API errors show user-friendly messages via useApiError hook
- **11.2**: Network errors detected via networkDetector and OfflineIndicator
- **11.3**: Loading states via LoadingSpinner, LoadingOverlay, and Skeleton components
- **11.4**: Success/error notifications via enhanced toast system
- **11.5**: Form validation errors via Form components and FormMessage
- **11.6**: 401 errors handled via axios interceptor with token refresh
- **11.7**: 429 rate limit errors handled via useApiError and RateLimitNotice
