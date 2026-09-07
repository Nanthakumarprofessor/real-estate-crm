/**
 * FollowUpSummary — upcoming and overdue follow-up counts.
 *
 * Overdue is styled in warning/danger to draw attention.
 */
import type { FollowUpStatistics } from '../../api/dashboardApi';

interface FollowUpSummaryProps {
  data: FollowUpStatistics;
}

export default function FollowUpSummary({ data }: FollowUpSummaryProps) {
  const hasOverdue = data.overdue > 0;

  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body">
        <h2 className="h6 fw-semibold mb-3 d-flex align-items-center gap-2">
          <i className="bi bi-clock-history text-warning" aria-hidden="true" />
          Follow-ups
        </h2>

        <div className="row g-2">
          {/* Upcoming */}
          <div className="col-6">
            <div className="p-3 rounded-3 bg-primary bg-opacity-10 text-center">
              <div className="fw-bold text-primary" style={{ fontSize: '1.5rem' }}>
                {data.upcoming}
              </div>
              <div className="d-flex align-items-center justify-content-center gap-1 mt-1">
                <i className="bi bi-calendar-event text-primary" style={{ fontSize: 12 }} aria-hidden="true" />
                <span className="text-muted small">Upcoming</span>
              </div>
            </div>
          </div>

          {/* Overdue — highlighted when > 0 */}
          <div className="col-6">
            <div
              className={`p-3 rounded-3 text-center ${
                hasOverdue ? 'bg-danger bg-opacity-10' : 'bg-secondary bg-opacity-10'
              }`}
            >
              <div
                className={`fw-bold ${hasOverdue ? 'text-danger' : 'text-secondary'}`}
                style={{ fontSize: '1.5rem' }}
              >
                {data.overdue}
              </div>
              <div className="d-flex align-items-center justify-content-center gap-1 mt-1">
                <i
                  className={`bi bi-exclamation-circle${hasOverdue ? '-fill' : ''} ${
                    hasOverdue ? 'text-danger' : 'text-secondary'
                  }`}
                  style={{ fontSize: 12 }}
                  aria-hidden="true"
                />
                <span className="text-muted small">Overdue</span>
              </div>
            </div>
          </div>
        </div>

        {/* Alert banner if overdue */}
        {hasOverdue && (
          <div className="alert alert-warning d-flex align-items-center gap-2 py-2 mt-3 mb-0 small">
            <i className="bi bi-exclamation-triangle-fill flex-shrink-0" aria-hidden="true" />
            <span>{data.overdue} overdue follow-up{data.overdue !== 1 ? 's' : ''} need attention.</span>
          </div>
        )}
      </div>
    </div>
  );
}
