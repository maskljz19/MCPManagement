import { Outlet } from 'react-router-dom';

/**
 * AuthLayout - Layout for authentication pages (login, register)
 * Provides centered layout with branding
 * Validates: Requirements 10.1, 10.2, 10.3, 10.5
 * 
 * Responsive Features:
 * - Mobile: Full-width with padding
 * - Tablet: Constrained width with more padding
 * - Desktop: Centered with maximum width
 * 
 * Accessibility Features:
 * - Semantic HTML with proper landmarks
 * - ARIA labels for regions
 */
export function AuthLayout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header with logo */}
      <header className="border-b" role="banner">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center">
          <div className="flex items-center space-x-2">
            <div 
              className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center"
              aria-hidden="true"
            >
              <span className="text-primary-foreground font-bold text-sm">MCP</span>
            </div>
            <span className="font-semibold text-lg sm:text-xl">平台</span>
          </div>
        </div>
      </header>

      {/* Main content - centered with responsive padding */}
      <main 
        className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8"
        role="main"
      >
        <div className="w-full max-w-md sm:max-w-lg">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-4 sm:py-6" role="contentinfo">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs sm:text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} MCP 平台. 保留所有权利.</p>
        </div>
      </footer>
    </div>
  );
}
