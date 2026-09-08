/**
 * ConfirmModal — reusable destructive-action confirmation dialog.
 */
interface ConfirmModalProps {
  title: string;
  message: string;
  subMessage?: string;
  confirmLabel?: string;
  error?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  title,
  message,
  subMessage,
  confirmLabel = 'Delete',
  error,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <div
      className="modal d-block"
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
    >
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable" style={{ maxWidth: 400 }}>
        <div className="modal-content border-0 shadow">
          <div className="modal-header border-0 pb-0">
            <div className="d-flex align-items-center gap-2">
              <div
                className="rounded-circle bg-danger bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0"
                style={{ width: 36, height: 36 }}
              >
                <i className="bi bi-trash3-fill text-danger" aria-hidden="true" />
              </div>
              <h5 className="modal-title mb-0">{title}</h5>
            </div>
          </div>
          <div className="modal-body pt-2">
            {error && (
              <div className="alert alert-danger small py-2 mb-2 d-flex align-items-center gap-2">
                <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />
                {error}
              </div>
            )}
            <p className="mb-1">{message}</p>
            {subMessage && <p className="text-muted small mb-0">{subMessage}</p>}
          </div>
          <div className="modal-footer border-0 pt-0">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={onCancel}
              disabled={busy}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={onConfirm}
              disabled={busy}
            >
              {busy ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                  {confirmLabel}…
                </>
              ) : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
