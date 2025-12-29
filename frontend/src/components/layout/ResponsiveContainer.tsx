import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface ResponsiveContainerProps {
  children: ReactNode;
  className?: string;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

/**
 * ResponsiveContainer - Responsive container component
 * Validates: Requirements 10.1, 10.2, 10.3
 * 
 * Provides consistent responsive padding and max-width across different screen sizes
 * 
 * @param children - Child elements
 * @param className - Additional CSS classes
 * @param maxWidth - Maximum width constraint
 * @param padding - Responsive padding size
 */
export function ResponsiveContainer({
  children,
  className,
  maxWidth = 'full',
  padding = 'md',
}: ResponsiveContainerProps) {
  const maxWidthClasses = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    '2xl': 'max-w-screen-2xl',
    full: 'max-w-full',
  };

  const paddingClasses = {
    none: '',
    sm: 'px-2 sm:px-4',
    md: 'px-4 sm:px-6 lg:px-8',
    lg: 'px-6 sm:px-8 lg:px-12',
  };

  return (
    <div
      className={cn(
        'w-full mx-auto',
        maxWidthClasses[maxWidth],
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  );
}

interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
  cols?: {
    mobile?: 1 | 2;
    tablet?: 1 | 2 | 3;
    desktop?: 1 | 2 | 3 | 4 | 5 | 6;
  };
  gap?: 'sm' | 'md' | 'lg';
}

/**
 * ResponsiveGrid - Responsive grid layout component
 * Validates: Requirements 10.1, 10.2, 10.3
 * 
 * Provides responsive grid layout with configurable columns per breakpoint
 * 
 * @param children - Grid items
 * @param className - Additional CSS classes
 * @param cols - Number of columns per breakpoint
 * @param gap - Gap size between grid items
 */
export function ResponsiveGrid({
  children,
  className,
  cols = { mobile: 1, tablet: 2, desktop: 3 },
  gap = 'md',
}: ResponsiveGridProps) {
  const mobileColsClass = cols.mobile === 2 ? 'grid-cols-2' : 'grid-cols-1';
  const tabletColsClass = cols.tablet ? `md:grid-cols-${cols.tablet}` : '';
  const desktopColsClass = cols.desktop ? `lg:grid-cols-${cols.desktop}` : '';

  const gapClasses = {
    sm: 'gap-2 md:gap-3',
    md: 'gap-4 md:gap-6',
    lg: 'gap-6 md:gap-8',
  };

  return (
    <div
      className={cn(
        'grid',
        mobileColsClass,
        tabletColsClass,
        desktopColsClass,
        gapClasses[gap],
        className
      )}
    >
      {children}
    </div>
  );
}

interface ResponsiveStackProps {
  children: ReactNode;
  className?: string;
  direction?: 'vertical' | 'horizontal-on-desktop';
  spacing?: 'sm' | 'md' | 'lg';
}

/**
 * ResponsiveStack - Responsive stack layout component
 * Validates: Requirements 10.1, 10.2, 10.3
 * 
 * Stacks elements vertically on mobile, optionally horizontal on desktop
 * 
 * @param children - Stack items
 * @param className - Additional CSS classes
 * @param direction - Stack direction behavior
 * @param spacing - Space between items
 */
export function ResponsiveStack({
  children,
  className,
  direction = 'vertical',
  spacing = 'md',
}: ResponsiveStackProps) {
  const spacingClasses = {
    sm: 'space-y-2 md:space-y-3',
    md: 'space-y-4 md:space-y-6',
    lg: 'space-y-6 md:space-y-8',
  };

  const directionClasses =
    direction === 'horizontal-on-desktop'
      ? 'flex flex-col lg:flex-row lg:space-y-0 lg:space-x-6'
      : 'flex flex-col';

  return (
    <div
      className={cn(
        directionClasses,
        direction === 'vertical' && spacingClasses[spacing],
        className
      )}
    >
      {children}
    </div>
  );
}
