/**
 * UserTable — responsive user list.
 * Desktop: full table. Mobile: stacked cards.
 */
import type { CrmUser } from '../../api/usersApi';

const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'bg-danger',
  SALES: 'bg-success',
};

interface UserTableProps {
  users: CrmUser[];
  currentUserId: number;
  onView:       (user: CrmUser) => void;
  onEdit:       (user: CrmUser) => void;
  onDeactivate: (user: CrmUser) => void;
  onReactivate: (user: CrmUser) => void;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' });
}

export default function UserTable({
  users, currentUserId, onView, onEdit, onDeactivate, onReactivate,
}: UserTableProps) {

  function actions(u: CrmUser) {
    return (
      <div className="d-flex gap-1 flex-wrap">
        <button type="button" className="btn btn-sm btn-outline-secondary py-0 px-2"
          onClick={() => onView(u)} aria-label={`View ${u.name}`}>
          <i className="bi bi-eye" aria-hidden="true" />
        </button>
        <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2"
          onClick={() => onEdit(u)} aria-label={`Edit ${u.name}`}>
          <i className="bi bi-pencil" aria-hidden="true" />
        </button>
        {u.is_active ? (
          <button type="button" className="btn btn-sm btn-outline-warning py-0 px-2"
            onClick={() => onDeactivate(u)} aria-label={`Deactivate ${u.name}`}
            title="Deactivate">
            <i className="bi bi-person-dash" aria-hidden="true" />
          </button>
        ) : (
          <button type="button" className="btn btn-sm btn-outline-success py-0 px-2"
            onClick={() => onReactivate(u)} aria-label={`Reactivate ${u.name}`}
            title="Reactivate">
            <i className="bi bi-person-check" aria-hidden="true" />
          </button>
        )}
      </div>
    );
  }

  // ── Mobile cards ──────────────────────────────────────────────────────────
  const cards = (
    <div className="d-md-none d-flex flex-column gap-2">
      {users.map((u) => (
        <div key={u.id} className="card border-0 shadow-sm"
          style={{ cursor: 'pointer' }}
          onClick={() => onView(u)}
          role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onView(u)}
          aria-label={`View ${u.name}`}>
          <div className="card-body py-3">
            <div className="d-flex justify-content-between align-items-start mb-1">
              <div>
                <div className="fw-semibold">{u.name}</div>
                <div className="text-muted small">{u.email}</div>
              </div>
              <div className="d-flex flex-column align-items-end gap-1">
                <span className={`badge ${ROLE_BADGE[u.role]}`} style={{ fontSize: 10 }}>{u.role}</span>
                <span className={`badge ${u.is_active ? 'bg-success' : 'bg-secondary'}`} style={{ fontSize: 10 }}>
                  {u.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
            <div className="d-flex gap-2 mt-2" onClick={(e) => e.stopPropagation()} role="presentation">
              {actions(u)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  // ── Desktop table ─────────────────────────────────────────────────────────
  const table = (
    <div className="d-none d-md-block table-responsive">
      <table className="table table-hover align-middle mb-0">
        <thead className="table-light">
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Joined</th>
            <th style={{ width: 130 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} style={{ cursor: 'pointer' }}>
              <td onClick={() => onView(u)} role="button" tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onView(u)}>
                <div className="fw-semibold">
                  {u.name}
                  {u.id === currentUserId && (
                    <span className="badge bg-secondary ms-2" style={{ fontSize: 10 }}>You</span>
                  )}
                </div>
              </td>
              <td className="small text-muted">{u.email}</td>
              <td>
                <span className={`badge ${ROLE_BADGE[u.role]}`} style={{ fontSize: 11 }}>{u.role}</span>
              </td>
              <td>
                <span className={`badge ${u.is_active ? 'bg-success' : 'bg-secondary'}`} style={{ fontSize: 11 }}>
                  {u.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td className="small text-muted">{formatDate(u.created_at)}</td>
              <td onClick={(e) => e.stopPropagation()} role="presentation">
                {actions(u)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return <>{cards}{table}</>;
}
