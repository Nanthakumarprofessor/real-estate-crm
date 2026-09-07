/**
 * LeadTable — responsive lead list with action buttons.
 *
 * Desktop: full table.
 * Mobile/tablet: cards stacked vertically (via d-md-none / d-none d-md-table).
 */
import type { Lead, UserOption } from '../../api/leadsApi';
import { STAGE_BADGE, STAGE_LABEL, SOURCE_LABEL } from './leadConstants';

interface LeadTableProps {
  leads: Lead[];
  isAdmin: boolean;
  currentUserId: number;
  users: UserOption[];
  onView:   (lead: Lead) => void;
  onEdit:   (lead: Lead) => void;
  onDelete: (lead: Lead) => void;
}

export default function LeadTable({
  leads,
  isAdmin,
  currentUserId,
  users,
  onView,
  onEdit,
  onDelete,
}: LeadTableProps) {
  function assigneeName(assignedTo: number | null): string {
    if (assignedTo == null) return 'Unassigned';
    const u = users.find((u) => u.id === assignedTo);
    return u ? u.name : `#${assignedTo}`;
  }

  // ── Mobile card view ──────────────────────────────────────────────────────
  const cardList = (
    <div className="d-md-none d-flex flex-column gap-2">
      {leads.map((lead) => {
        const canEdit = isAdmin || lead.assigned_to === currentUserId;
        return (
          <div
            key={lead.id}
            className="card border-0 shadow-sm"
            style={{ cursor: 'pointer' }}
            onClick={() => onView(lead)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onView(lead)}
            aria-label={`View lead ${lead.name}`}
          >
            <div className="card-body py-3">
              <div className="d-flex justify-content-between align-items-start mb-1">
                <div>
                  <div className="fw-semibold">{lead.name}</div>
                  {lead.email && <div className="text-muted small">{lead.email}</div>}
                </div>
                <span className={`badge ${STAGE_BADGE[lead.stage]}`} style={{ fontSize: 10 }}>
                  {STAGE_LABEL[lead.stage]}
                </span>
              </div>
              <div className="small text-muted">
                {lead.phone && <span className="me-3">{lead.phone}</span>}
                {lead.source && <span>{SOURCE_LABEL[lead.source]}</span>}
              </div>
              <div className="small text-muted mt-1">
                Assigned: {assigneeName(lead.assigned_to)}
              </div>
              {/* Actions */}
              <div className="d-flex gap-2 mt-2" onClick={(e) => e.stopPropagation()} role="presentation">
                {canEdit && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary py-0 px-2"
                    onClick={() => onEdit(lead)}
                    aria-label={`Edit ${lead.name}`}
                  >
                    <i className="bi bi-pencil" aria-hidden="true" />
                  </button>
                )}
                {isAdmin && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger py-0 px-2"
                    onClick={() => onDelete(lead)}
                    aria-label={`Delete ${lead.name}`}
                  >
                    <i className="bi bi-trash3" aria-hidden="true" />
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );

  // ── Desktop table view ────────────────────────────────────────────────────
  const desktopTable = (
    <div className="d-none d-md-block table-responsive">
      <table className="table table-hover align-middle mb-0">
        <thead className="table-light">
          <tr>
            <th scope="col">Lead</th>
            <th scope="col">Phone</th>
            <th scope="col">Source</th>
            <th scope="col">Stage</th>
            <th scope="col">Assigned To</th>
            <th scope="col" style={{ width: 96 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => {
            const canEdit = isAdmin || lead.assigned_to === currentUserId;
            return (
              <tr key={lead.id} style={{ cursor: 'pointer' }}>
                <td
                  onClick={() => onView(lead)}
                  aria-label={`View ${lead.name}`}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && onView(lead)}
                  role="button"
                >
                  <div className="fw-semibold">{lead.name}</div>
                  {lead.email && <div className="text-muted small">{lead.email}</div>}
                </td>
                <td className="small text-muted">{lead.phone ?? '—'}</td>
                <td className="small">{lead.source ? SOURCE_LABEL[lead.source] : '—'}</td>
                <td>
                  <span className={`badge ${STAGE_BADGE[lead.stage]}`} style={{ fontSize: 11 }}>
                    {STAGE_LABEL[lead.stage]}
                  </span>
                </td>
                <td className="small">{assigneeName(lead.assigned_to)}</td>
                <td>
                  <div className="d-flex gap-1">
                    {canEdit && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-primary py-0 px-2"
                        onClick={(e) => { e.stopPropagation(); onEdit(lead); }}
                        aria-label={`Edit ${lead.name}`}
                      >
                        <i className="bi bi-pencil" aria-hidden="true" />
                      </button>
                    )}
                    {isAdmin && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger py-0 px-2"
                        onClick={(e) => { e.stopPropagation(); onDelete(lead); }}
                        aria-label={`Delete ${lead.name}`}
                      >
                        <i className="bi bi-trash3" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <>
      {cardList}
      {desktopTable}
    </>
  );
}
