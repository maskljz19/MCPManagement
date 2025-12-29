import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast';
import { useToast } from '@/hooks/use-toast';
import { useEffect } from 'react';

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, duration, ...props }) {
        return (
          <ToastWithDuration
            key={id}
            id={id}
            title={title}
            description={description}
            action={action}
            duration={duration}
            dismiss={dismiss}
            {...props}
          />
        );
      })}
      <ToastViewport />
    </ToastProvider>
  );
}

interface ToastWithDurationProps {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactElement;
  duration?: number;
  dismiss: (toastId?: string) => void;
  [key: string]: any;
}

function ToastWithDuration({
  id,
  title,
  description,
  action,
  duration,
  dismiss,
  ...props
}: ToastWithDurationProps) {
  useEffect(() => {
    if (duration) {
      const timer = setTimeout(() => {
        dismiss(id);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [id, duration, dismiss]);

  return (
    <Toast {...props}>
      <div className="grid gap-1">
        {title && <ToastTitle>{title}</ToastTitle>}
        {description && <ToastDescription>{description}</ToastDescription>}
      </div>
      {action}
      <ToastClose />
    </Toast>
  );
}
