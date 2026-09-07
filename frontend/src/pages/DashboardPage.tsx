/**
 * DashboardPage — Phase 9.3
 *
 * Fetches GET /api/dashboard/summary and renders:
 *   - 4 KPI stat cards
 *   - Lead pipeline (by_stage horizontal bars)
 *   - Property inventory summary
 *   - Booking summary
 *   - Follow-up summary
 *
 * States:
 *   loading  → skeleton cards (no misleading zeros)
 *   error    → error alert + Retry button
 *   success  → full dashboard
 *
 * The backend scopes data for Admin vs Sales automatically.
 * This component simply renders whatever the API returns.
 */
import { useCallback, useEffect, useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import DashboardSkeleton from '../components/dashboard/DashboardSkeleton';
import StatCard from '../components/dashboard/StatCard';
import LeadPipeline from '../components/dashboard/LeadPipeline';
import PropertySummary from '../components/dashboard/PropertySummary';
import BookingSummary from '../components/dashboard/BookingSummary';
import FollowUpSummary from '../components/dashboard/FollowUpSummary';
import { getDashboardSummary, type DashboardSummary } from '../api/dashboardApi';
import { parseApiError } from '../hooks/useApiError';
import { useAuth } from '../context/AuthContext';

export default function DashboardPage() {
  const { user } = useAuth();

  const [data, setData]       = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(''); // always clear before every attempt

    try {
      const summary = await getDashboardSummary();
      setData(summary);
      setError('');
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── Refresh handler ────────────────────────────────────────────────────────
  function handleRefresh() {
    fetchData(true);
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={`Welcome back, ${user?.name ?? ''}. Here's your CRM overview.`}
        icon="bi-grid-1x2-fill"
      >
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
          onClick={handleRefresh}
          disabled={loading || refreshing}
          aria-label="Refresh dashboard"
        >
          <i
            className={`bi bi-arrow-clockwise ${refreshing ? 'crm-spin' : ''}`}
            aria-hidden="true"
          />
          <span className="d-none d-sm-inline">Refresh</span>
        </button>
      </PageHeader>

      {/* ── Loading skeleton ─────────────────────────────────────────────── */}
      {loading && <DashboardSkeleton />}

      {/* ── Error state ──────────────────────────────────────────────────── */}
      {!loading && error && (
        <div className="d-flex flex-column align-items-center justify-content-center py-5 text-center">
          <div
            className="d-inline-flex align-items-center justify-content-center rounded-circle bg-danger bg-opacity-10 mb-3"
            style={{ width: 64, height: 64 }}
          >
            <i className="bi bi-exclamation-triangle-fill fs-3 text-danger" aria-hidden="true" />
          </div>
          <h2 className="h5 fw-semibold mb-1">Unable to load dashboard</h2>
          <p className="text-muted small mb-3">{error}</p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => fetchData()}
          >
            <i className="bi bi-arrow-clockwise me-1" aria-hidden="true" />
            Try again
          </button>
        </div>
      )}

      {/* ── Dashboard content ────────────────────────────────────────────── */}
      {!loading && !error && data && (
        <>
          {/* KPI cards */}
          <div className="row g-3 mb-4">
            <div className="col-sm-6 col-xl-3">
              <StatCard
                label="Active Leads"
                value={data.leads.total}
                icon="bi-people-fill"
                color="primary"
                hint="All pipeline stages"
              />
            </div>
            <div className="col-sm-6 col-xl-3">
              <StatCard
                label="Upcoming Follow-ups"
                value={data.follow_ups.upcoming}
                icon="bi-calendar-event-fill"
                color="info"
                hint={
                  data.follow_ups.overdue > 0
                    ? `${data.follow_ups.overdue} overdue`
                    : 'None overdue'
                }
                accentValue={false}
              />
            </div>
            <div className="col-sm-6 col-xl-3">
              <StatCard
                label="Available Units"
                value={data.properties.available_units}
                icon="bi-buildings-fill"
                color="success"
                hint={`of ${data.properties.total_units} total`}
              />
            </div>
            <div className="col-sm-6 col-xl-3">
              <StatCard
                label="Confirmed Bookings"
                value={data.bookings.confirmed}
                icon="bi-calendar-check-fill"
                color="warning"
                hint={
                  data.bookings.cancelled > 0
                    ? `${data.bookings.cancelled} cancelled`
                    : undefined
                }
              />
            </div>
          </div>

          {/* Analytics row */}
          <div className="row g-3">
            {/* Lead pipeline — wider */}
            <div className="col-12 col-lg-7">
              <LeadPipeline data={data.leads} />
            </div>

            {/* Right column — stacked cards */}
            <div className="col-12 col-lg-5">
              <div className="row g-3">
                <div className="col-12">
                  <PropertySummary data={data.properties} />
                </div>
                <div className="col-12 col-sm-6 col-lg-12">
                  <BookingSummary data={data.bookings} />
                </div>
                <div className="col-12 col-sm-6 col-lg-12">
                  <FollowUpSummary data={data.follow_ups} />
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
