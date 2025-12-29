import { useEffect, useRef } from 'react';

interface LiveRegionProps {
  message: string;
  politeness?: 'polite' | 'assertive' | 'off';
  clearOnUnmount?: boolean;
}

/**
 * LiveRegion - Announces dynamic content updates to screen readers
 * Validates: Requirement 10.5
 * 
 * This component creates an ARIA live region that announces messages
 * to screen readers without requiring focus changes.
 * 
 * @param message - The message to announce
 * @param politeness - How urgently to announce (default: 'polite')
 * @param clearOnUnmount - Whether to clear the message when unmounting
 */
export function LiveRegion({ 
  message, 
  politeness = 'polite',
  clearOnUnmount = true 
}: LiveRegionProps) {
  const regionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      if (clearOnUnmount && regionRef.current) {
        regionRef.current.textContent = '';
      }
    };
  }, [clearOnUnmount]);

  return (
    <div
      ref={regionRef}
      role="status"
      aria-live={politeness}
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  );
}

/**
 * Hook for announcing messages to screen readers
 * Validates: Requirement 10.5
 * 
 * Usage:
 * const announce = useAnnouncer();
 * announce('Data loaded successfully');
 */
export function useAnnouncer() {
  const announcerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Create announcer element if it doesn't exist
    if (!announcerRef.current) {
      const announcer = document.createElement('div');
      announcer.setAttribute('role', 'status');
      announcer.setAttribute('aria-live', 'polite');
      announcer.setAttribute('aria-atomic', 'true');
      announcer.className = 'sr-only';
      document.body.appendChild(announcer);
      announcerRef.current = announcer;
    }

    return () => {
      if (announcerRef.current) {
        document.body.removeChild(announcerRef.current);
        announcerRef.current = null;
      }
    };
  }, []);

  const announce = (message: string, politeness: 'polite' | 'assertive' = 'polite') => {
    if (announcerRef.current) {
      announcerRef.current.setAttribute('aria-live', politeness);
      announcerRef.current.textContent = message;
      
      // Clear after a delay to allow re-announcement of the same message
      setTimeout(() => {
        if (announcerRef.current) {
          announcerRef.current.textContent = '';
        }
      }, 1000);
    }
  };

  return announce;
}
