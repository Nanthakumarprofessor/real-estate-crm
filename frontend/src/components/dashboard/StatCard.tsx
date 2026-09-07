/**
 * StatCard — single KPI metric card.
 *
 * Used for the four top-row summary numbers.
 */
interface StatCardProps {
  label: string;
  value: number | string;
  icon: string;               // Bootstrap Icon class e.g. "bi-people-fill"
  color: string;              // Bootstrap color name e.g. "primary"
  /** Optional small descriptive line below the value */
  hint?: string;
  /** If true, value text is coloured with the card's accent color */
  accentValue?: boolean;
}

export default function StatCard({
  label,
  value,
  icon,
  color,
  hint,
  accentValue = false,
}: StatCardProps) {
  return (
    <div className="card border-0 shadow-sm h-100">
      <div className="card-body d-flex align-items-center gap-3 py-3">
        {/* Icon */}
        <div
          className={`d-flex align-items-center justify-content-center rounded-3 bg-${color} bg-opacity-10 flex-shrink-0`}
          style={{ width: 52, height: 52 }}
          aria-hidden="true"
        >
          <i className={`bi ${icon} fs-4 text-${color}`} />
        </div>

        {/* Text */}
        <div className="min-w-0">
          <div className="text-muted small fw-medium mb-1">{label}</div>
          <div
            className={`fw-bold lh-1 ${accentValue ? `text-${color}` : ''}`}
            style={{ fontSize: '1.6rem' }}
          >
            {value}
          </div>
          {hint && <div className="text-muted mt-1" style={{ fontSize: 11 }}>{hint}</div>}
        </div>
      </div>
    </div>
  );
}
