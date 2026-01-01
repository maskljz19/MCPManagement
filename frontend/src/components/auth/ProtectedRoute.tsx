import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useEffect, useState } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
}

/**
 * ProtectedRoute component that guards routes requiring authentication
 * Redirects to login page if user is not authenticated
 * Validates: Requirements 1.8
 */
export function ProtectedRoute({ children, requiredPermission }: ProtectedRouteProps) {
  const { isAuthenticated, user, setAuth } = useAuthStore();
  const location = useLocation();
  const [isChecking, setIsChecking] = useState(true);
  const [authRestored, setAuthRestored] = useState(false);

  // Check and restore authentication state on mount (only once)
  useEffect(() => {
    const checkAuth = async () => {
      console.log('🔍 ProtectedRoute: Checking auth state...');
      console.log('  Current state:', { isAuthenticated, hasUser: !!user });
      
      // If already authenticated in store, we're good
      if (isAuthenticated && user) {
        console.log('✅ Already authenticated:', user.username);
        setAuthRestored(true);
        setIsChecking(false);
        return;
      }

      // Try to restore from localStorage
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');
      
      console.log('  Tokens in localStorage:', {
        hasAccessToken: !!accessToken,
        hasRefreshToken: !!refreshToken,
      });
      
      if (accessToken && refreshToken) {
        console.log('🔄 Found tokens in localStorage, attempting to restore...');
        
        // Try to decode user from token
        try {
          const payload = JSON.parse(atob(accessToken.split('.')[1]));
          const restoredUser = {
            id: payload.user_id,
            username: payload.username,
            email: '',
            role: payload.role || 'viewer',
            is_active: true,
            created_at: new Date().toISOString(),
          };
          
          console.log('✅ Restored user from token:', restoredUser.username);
          setAuth(restoredUser, accessToken, refreshToken);
          setAuthRestored(true);
        } catch (e) {
          console.error('❌ Failed to decode token:', e);
          // Clear invalid tokens
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('auth-storage');
        }
      } else {
        console.log('⚠️ No tokens found in localStorage');
      }
      
      setIsChecking(false);
    };

    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Show loading while checking auth
  if (isChecking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Check if user is authenticated (either from store or just restored)
  if (!isAuthenticated && !authRestored) {
    console.log('🚫 Not authenticated, redirecting to login');
    // Redirect to login page, preserving the attempted location
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  // Check for required permission if specified
  if (requiredPermission && user) {
    // Simple permission check - can be extended based on requirements
    // For now, we'll check if user has admin role for admin-only routes
    if (requiredPermission === 'admin' && user.role !== 'admin') {
      console.log('🚫 Insufficient permissions, redirecting to dashboard');
      // Redirect to dashboard if user doesn't have required permission
      return <Navigate to="/dashboard" replace />;
    }
  }

  // User is authenticated and has required permissions
  return <>{children}</>;
}
