import { useState, useEffect } from 'react';

/**
 * useMediaQuery - Hook for responsive design
 * Validates: Requirements 10.1, 10.2, 10.3
 * 
 * Detects screen size changes and returns boolean for media query match
 * 
 * @param query - CSS media query string
 * @returns boolean indicating if the media query matches
 * 
 * @example
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * const isDesktop = useMediaQuery('(min-width: 1024px)');
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia(query).matches;
    }
    return false;
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQuery = window.matchMedia(query);
    
    // Update state if the match changes
    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Set initial value
    setMatches(mediaQuery.matches);

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [query]);

  return matches;
}

/**
 * Predefined breakpoint hooks for common screen sizes
 * Validates: Requirements 10.1, 10.2, 10.3
 */

// Mobile: < 640px
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 639px)');
}

// Tablet: 640px - 1023px
export function useIsTablet(): boolean {
  return useMediaQuery('(min-width: 640px) and (max-width: 1023px)');
}

// Desktop: >= 1024px
export function useIsDesktop(): boolean {
  return useMediaQuery('(min-width: 1024px)');
}

// Small screens (mobile + tablet): < 1024px
export function useIsSmallScreen(): boolean {
  return useMediaQuery('(max-width: 1023px)');
}

// Large screens (desktop): >= 1024px
export function useIsLargeScreen(): boolean {
  return useMediaQuery('(min-width: 1024px)');
}

// Prefers reduced motion (accessibility)
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

// Prefers dark mode
export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

/**
 * useBreakpoint - Returns current breakpoint name
 * Validates: Requirements 10.1, 10.2, 10.3
 * 
 * @returns 'mobile' | 'tablet' | 'desktop'
 */
export function useBreakpoint(): 'mobile' | 'tablet' | 'desktop' {
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
  
  if (isMobile) return 'mobile';
  if (isTablet) return 'tablet';
  return 'desktop';
}
