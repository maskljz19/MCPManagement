# shadcn/ui Components

This directory contains the shadcn/ui component library setup for the MCP Platform frontend.

## Components Installed

The following base UI components have been installed and configured:

### Form Components
- **Button** - Versatile button component with multiple variants (default, secondary, destructive, outline, ghost, link)
- **Input** - Text input field with consistent styling
- **Label** - Form label component with proper accessibility
- **Textarea** - Multi-line text input
- **Select** - Dropdown select component with search and keyboard navigation

### Layout Components
- **Card** - Container component with header, content, and footer sections
- **Dialog** - Modal dialog component for overlays and confirmations
- **Dropdown Menu** - Context menu and dropdown component

### Feedback Components
- **Toast** - Notification system for user feedback
- **Toaster** - Toast container and provider
- **Badge** - Status indicators and labels
- **Skeleton** - Loading placeholder component

## Usage

Import components from the `@/components/ui` path:

```tsx
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';

function MyComponent() {
  const { toast } = useToast();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Example</CardTitle>
      </CardHeader>
      <CardContent>
        <Button onClick={() => toast({ title: 'Success!' })}>
          Click me
        </Button>
      </CardContent>
    </Card>
  );
}
```

## Theme Configuration

The theme is configured using CSS variables in `src/index.css`. The following color tokens are available:

- `background` / `foreground` - Base colors
- `primary` / `primary-foreground` - Primary action colors
- `secondary` / `secondary-foreground` - Secondary action colors
- `muted` / `muted-foreground` - Muted/disabled colors
- `accent` / `accent-foreground` - Accent colors
- `destructive` / `destructive-foreground` - Error/danger colors
- `border` - Border color
- `input` - Input border color
- `ring` - Focus ring color

Both light and dark mode themes are configured.

## Utilities

The `cn()` utility function from `@/lib/utils` is used throughout for conditional class merging:

```tsx
import { cn } from '@/lib/utils';

<div className={cn('base-class', condition && 'conditional-class')} />
```

## Adding New Components

To add more shadcn/ui components:

1. Visit https://ui.shadcn.com/docs/components
2. Copy the component code
3. Create a new file in this directory
4. Add the export to `index.ts`

## Dependencies

The following Radix UI primitives are used:

- `@radix-ui/react-dialog`
- `@radix-ui/react-dropdown-menu`
- `@radix-ui/react-label`
- `@radix-ui/react-select`
- `@radix-ui/react-slot`
- `@radix-ui/react-toast`

Additional utilities:

- `class-variance-authority` - For variant management
- `clsx` - For conditional classes
- `tailwind-merge` - For Tailwind class merging
- `lucide-react` - For icons
