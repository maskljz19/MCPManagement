import { useAuthStore } from '@/stores/authStore';
import { useMemo } from 'react';

/**
 * Permission definitions based on user roles
 */
const PERMISSIONS = {
  ADMIN: {
    mcps: { create: true, read: true, update: true, delete: true },
    knowledge: { create: true, read: true, update: true, delete: true },
    deployments: { create: true, read: true, update: true, delete: true },
    github: { create: true, read: true, update: true, delete: true },
    analysis: { create: true, read: true, update: true, delete: true },
    apiKeys: { create: true, read: true, update: true, delete: true },
  },
  DEVELOPER: {
    mcps: { create: true, read: true, update: true, delete: true },
    knowledge: { create: true, read: true, update: true, delete: true },
    deployments: { create: true, read: true, update: true, delete: true },
    github: { create: true, read: true, update: true, delete: true },
    analysis: { create: true, read: true, update: true, delete: true },
    apiKeys: { create: true, read: true, update: true, delete: true },
  },
  VIEWER: {
    mcps: { create: false, read: true, update: false, delete: false },
    knowledge: { create: false, read: true, update: false, delete: false },
    deployments: { create: false, read: true, update: false, delete: false },
    github: { create: false, read: true, update: false, delete: false },
    analysis: { create: false, read: true, update: false, delete: false },
    apiKeys: { create: false, read: true, update: false, delete: false },
  },
} as const;

type Resource = keyof typeof PERMISSIONS.ADMIN;
type Action = 'create' | 'read' | 'update' | 'delete';

/**
 * Hook to check user permissions
 */
export function usePermissions() {
  const user = useAuthStore((state) => state.user);

  const permissions = useMemo(() => {
    if (!user) {
      return PERMISSIONS.VIEWER;
    }
    return PERMISSIONS[user.role] || PERMISSIONS.VIEWER;
  }, [user]);

  const can = (resource: Resource, action: Action): boolean => {
    return permissions[resource]?.[action] ?? false;
  };

  const canCreate = (resource: Resource): boolean => can(resource, 'create');
  const canRead = (resource: Resource): boolean => can(resource, 'read');
  const canUpdate = (resource: Resource): boolean => can(resource, 'update');
  const canDelete = (resource: Resource): boolean => can(resource, 'delete');

  return {
    can,
    canCreate,
    canRead,
    canUpdate,
    canDelete,
    permissions,
    role: user?.role || 'VIEWER',
  };
}
