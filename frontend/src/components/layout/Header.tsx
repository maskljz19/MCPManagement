import { Menu, Bell, LogOut, User, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuthStore } from '@/stores/authStore';
import { useWebSocketStore } from '@/stores/websocketStore';
import { useNavigate } from 'react-router-dom';
import { authService } from '@/services/authService';
import websocketClient from '@/services/websocketClient';
import { ThemeToggle } from '@/components/common/ThemeToggle';
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher';
import { useI18n } from '@/hooks/useI18n';

interface HeaderProps {
  onMenuClick: () => void;
}

/**
 * Header - Top navigation bar component
 * Provides breadcrumbs, notifications, and user menu
 * Validates: Requirements 10.1, 10.2, 10.3, 10.4
 * 
 * Accessibility Features:
 * - Proper header landmark with role="banner"
 * - Keyboard accessible menu button
 * - ARIA labels for icon buttons
 * - Focus management for dropdown menus
 * 
 * Logout functionality validates: Requirements 1.7, 8.6
 */
export function Header({ onMenuClick }: HeaderProps) {
  const { user, clearAuth } = useAuthStore();
  const { reset: resetWebSocket } = useWebSocketStore();
  const navigate = useNavigate();
  const { t } = useI18n();

  /**
   * Handle user logout
   * Requirements: 1.7, 8.6
   * - Calls logout API endpoint
   * - Clears authentication tokens
   * - Disconnects WebSocket connection
   * - Resets WebSocket store
   * - Redirects to login page
   */
  const handleLogout = async () => {
    try {
      // Call logout API endpoint
      await authService.logout();
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local cleanup even if API call fails
    }
    
    // Close WebSocket connection
    websocketClient.disconnect();
    
    // Clear tokens (already done in authService.logout, but ensure it's done)
    authService.clearTokens();
    
    // Update auth store
    clearAuth();
    
    // Reset WebSocket store
    resetWebSocket();
    
    // Redirect to login
    navigate('/auth/login');
  };

  return (
    <header 
      className="sticky top-0 z-30 h-16 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
      role="banner"
    >
      <div className="flex items-center justify-between h-full px-4 md:px-6">
        {/* Left side - Menu button (mobile) */}
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="lg:hidden focus-enhanced"
            aria-label={t('common.actions')}
            aria-expanded="false"
            aria-controls="sidebar-navigation"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>

          {/* Breadcrumbs or page title can go here */}
          <div className="hidden md:block">
            <h1 className="text-lg font-semibold">{t('nav.dashboard')}</h1>
          </div>
        </div>

        {/* Right side - Notifications and user menu */}
        <div className="flex items-center space-x-2" role="navigation" aria-label={t('common.actions')}>
          {/* Language switcher */}
          <div className="hidden md:flex">
            <LanguageSwitcher />
          </div>
          
          {/* Theme toggle */}
          <ThemeToggle />
          
          {/* Notifications */}
          <Button 
            variant="ghost" 
            size="icon" 
            className="focus-enhanced"
            aria-label={t('settings.notifications')}
          >
            <Bell className="h-5 w-5" aria-hidden="true" />
          </Button>

          {/* User menu */}
          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="ghost" 
                  className="flex items-center space-x-2 focus-enhanced"
                  aria-label={`${t('nav.profile')} - ${user.username}`}
                >
                  <div 
                    className="w-8 h-8 bg-primary rounded-full flex items-center justify-center"
                    aria-hidden="true"
                  >
                    <span className="text-primary-foreground text-sm font-medium">
                      {user.username.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="hidden md:inline-block">{user.username}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{user.username}</p>
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={() => navigate('/profile')}
                  className="focus-enhanced"
                >
                  <User className="mr-2 h-4 w-4" aria-hidden="true" />
                  <span>{t('nav.profile')}</span>
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={() => navigate('/settings')}
                  className="focus-enhanced"
                >
                  <Settings className="mr-2 h-4 w-4" aria-hidden="true" />
                  <span>{t('nav.settings')}</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={handleLogout} 
                  className="text-destructive focus-enhanced"
                >
                  <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
                  <span>{t('auth.logout')}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </header>
  );
}
