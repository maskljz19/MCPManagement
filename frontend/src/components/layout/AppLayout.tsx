import { Outlet } from 'react-router-dom';
import { useState, useCallback, memo } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useWebSocket } from '@/hooks/useWebSocket';

/**
 * AppLayout - Main application layout with sidebar and header
 * Provides responsive layout for authenticated pages
 * Validates: Requirements 10.1, 10.2, 10.3, 10.4
 * 
 * Accessibility Features:
 * - Skip to content link for keyboard navigation (Requirement 10.4)
 * - Proper landmark regions (main, navigation, header)
 * - Focus management for sidebar toggle
 * 
 * WebSocket Integration:
 * - Requirements 8.1: Establishes WebSocket connection when user is authenticated
 * - Requirements 8.2: Subscribes to relevant events
 * - Requirements 8.5: Handles automatic reconnection
 * 
 * Performance Optimizations:
 * - Memoized toggle handler to prevent unnecessary re-renders
 * - Optimized with useCallback for stable function references
 */
export const AppLayout = memo(function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Initialize WebSocket connection for authenticated users
  // This ensures WebSocket is connected when app loads or page is refreshed
  useWebSocket();

  // Memoize toggle handler to prevent recreation on every render
  const handleToggle = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Skip to content link for keyboard navigation - Requirement 10.4 */}
      <a 
        href="#main-content" 
        className="skip-to-content"
        aria-label="跳转到主内容"
      >
        跳转到主内容
      </a>

      {/* Sidebar - Navigation landmark */}
      <Sidebar collapsed={sidebarCollapsed} onToggle={handleToggle} />

      {/* Main content area */}
      <div
        className={`transition-all duration-300 ${
          sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'
        }`}
      >
        {/* Header */}
        <Header onMenuClick={handleToggle} />

        {/* Page content - Main landmark with id for skip link */}
        <main 
          id="main-content" 
          className="p-4 md:p-6 lg:p-8"
          tabIndex={-1}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
});
