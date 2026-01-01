/**
 * Performance Optimization Utilities
 * 
 * Collection of utilities for improving application performance:
 * - Debouncing and throttling
 * - Lazy loading helpers
 * - Performance monitoring
 */

/**
 * Debounce function - delays execution until after wait time has elapsed
 * Useful for search inputs, resize handlers, etc.
 * 
 * @param func - Function to debounce
 * @param wait - Wait time in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function - ensures function is called at most once per interval
 * Useful for scroll handlers, mouse move events, etc.
 * 
 * @param func - Function to throttle
 * @param limit - Time limit in milliseconds
 * @returns Throttled function
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Preload image - loads image in background
 * Useful for preloading images that will be shown later
 * 
 * @param src - Image source URL
 * @returns Promise that resolves when image is loaded
 */
export function preloadImage(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = src;
  });
}

/**
 * Preload multiple images
 * 
 * @param sources - Array of image source URLs
 * @returns Promise that resolves when all images are loaded
 */
export function preloadImages(sources: string[]): Promise<void[]> {
  return Promise.all(sources.map(preloadImage));
}

/**
 * Check if element is in viewport
 * Useful for manual lazy loading implementations
 * 
 * @param element - DOM element to check
 * @param offset - Offset in pixels (default: 0)
 * @returns True if element is in viewport
 */
export function isInViewport(element: HTMLElement, offset = 0): boolean {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= -offset &&
    rect.left >= -offset &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) + offset &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth) + offset
  );
}

/**
 * Measure performance of a function
 * Useful for identifying performance bottlenecks
 * 
 * @param name - Name for the measurement
 * @param func - Function to measure
 * @returns Result of the function
 */
export async function measurePerformance<T>(
  name: string,
  func: () => T | Promise<T>
): Promise<T> {
  const start = performance.now();
  const result = await func();
  const end = performance.now();
  
  if (import.meta.env.DEV) {
    console.log(`[Performance] ${name}: ${(end - start).toFixed(2)}ms`);
  }
  
  return result;
}

/**
 * Request idle callback wrapper with fallback
 * Schedules work to be done when browser is idle
 * 
 * @param callback - Function to call when idle
 * @param options - Options for idle callback
 */
export function requestIdleCallback(
  callback: () => void,
  options?: { timeout?: number }
): number {
  if ('requestIdleCallback' in window) {
    return window.requestIdleCallback(callback, options);
  }
  // Fallback for browsers that don't support requestIdleCallback
  return setTimeout(callback, 1) as unknown as number;
}

/**
 * Cancel idle callback wrapper with fallback
 * 
 * @param id - ID returned from requestIdleCallback
 */
export function cancelIdleCallback(id: number): void {
  if ('cancelIdleCallback' in window) {
    window.cancelIdleCallback(id);
  } else {
    clearTimeout(id);
  }
}

/**
 * Get Web Vitals metrics
 * Useful for monitoring Core Web Vitals
 */
export interface WebVitals {
  LCP?: number; // Largest Contentful Paint
  FID?: number; // First Input Delay
  CLS?: number; // Cumulative Layout Shift
  FCP?: number; // First Contentful Paint
  TTFB?: number; // Time to First Byte
}

/**
 * Report Web Vitals to console (dev mode only)
 * In production, you would send these to an analytics service
 * 
 * Note: This function requires the 'web-vitals' package to be installed.
 * Install with: npm install web-vitals
 * 
 * If not installed, this function will do nothing.
 */
export function reportWebVitals(onPerfEntry?: (metric: any) => void): void {
  if (onPerfEntry && typeof onPerfEntry === 'function') {
    // Uncomment the following code if you have web-vitals installed
    // import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
    //   getCLS(onPerfEntry);
    //   getFID(onPerfEntry);
    //   getFCP(onPerfEntry);
    //   getLCP(onPerfEntry);
    //   getTTFB(onPerfEntry);
    // }).catch(() => {
    //   if (import.meta.env.DEV) {
    //     console.log('[Performance] web-vitals not installed');
    //   }
    // });
    
    if (import.meta.env.DEV) {
      console.log('[Performance] reportWebVitals called. Install web-vitals package to enable metrics.');
    }
  }
}
