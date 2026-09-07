/**
 * useToast — lightweight toast notification state.
 *
 * Usage:
 *   const { toasts, toast, dismissToast } = useToast();
 *   toast('Lead created.', 'success');
 *
 * Toasts auto-dismiss after 3500 ms.
 */
import { useCallback, useRef, useState } from 'react';

export interface ToastItem {
  id: number;
  text: string;
  type: 'success' | 'danger';
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const toast = useCallback((text: string, type: 'success' | 'danger' = 'success') => {
    const id = ++counter.current;
    setToasts((p) => [...p, { id, text, type }]);
    setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), 3500);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((p) => p.filter((t) => t.id !== id));
  }, []);

  return { toasts, toast, dismissToast };
}
