import { RouterProvider } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { router } from '@/router';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { OfflineIndicator } from '@/components/common/OfflineIndicator';
import { ThemeProvider } from '@/components/common/ThemeProvider';

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <RouterProvider router={router} />
        <Toaster />
        <OfflineIndicator />
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
