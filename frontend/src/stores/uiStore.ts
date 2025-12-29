import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * UI Store
 * Requirements: 12.3
 * 
 * Manages UI state including theme preferences, sidebar state, and notifications.
 * Persists theme preferences to localStorage.
 */

type Theme = 'light' | 'dark' | 'system';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface UIState {
  // State
  theme: Theme;
  sidebarCollapsed: boolean;
  notifications: Notification[];
  isLoading: boolean;
  
  // Actions
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setLoading: (isLoading: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Initial state
      theme: 'system',
      sidebarCollapsed: false,
      notifications: [],
      isLoading: false,
      
      // Actions
      setTheme: (theme) =>
        set({ theme }),
      
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      
      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),
      
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            { ...notification, id: crypto.randomUUID() },
          ],
        })),
      
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
      
      clearNotifications: () =>
        set({ notifications: [] }),
      
      setLoading: (isLoading) =>
        set({ isLoading }),
    }),
    {
      name: 'ui-storage', // localStorage key
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
