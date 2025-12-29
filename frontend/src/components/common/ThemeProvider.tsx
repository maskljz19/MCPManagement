import { useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';

/**
 * Theme Provider Component
 * Requirements: 12.3
 * 
 * Initializes and manages theme on app load.
 * Restores theme preference from localStorage.
 */

interface ThemeProviderProps {
  children: React.ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme } = useTheme();

  // Initialize theme on mount
  useEffect(() => {
    const root = window.document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light', 'dark');
    
    // Determine the actual theme to apply
    let effectiveTheme = theme;
    
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      effectiveTheme = systemTheme;
    }
    
    // Apply theme class
    root.classList.add(effectiveTheme);
  }, [theme]);

  return <>{children}</>;
}
