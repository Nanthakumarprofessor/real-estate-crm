/**
 * BookingDetails — offcanvas drawer showing full booking information.
 *
 * Consistent with LeadDetails and ProjectDetails patterns.
 */
import type { ReactNode } from 'react';
import type { Booking } from '../../api/bookingsApi';
import type { EnrichmentMaps } from './BookingTable';

interface BookingDetailsProps {
  booking: Booking;
  enrichment: EnrichmentMaps;
  isAdmin: boolean;
  onClose: () => void;
  onCancel: (booking: Booking) => void;
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function formatAmount(a: number | null) {
  if (a == null) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(a);
}

const STATUS_BADGE: Record<string, string> = {
  CONFIRMED: 'bg-success',
  CANCELLED: 'bg-secondary',
};

export default function BookingDetails({
  booking, enrichment, isAdmin, onClose, onCancel,
}: BookingDetailsProps) {
  const leadName  = enrichment.leadNames[booking.lead_id]  ?? `Lead #${booking.lead_id}`;
  const unitLabel = enrichment.unitLabels[booking.unit_id] ?? `Unit #${booking.unit_id}`;
  const bookedBy  = enrichment.userNames[booking.booked_by] ?? `User #${booking.booked_by}`;

  const rows: { label: string; value: ReactNode }[] = [
    { label: 'Customer',     value: leadName },
    { label: 'Unit',         value: unitLabel },
    { label: 'Amount',       value: formatAmount(booking.amount) },
    { label: 'Booking Date', value: formatDateTime(booking.booking_date) },
    {
      label: 'Status',
      value: (
        <span className={`badge ${STATUS_BADGE[booking.status]}`}>
          {booking.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled'}
        </span>
      ),
    },
    { label: 'Booked by',   value: bookedBy },
    { label: 'Created',     value: formatDateTime(booking.created_at) },
  ];

  return (
    <>
      <div className="offcanvas-backdrop fade show" onClick={onClose} aria-hidden="true" />
      <div className="offcanvas offcanvas-end show" tabIndex={-1} role="dialog"
        aria-label="Booking details" style={{ width: 'min(480px, 100vw)' }}>

        <div className="offcanvas-header border-bottom">
          <div className="d-flex align-items-center gap-2">
            <span className={`badge ${STATUS_BADGE[booking.status]}`}>
              {booking.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled'}
            </span>
            <h5 className="offcanvas-title mb-0">Booking #{booking.id}</h5>
          </div>
          <div className="d-flex align-items-center gap-2">
            {isAdmin && booking.status === 'CONFIRMED' && (
              <button type="button" className="btn btn-sm btn-outline-danger"
                onClick={() => onCancel(booking)}>
                <i className="bi bi-x-circle me-1" aria-hidden="true" />Cancel
              </button>
            )}
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
        </div>
      </div>
    </>
  );
}
