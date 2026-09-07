/**
 * LeadDetails — offcanvas drawer showing full lead info, notes, follow-ups.
 *
 * Opens by sliding in from the right.
 * Contains LeadNotes and LeadFollowUps as sub-sections.
 */
import type { Lead } from '../../api/leadsApi';
import type { UserOption } from '../../api/leadsApi';
import { STAGE_BADGE, STAGE_LABEL, SOURCE_LABEL } from './leadConstants';
import LeadNotes from './LeadNotes';
import LeadFollowUps from './LeadFollowUps';

interface LeadDetailsProps {
  lead: Lead;
  currentUserId: number;
  isAdmin: boolean;
  users: UserOption[];
  onClose: () => void;
  onEdit: (lead: Lead) => void;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' });
}

export default function LeadDetails({
  lead,
  currentUserId,
  isAdmin,
  users,
  onClose,
  onEdit,
}: LeadDetailsProps) {
  const assignee = users.find((u) => u.id === lead.assigned_to);

  return (
    <>
      {/* Backdrop */}
      <div
        className="offcanvas-backdrop fade show"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        className="offcanvas offcanvas-end show"
        tabIndex={-1}
        role="dialog"
        aria-label="Lead details"
        style={{ width: 'min(520px, 100vw)' }}
      >
        {/* Header */}
        <div className="offcanvas-header border-bottom">
          <div className="d-flex align-items-center gap-2">
            <span className={`badge ${STAGE_BADGE[lead.stage]}`}>
              {STAGE_LABEL[lead.stage]}
            </span>
            <h5 className="offcanvas-title mb-0">{lead.name}</h5>
          </div>
          <div className="d-flex align-items-center gap-2">
            {(isAdmin || lead.assigned_to === currentUserId) && (
              <button
                type="button"
                className="btn btn-sm btn-outline-primary"
                onClick={() => onEdit(lead)}
                aria-label="Edit lead"
              >
                <i className="bi bi-pencil me-1" aria-hidden="true" />
                Edit
              </button>
            )}
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close" />
          </div>
        </div>

        {/* Body — scrollable */}
        <div className="offcanvas-body overflow-auto">

          {/* Lead info */}
          <section className="mb-4">
            <h6 className="fw-semibold mb-3 d-flex align-items-center gap-2">
              <i className="bi bi-person-fill text-primary" aria-hidden="true" />
              Lead Information
            </h6>
            <dl className="row row-cols-2 g-2 mb-0 small">
              {[
                { label: 'Name',     value: lead.name },
                { label: 'Email',    value: lead.email ?? '—' },
                { label: 'Phone',    value: lead.phone ?? '—' },
                { label: 'Source',   value: lead.source ? SOURCE_LABEL[lead.source] : '—' },
                { label: 'Stage',    value: <span className={`badge ${STAGE_BADGE[lead.stage]}`}>{STAGE_LABEL[lead.stage]}</span> },
                { label: 'Assigned', value: assignee ? `${assignee.name}` : lead.assigned_to ? `User #${lead.assigned_to}` : 'Unassigned' },
                { label: 'Created',  value: formatDate(lead.created_at) },
                { label: 'Status',   value: lead.is_active ? <span className="text-success fw-medium">Active</span> : <span className="text-danger fw-medium">Inactive</span> },
              ].map(({ label, value }) => (
                <div key={label} className="col">
                  <dt className="text-muted fw-normal">{label}</dt>
                  <dd className="fw-medium mb-0">{value}</dd>
                </div>
              ))}
            </dl>
          </section>

          <hr />

          {/* Notes */}
          <section className="mb-4">
            <LeadNotes
              leadId={lead.id}
              currentUserId={currentUserId}
              isAdmin={isAdmin}
            />
          </section>

          <hr />

          {/* Follow-ups */}
          <section>
            <LeadFollowUps leadId={lead.id} />
          </section>
        </div>
      </div>
    </>
  );
}
