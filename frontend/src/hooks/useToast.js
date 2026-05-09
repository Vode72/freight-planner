// src/hooks/useToast.js
import { useToastContext } from '../context/ToastContext';
 
export function useToast() {
  const { addToast } = useToastContext();
  return {
    success: (message, duration) => addToast({ message, type: 'success', duration }),
    error:   (message, duration) => addToast({ message, type: 'error',   duration }),
    warning: (message, duration) => addToast({ message, type: 'warning', duration }),
    info:    (message, duration) => addToast({ message, type: 'info',    duration }),
  };
}