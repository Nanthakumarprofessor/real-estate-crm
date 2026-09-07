/**
 * PropertySummary — unit inventory breakdown.
 *
 * Shows total / available / booked with a segmented progress bar.
 * Pure CSS — no chart library.
 */
import type { PropertyStatistics } from '../../api/dashboardApi';

interface PropertySummaryProps {
  data: PropertyStatistics;
}

export default function PropertySummary({ data }: PropertySummaryProps) {
  const { total_units, available_units, booked_units } = data;
  const total = total_units || 1; // avoid divide-by-zero in bar width calc
  const availPct = Math.round((available_units / total) * 100);
  const bookedPct = Math.round((booked_units / total) * 100);

  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body">
        <h2 className="h6 fw-semibold mb-3 d-flex align-items-center gap-2">
          <i className="bi bi-buildings-fill text-success" aria-hidden="true" />
          Property Inventory
        </h2>

        {/* Segmented bar */}
        <div
          className="d-flex rounded-pill overflow-hidden mb-3"
          style={{ height: 12 }}
          role="img"
          aria-label={`${available_units} available, ${booked_units} booked out of ${total_units} total`}
        >
          <div
            className="bg-success"
            style={{ width: `${availPct}%`, transition: 'width 0.4s ease' }}
          />
          <div
            className="bg-danger"
            style={{ width: `${bookedPct}%`, transition: 'width 0.4s ease' }}
          />
          {/* Remainder (neither available nor booked — edge case) */}
          <div className="flex-grow-1 bg-secondary bg-opacity-15" />
        </div>

        {/* Legend stats */}
        <div className="row g-2 text-center">
          <div className="col-4">
            <div className="p-2 rounded-3 bg-secondary bg-opacity-10">
              <div className="fw-bold fs-5">{total_units}</div>
              <div className="text-muted" style={{ fontSize: 11 }}>Total</div>
            </div>
          </div>
          <div className="col-4">
            <div className="p-2 rounded-3 bg-success bg-opacity-10">
              <div className="fw-bold fs-5 text-success">{available_units}</div>
              <div className="text-muted" style={{ fontSize: 11 }}>Available</div>
            </div>
          </div>
          <div className="col-4">
            <div className="p-2 rounded-3 bg-danger bg-opacity-10">
              <div className="fw-bold fs-5 text-danger">{booked_units}</div>
              <div className="text-muted" style={{ fontSize: 11 }}>Booked</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
