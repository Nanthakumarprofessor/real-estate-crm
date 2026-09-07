/**
 * UserDetails — offcanvas drawer showing full user information.
 * Consistent with LeadDetails, BookingDetails, ProjectDetails patterns.
 */
import type { ReactNode } from 'react';
import type { CrmUser } from '../../api/usersApi';

interface UserDetailsProps {
  user: CrmUser;
  currentUserId: number;
  onClose: () => void;
  onEdit: (user: CrmUser) => void;
  onDeactivate: (user: CrmUser) => void;
  onReactivate: (user: CrmUser) => void;
}

const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'bg-danger',
  SALES: 'bg-success',
};

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export default function UserDetails({
  user, currentUserId, onClose, onEdit, onDeactivate, onReactivate,
}: UserDetailsProps) {
  const isCurrentUser = user.id === currentUserId;

  const rows: { label: string; value: ReactNode }[] = [
    { label: 'Name',    value: <>{user.name}{isCurrentUser && <span className="badge bg-secondary ms-2" style={{ fontSize: 10 }}>You</span>}</> },
    { label: 'Email',   value: user.email },
    { label: 'Role',    value: <span className={`badge ${ROLE_BADGE[user.role]}`}>{user.role}</span> },
    { label: 'Status',  value: <span className={`badge ${user.is_active ? 'bg-success' : 'bg-secondary'}`}>{user.is_active ? 'Active' : 'Inactive'}</span> },
    { label: 'Created', value: formatDateTime(user.created_at) },
    { label: 'Updated', value: formatDateTime(user.updated_at) },
  ];

  return (
    <>
      <div className="offcanvas-backdrop fade show" onClick={onClose} aria-hidden="true" />
      <div className="offcanvas offcanvas-end show" tabIndex={-1} role="dialog"
        aria-label="User details" style={{ width: 'min(440px, 100vw)' }}>

        <div className="offcanvas-header border-bottom">
          <div className="d-flex align-items-center gap-2">
            <div className="d-flex align-items-center justify-content-center rounded-circle bg-primary text-white flex-shrink-0"
              style={{ width: 40, height: 40, fontSize: 16 }} aria-hidden="true">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h5 className="offcanvas-title mb-0">{user.name}</h5>
              <span className={`badge ${ROLE_BADGE[user.role]}`} style={{ fontSize: 10 }}>{user.role}</span>
            </div>
          </div>
          <div className="d-flex align-items-center gap-2">
            <button type="button" className="btn btn-sm btn-outline-primary"
              onClick={() => onEdit(user)} aria-label="Edit user">
              <i className="bi bi-pencil me-1" aria-hidden="true" />Edit
            </button>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close" />
          </div>
        </div>

        <div className="offcanvas-body">
          <dl className="row g-3 small">
            {rows.map(({ label, value }) => (
              <div key={label} className="col-12">
                <dt className="text-muted fw-normal mb-0">{label}</dt>
                <dd className="fw-medium mb-0">{value}</dd>
              </div>
            ))}
          </dl>

          {/* Deactivate / Reactivate action */}
          <hr />
          <div className="d-grid">
            {user.is_active ? (
              <button type="button" className="btn btn-outline-warning"
                onClick={() => onDeactivate(user)}
                disabled={isCurrentUser}
                title={isCurrentUser ? 'You cannot deactivate yourself' : undefined}>
                <i className="bi bi-person-dash me-2" aria-hidden="true" />
                Deactivate User
                {isCurrentUser && <span className="ms-2 text-muted small">(current user)</span>}
              </button>
            ) : (
              <button type="button" className="btn btn-outline-success"
                onClick={() => onReactivate(user)}>
                <i className="bi bi-person-check me-2" aria-hidden="true" />
                Reactivate User
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
