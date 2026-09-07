/**
 * BookingSummary — confirmed and cancelled booking counts.
 */
import type { BookingStatistics } from '../../api/dashboardApi';

interface BookingSummaryProps {
  data: BookingStatistics;
}

export default function BookingSummary({ data }: BookingSummaryProps) {
  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body">
        <h2 className="h6 fw-semibold mb-3 d-flex align-items-center gap-2">
          <i className="bi bi-calendar-check-fill text-info" aria-hidden="true" />
          Booking Summary
        </h2>

        <div className="row g-2">
          {/* Confirmed */}
          <div className="col-6">
            <div className="p-3 rounded-3 bg-success bg-opacity-10 text-center">
              <div className="fw-bold text-success" style={{ fontSize: '1.5rem' }}>
                {data.confirmed}
              </div>
              <div className="d-flex align-items-center justify-content-center gap-1 mt-1">
                <i className="bi bi-check-circle-fill text-success" style={{ fontSize: 12 }} aria-hidden="true" />
                <span className="text-muted small">Confirmed</span>
              </div>
            </div>
          </div>

          {/* Cancelled */}
          <div className="col-6">
            <div className="p-3 rounded-3 bg-secondary bg-opacity-10 text-center">
              <div className="fw-bold text-secondary" style={{ fontSize: '1.5rem' }}>
                {data.cancelled}
              </div>
              <div className="d-flex align-items-center justify-content-center gap-1 mt-1">
                <i className="bi bi-x-circle-fill text-secondary" style={{ fontSize: 12 }} aria-hidden="true" />
                <span className="text-muted small">Cancelled</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
