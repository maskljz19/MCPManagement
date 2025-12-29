import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { FieldErrors } from 'react-hook-form';

interface FormErrorSummaryProps {
  errors: FieldErrors;
  title?: string;
}

/**
 * Form error summary component to display all form errors
 * Validates: Requirements 11.5
 */
export function FormErrorSummary({ errors, title = 'Please fix the following errors:' }: FormErrorSummaryProps) {
  const errorMessages = Object.entries(errors)
    .map(([field, error]) => {
      if (error && typeof error === 'object' && 'message' in error) {
        return {
          field,
          message: String(error.message),
        };
      }
      return null;
    })
    .filter((item): item is { field: string; message: string } => item !== null);

  if (errorMessages.length === 0) {
    return null;
  }

  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <ul className="mt-2 list-inside list-disc space-y-1">
          {errorMessages.map(({ field, message }) => (
            <li key={field} className="text-sm">
              {message}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}
