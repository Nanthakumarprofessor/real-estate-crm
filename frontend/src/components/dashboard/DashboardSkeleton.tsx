/**
 * DashboardSkeleton — lightweight shimmer placeholder shown while data loads.
 *
 * Matches the real dashboard layout so there's no jarring layout shift.
 * Pure CSS — no extra library.
 */
export default function DashboardSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading dashboard…">
      {/* KPI cards */}
      <div className="row g-3 mb-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="col-sm-6 col-xl-3">
            <div className="card border-0 shadow-sm">
              <div className="card-body d-flex align-items-center gap-3 py-3">
                <div className="skeleton rounded-3 flex-shrink-0" style={{ width: 52, height: 52 }} />
                <div className="flex-grow-1">
                  <div className="skeleton rounded mb-2" style={{ height: 12, width: '60%' }} />
                  <div className="skeleton rounded" style={{ height: 28, width: '40%' }} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Analytics row */}
      <div className="row g-3">
        <div className="col-12 col-lg-7">
          <div className="card border-0 shadow-sm" style={{ minHeight: 260 }}>
            <div className="card-body">
              <div className="skeleton rounded mb-3" style={{ height: 16, width: '35%' }} />
              {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                <div key={i} className="d-flex align-items-center gap-2 mb-2">
                  <div className="skeleton rounded" style={{ width: 82, height: 10 }} />
                  <div className="skeleton rounded-pill flex-grow-1" style={{ height: 10 }} />
                  <div className="skeleton rounded" style={{ width: 20, height: 10 }} />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-5">
          <div className="row g-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="col-12">
                <div className="card border-0 shadow-sm" style={{ minHeight: 100 }}>
                  <div className="card-body">
                    <div className="skeleton rounded mb-2" style={{ height: 14, width: '40%' }} />
                    <div className="skeleton rounded" style={{ height: 40 }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
