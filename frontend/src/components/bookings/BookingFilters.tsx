/**
 * BookingFilters — status filter for the booking list.
 *
 * Backend supports filtering by status, lead_id, unit_id.
 * For this UI we expose the status filter (most useful for CRM users).
 */
import type { BookingStatus } from '../../api/bookingsApi';

interface BookingFiltersProps {
  status: BookingStatus | '';
  onStatusChange: (v: BookingStatus | '') => void;
}

export default function BookingFilters({ status, onStatusChange }: BookingFiltersProps) {
  return (
    <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
      <select
        className="form-select form-select-sm"
        style={{ maxWidth: 180 }}
        value={status}
        onChange={(e) => onStatusChange(e.target.value as BookingStatus | '')}
        aria-label="Filter by booking status"
      >
        <option value="">All Status</option>
        <option value="CONFIRMED">Confirmed</option>
        <option value="CANCELLED">Cancelled</option>
      </select>

      {status && (
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
          onClick={() => onStatusChange('')}
        >
          <i className="bi bi-x" aria-hidden="true" />Clear
        </button>
      )}
    </div>
  );
}
