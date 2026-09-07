/**
 * BookingTable — responsive booking list.
 *
 * The backend only returns IDs.
 * We accept pre-enriched label maps from the parent (built by resolving
 * lead names and unit numbers once per page load) to avoid N+1 requests.
 *
 * Desktop: full table.
 * Mobile: stacked cards.
 */
import type { Booking } from '../../api/bookingsApi';

export interface EnrichmentMaps {
  /** lead_id → display name */
  leadNames: Record<number, string>;
  /** unit_id → display string e.g. "A-101 (Tower A, ABC Residency)" */
  unitLabels: Record<number, string>;
  /** user_id → display name */
  userNames: Record<number, string>;
}

const STATUS_BADGE: Record<string, string> = {
  CONFIRMED: 'bg-success',
  CANCELLED: 'bg-secondary',
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' });
}

function formatAmount(a: number | null) {
  if (a == null) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(a);
}

interface BookingTableProps {
  bookings: Booking[];
  enrichment: EnrichmentMaps;
  isAdmin: boolean;
  onView:   (booking: Booking) => void;
  onCancel: (booking: Booking) => void;
}

export default function BookingTable({
  bookings, enrichment, isAdmin, onView, onCancel,
}: BookingTableProps) {
  function leadName(id: number)  { return enrichment.leadNames[id]  ?? `Lead #${id}`; }
  function unitLabel(id: number) { return enrichment.unitLabels[id] ?? `Unit #${id}`; }

  // ── Mobile cards ──────────────────────────────────────────────────────────
  const cards = (
    <div className="d-md-none d-flex flex-column gap-2">
      {bookings.map((b) => (
        <div key={b.id} className="card border-0 shadow-sm"
          style={{ cursor: 'pointer' }}
          onClick={() => onView(b)}
          role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onView(b)}
          aria-label={`View booking #${b.id}`}>
          <div className="card-body py-3">
            <div className="d-flex justify-content-between align-items-start mb-1">
              <div className="fw-semibold small">{leadName(b.lead_id)}</div>
              <span className={`badge ${STATUS_BADGE[b.status]}`} style={{ fontSize: 10 }}>
                {b.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled'}
              </span>
            </div>
            <div className="text-muted small mb-1">{unitLabel(b.unit_id)}</div>
            <div className="d-flex justify-content-between align-items-center">
              <span className="text-muted small">{formatDate(b.booking_date)}</span>
              <span className="fw-medium small">{formatAmount(b.amount)}</span>
            </div>
            {/* Actions */}
            <div className="d-flex gap-2 mt-2" onClick={(e) => e.stopPropagation()} role="presentation">
              {isAdmin && b.status === 'CONFIRMED' && (
                <button type="button" className="btn btn-sm btn-outline-danger py-0 px-2"
                  onClick={() => onCancel(b)} aria-label={`Cancel booking for ${leadName(b.lead_id)}`}>
                  <i className="bi bi-x-circle me-1" aria-hidden="true" />Cancel
                </button>
              )}
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
            <th>Customer</th>
            <th>Unit</th>
            <th>Date</th>
            <th>Amount</th>
            <th>Status</th>
            {isAdmin && <th style={{ width: 100 }}>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {bookings.map((b) => (
            <tr key={b.id} style={{ cursor: 'pointer' }}>
              <td onClick={() => onView(b)} role="button" tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onView(b)}>
                <div className="fw-semibold">{leadName(b.lead_id)}</div>
              </td>
              <td className="small">{unitLabel(b.unit_id)}</td>
              <td className="small text-muted">{formatDate(b.booking_date)}</td>
              <td className="small fw-medium">{formatAmount(b.amount)}</td>
              <td>
                <span className={`badge ${STATUS_BADGE[b.status]}`} style={{ fontSize: 11 }}>
                  {b.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled'}
                </span>
              </td>
              {isAdmin && (
                <td>
                  {b.status === 'CONFIRMED' && (
                    <button type="button" className="btn btn-sm btn-outline-danger py-0 px-2"
                      onClick={(e) => { e.stopPropagation(); onCancel(b); }}
                      aria-label={`Cancel booking for ${leadName(b.lead_id)}`}>
                      <i className="bi bi-x-circle" aria-hidden="true" />
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return <>{cards}{table}</>;
}
