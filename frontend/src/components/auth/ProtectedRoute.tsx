import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

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
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  // Check if user is authenticated
  if (!isAuthenticated) {
    // Redirect to login page, preserving the attempted location
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  // Check for required permission if specified
  if (requiredPermission && user) {
    // Simple permission check - can be extended based on requirements
    // For now, we'll check if user has admin role for admin-only routes
    if (requiredPermission === 'admin' && user.role !== 'admin') {
      // Redirect to dashboard if user doesn't have required permission
      return <Navigate to="/dashboard" replace />;
    }
  }

  // User is authenticated and has required permissions
  return <>{children}</>;
}
