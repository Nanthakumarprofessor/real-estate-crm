/**
 * LoadingSpinner — centered full-area spinner for async loading states.
 */
interface LoadingSpinnerProps {
  /** If true, fills the full viewport height (used for page-level loading). */
  fullPage?: boolean;
}

export default function LoadingSpinner({ fullPage = false }: LoadingSpinnerProps) {
  const wrapClass = fullPage
    ? 'd-flex justify-content-center align-items-center vh-100'
    : 'd-flex justify-content-center align-items-center py-5';

  return (
    <div className={wrapClass}>
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Loading…</span>
      </div>
    </div>
  );
}
