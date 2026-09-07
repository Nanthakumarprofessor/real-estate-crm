/**
 * EmptyState — shown when a list or section has no data yet.
 */
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: string;
  title: string;
  message?: string;
  children?: ReactNode;
}

export default function EmptyState({ icon = 'bi-inbox', title, message, children }: EmptyStateProps) {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center py-5 text-center">
      <div
        className="d-flex align-items-center justify-content-center rounded-circle bg-secondary bg-opacity-10 mb-3"
        style={{ width: 64, height: 64 }}
      >
        <i className={`bi ${icon} fs-3 text-secondary`} aria-hidden="true" />
      </div>
      <h5 className="fw-semibold mb-1">{title}</h5>
      {message && <p className="text-muted small mb-3">{message}</p>}
      {children}
    </div>
  );
}
