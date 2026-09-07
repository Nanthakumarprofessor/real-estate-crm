/**
 * LeadPipeline — visualises lead counts per stage as a horizontal bar chart.
 *
 * Each row: stage label | filled bar (width ∝ count / max) | count number
 *
 * All seven stages always render even if count = 0.
 * Bar width is relative to the highest stage count (not total) to keep
 * the visual meaningful at small numbers.
 *
 * Pure CSS — no chart library dependency.
 */
import type { LeadStatistics } from '../../api/dashboardApi';
import type { LeadStage } from '../../api/types';

interface StageConfig {
  key: LeadStage;
  label: string;
  color: string;   // Bootstrap bg-* color
}

const STAGES: StageConfig[] = [
  { key: 'NEW',         label: 'New',         color: 'secondary' },
  { key: 'CONTACTED',   label: 'Contacted',   color: 'info'      },
  { key: 'SITE_VISIT',  label: 'Site Visit',  color: 'primary'   },
  { key: 'INTERESTED',  label: 'Interested',  color: 'warning'   },
  { key: 'NEGOTIATION', label: 'Negotiation', color: 'orange'    },
  { key: 'BOOKED',      label: 'Booked',      color: 'success'   },
  { key: 'LOST',        label: 'Lost',        color: 'danger'    },
];

interface LeadPipelineProps {
  data: LeadStatistics;
}

export default function LeadPipeline({ data }: LeadPipelineProps) {
  const counts = STAGES.map((s) => data.by_stage[s.key] ?? 0);
  const max = Math.max(...counts, 1); // avoid division by zero

  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body">
        <h2 className="h6 fw-semibold mb-3 d-flex align-items-center gap-2">
          <i className="bi bi-funnel-fill text-primary" aria-hidden="true" />
          Lead Pipeline
        </h2>

        <div className="d-flex flex-column gap-2">
          {STAGES.map(({ key, label, color }, idx) => {
            const count = counts[idx];
            const pct = Math.round((count / max) * 100);
            // Map 'orange' to 'warning' for Bootstrap (we style NEGOTIATION differently)
            const bsColor = color === 'orange' ? 'warning' : color;

            return (
              <div key={key} className="d-flex align-items-center gap-2">
                {/* Stage label — fixed width */}
                <span
                  className="text-muted small flex-shrink-0 text-end"
                  style={{ width: 82, fontSize: 12 }}
                >
                  {label}
                </span>

                {/* Bar track */}
                <div
                  className="flex-grow-1 rounded-pill overflow-hidden"
                  style={{ height: 10, backgroundColor: 'var(--bs-gray-200)' }}
                  role="meter"
                  aria-valuenow={count}
                  aria-valuemin={0}
                  aria-valuemax={max}
                  aria-label={`${label}: ${count}`}
                >
                  <div
                    className={`h-100 rounded-pill bg-${bsColor}`}
                    style={{
                      width: `${pct}%`,
                      minWidth: count > 0 ? 6 : 0,
                      transition: 'width 0.4s ease',
                      opacity: key === 'LOST' ? 0.7 : 1,
                    }}
                  />
                </div>

                {/* Count */}
                <span
                  className="fw-semibold flex-shrink-0 text-end"
                  style={{ width: 24, fontSize: 13 }}
                >
                  {count}
                </span>
              </div>
            );
          })}
        </div>

        {/* Total */}
        <div className="mt-3 pt-2 border-top d-flex justify-content-between align-items-center">
          <span className="text-muted small">Total active leads</span>
          <span className="fw-bold text-primary">{data.total}</span>
        </div>
      </div>
    </div>
  );
}
