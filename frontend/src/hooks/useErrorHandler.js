import { useCallback } from "react";
import { toast } from "sonner";

/**
 * Custom hook for consistent error handling
 * Eliminates duplication across 100+ error handlers
 */
export function useErrorHandler() {
  const handleError = useCallback(
    (error, defaultMessage = "An error occurred") => {
      const message =
        error?.message || error?.response?.data?.message || defaultMessage;
      console.error(message, error);
      toast.error(message);
      return message;
    },
    []
  );

  const handleSuccess = useCallback((message = "Operation successful") => {
    toast.success(message);
  }, []);

  const handleValidationError = useCallback((errors) => {
    if (Object.keys(errors).length > 0) {
      const firstError = Object.values(errors)[0];
      toast.error(firstError);
      return false;
    }
    return true;
  }, []);

  return {
    handleError,
    handleSuccess,
    handleValidationError,
  };
}
