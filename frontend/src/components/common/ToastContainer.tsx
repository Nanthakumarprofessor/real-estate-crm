/**
 * ToastContainer — renders the toast notification stack.
 * Pair with the useToast hook.
 */
import type { ToastItem } from '../../hooks/useToast';

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}

export default function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;
  return (
    <div
      className="position-fixed top-0 end-0 p-3"
      style={{ zIndex: 1100 }}
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`toast show align-items-center text-white border-0 bg-${t.type} mb-2`}
          role="alert"
        >
          <div className="d-flex">
            <div className="toast-body small">{t.text}</div>
            <button
              type="button"
              className="btn-close btn-close-white me-2 m-auto"
              onClick={() => onDismiss(t.id)}
              aria-label="Close notification"
            />
          </div>
        </div>
      ))}
    </div>
  );
}
