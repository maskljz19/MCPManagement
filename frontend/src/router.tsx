import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { AppLayout } from '@/components/layout/AppLayout';
import { AuthLayout } from '@/components/layout/AuthLayout';

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('@/features/dashboard/Dashboard'));
const Login = lazy(() => import('@/features/auth/Login'));
const Register = lazy(() => import('@/features/auth/Register'));
const ToolList = lazy(() => import('@/features/tools/ToolList'));
const ToolDetail = lazy(() => import('@/features/tools/ToolDetail'));
const ToolForm = lazy(() => import('@/features/tools/ToolForm'));
const Knowledge = lazy(() => import('@/features/knowledge/Knowledge'));
const Analysis = lazy(() => import('@/features/analysis/Analysis'));
const GitHub = lazy(() => import('@/features/github/GitHub'));
const Deployments = lazy(() => import('@/features/deployments/Deployments'));
const DeploymentNew = lazy(() => import('@/features/deployments/DeploymentNew'));
const DeploymentDetail = lazy(() => import('@/features/deployments/DeploymentDetail'));
const APIKeys = lazy(() => import('@/features/api-keys/APIKeys'));

// Loading fallback component
const LoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
  </div>
);

// Wrapper for lazy loaded components with Suspense
const LazyPage = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<LoadingFallback />}>{children}</Suspense>
);

export const router = createBrowserRouter([
  {
    path: '/auth',
    element: (
      <LazyPage>
        <AuthLayout />
      </LazyPage>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/auth/login" replace />,
      },
      {
        path: 'login',
        element: (
          <LazyPage>
            <Login />
          </LazyPage>
        ),
      },
      {
        path: 'register',
        element: (
          <LazyPage>
            <Register />
          </LazyPage>
        ),
      },
    ],
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: (
          <LazyPage>
            <Dashboard />
          </LazyPage>
        ),
      },
      {
        path: 'tools',
        children: [
          {
            index: true,
            element: (
              <LazyPage>
                <ToolList />
              </LazyPage>
            ),
          },
          {
            path: 'new',
            element: (
              <LazyPage>
                <ToolForm />
              </LazyPage>
            ),
          },
          {
            path: ':id',
            element: (
              <LazyPage>
                <ToolDetail />
              </LazyPage>
            ),
          },
          {
            path: ':id/edit',
            element: (
              <LazyPage>
                <ToolForm />
              </LazyPage>
            ),
          },
        ],
      },
      {
        path: 'knowledge',
        element: (
          <LazyPage>
            <Knowledge />
          </LazyPage>
        ),
      },
      {
        path: 'analysis',
        element: (
          <LazyPage>
            <Analysis />
          </LazyPage>
        ),
      },
      {
        path: 'github',
        element: (
          <LazyPage>
            <GitHub />
          </LazyPage>
        ),
      },
      {
        path: 'deployments',
        children: [
          {
            index: true,
            element: (
              <LazyPage>
                <Deployments />
              </LazyPage>
            ),
          },
          {
            path: 'new',
            element: (
              <LazyPage>
                <DeploymentNew />
              </LazyPage>
            ),
          },
          {
            path: ':id',
            element: (
              <LazyPage>
                <DeploymentDetail />
              </LazyPage>
            ),
          },
        ],
      },
      {
        path: 'api-keys',
        element: (
          <LazyPage>
            <APIKeys />
          </LazyPage>
        ),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
