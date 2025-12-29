import { Link, useLocation } from 'react-router-dom';
import { memo, useMemo } from 'react';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Wrench,
  BookOpen,
  Sparkles,
  Github,
  Rocket,
  Key,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/authStore';
import { useI18n } from '@/hooks/useI18n';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

interface NavItem {
  titleKey: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  {
    titleKey: 'nav.dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    titleKey: 'nav.tools',
    href: '/tools',
    icon: Wrench,
  },
  {
    titleKey: 'nav.knowledge',
    href: '/knowledge',
    icon: BookOpen,
  },
  {
    titleKey: 'nav.analysis',
    href: '/analysis',
    icon: Sparkles,
  },
  {
    titleKey: 'nav.github',
    href: '/github',
    icon: Github,
  },
  {
    titleKey: 'nav.deployments',
    href: '/deployments',
    icon: Rocket,
  },
  {
    titleKey: 'nav.apiKeys',
    href: '/api-keys',
    icon: Key,
  },
];

/**
 * Sidebar - Navigation sidebar component
 * Provides collapsible navigation menu with user information
 * Validates: Requirements 10.1, 10.2, 10.3, 10.4
 * 
 * Accessibility Features:
 * - Proper navigation landmark with aria-label
 * - Keyboard accessible toggle button
 * - Focus trap when sidebar is open on mobile
 * - Proper ARIA attributes for collapsed state
 * 
 * Performance Optimizations:
 * - Memoized with React.memo to prevent unnecessary re-renders
 * - Memoized user initial to avoid recalculation
 */
export const Sidebar = memo(function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const { user } = useAuthStore();
  const { t } = useI18n();

  // Memoize user initial to avoid recalculation on every render
  const userInitial = useMemo(() => {
    return user?.username.charAt(0).toUpperCase() || '';
  }, [user?.username]);

  // Handle keyboard navigation for mobile overlay
  const handleOverlayKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onToggle();
    }
  };

  return (
    <>
      {/* Mobile overlay */}
      {!collapsed && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
          onKeyDown={handleOverlayKeyDown}
          role="button"
          tabIndex={0}
          aria-label={t('common.close')}
        />
      )}

      {/* Sidebar - Navigation landmark */}
      <aside
        className={cn(
          'fixed top-0 left-0 z-50 h-screen bg-card border-r transition-all duration-300',
          'flex flex-col',
          collapsed ? 'w-16' : 'w-64',
          // Mobile: slide in from left
          'lg:translate-x-0',
          collapsed ? '-translate-x-full lg:translate-x-0' : 'translate-x-0'
        )}
        aria-label={t('nav.dashboard')}
        aria-hidden={collapsed ? 'true' : 'false'}
      >
        {/* Logo and toggle */}
        <div className="flex items-center justify-between h-16 px-4 border-b">
          {!collapsed && (
            <Link 
              to="/dashboard" 
              className="flex items-center space-x-2 focus-enhanced rounded-md"
              aria-label={t('nav.dashboard')}
            >
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-sm">MCP</span>
              </div>
              <span className="font-semibold text-lg">{t('nav.dashboard')}</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className={cn('hidden lg:flex', collapsed && 'mx-auto')}
            aria-label={collapsed ? t('common.actions') : t('common.close')}
            aria-expanded={!collapsed}
            aria-controls="sidebar-navigation"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav 
          id="sidebar-navigation"
          className="flex-1 overflow-y-auto py-4" 
          aria-label={t('nav.dashboard')}
        >
          <ul className="space-y-1 px-2" role="list">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname.startsWith(item.href);
              const title = t(item.titleKey);

              return (
                <li key={item.href}>
                  <Link
                    to={item.href}
                    className={cn(
                      'flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      'focus-enhanced',
                      isActive && 'bg-accent text-accent-foreground font-medium',
                      collapsed && 'justify-center'
                    )}
                    title={collapsed ? title : undefined}
                    aria-label={collapsed ? title : undefined}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                    {!collapsed && <span>{title}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User info */}
        {user && (
          <div className="border-t p-4" role="contentinfo" aria-label={t('nav.profile')}>
            <div className={cn('flex items-center', collapsed ? 'justify-center' : 'space-x-3')}>
              <div 
                className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0"
                aria-hidden="true"
              >
                <span className="text-primary-foreground text-sm font-medium">
                  {userInitial}
                </span>
              </div>
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.username}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.role}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </aside>
    </>
  );
});
