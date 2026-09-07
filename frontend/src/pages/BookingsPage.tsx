/**
 * BookingsPage — Phase 9.6
 *
 * Paginated booking list with status filter.
 * Admin: create bookings, cancel CONFIRMED bookings, view all.
 * Sales: create bookings (own leads), view own bookings, no cancel.
 *
 * Enrichment strategy:
 *   The backend only returns lead_id, unit_id, booked_by (numeric IDs).
 *   After loading a page of bookings, we resolve the unique IDs in one batch
 *   using the existing list APIs (leads, users).  Building/project context is
 *   resolved lazily in the detail view via the unit → building → project chain
 *   available from the properties API.
 *
 *   This gives us human-readable labels in the table without N+1 per-row calls.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import EmptyState from '../components/common/EmptyState';
import ToastContainer from '../components/common/ToastContainer';
import ConfirmModal from '../components/common/ConfirmModal';
import BookingFilters from '../components/bookings/BookingFilters';
import BookingTable, { type EnrichmentMaps } from '../components/bookings/BookingTable';
import BookingForm from '../components/bookings/BookingForm';
import BookingDetails from '../components/bookings/BookingDetails';
import {
  cancelBooking,
  listBookings,
  type Booking,
  type BookingStatus,
} from '../api/bookingsApi';
import { listLeads, listUsers } from '../api/leadsApi';
import apiClient from '../api/axios';
import { parseApiError } from '../hooks/useApiError';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/useToast';

const PAGE_SIZE = 10;

export default function BookingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const { toasts, toast, dismissToast } = useToast();

  // ── List state ─────────────────────────────────────────────────────────────
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [loading, setLoading]   = useState(true);
  const [listError, setListError] = useState('');

  const [statusFilter, setStatusFilter] = useState<BookingStatus | ''>('');

  // ── Enrichment maps ────────────────────────────────────────────────────────
  const [enrichment, setEnrichment] = useState<EnrichmentMaps>({
    leadNames: {}, unitLabels: {}, userNames: {},
  });

  // ── Unit label cache (unit_id → string) shared across pages ───────────────
  const unitLabelCache = useRef<Record<number, string>>({});

  // ── Modal state ────────────────────────────────────────────────────────────
  const [showForm, setShowForm]         = useState(false);
  const [detailBooking, setDetailBooking] = useState<Booking | undefined>();

  // ── Cancel state ───────────────────────────────────────────────────────────
  const [cancelTarget, setCancelTarget] = useState<Booking | null>(null);
  const [cancelling, setCancelling]     = useState(false);
  const [cancelError, setCancelError]   = useState('');

  // ── Enrichment builder ─────────────────────────────────────────────────────
  const buildEnrichment = useCallback(async (items: Booking[]) => {
    if (items.length === 0) return;

    const leadNames:  Record<number, string> = {};
    const userNames:  Record<number, string> = {};
    const unitLabels: Record<number, string> = { ...unitLabelCache.current };

    // Resolve lead names
    try {
      const res = await listLeads({ size: 100 });
      res.items.forEach((l) => { leadNames[l.id] = l.name; });
    } catch {/* fallback to IDs */}

    // Resolve user names (admin only — reuse listUsers)
    try {
      const users = await listUsers();
      users.forEach((u) => { userNames[u.id] = u.name; });
    } catch {/* fallback */}

    // Resolve unit labels: unit_number + building name + project name
    // Use the individual unit/building/project endpoints for each unknown unit.
    // Page size is 10, so this is at most 10 units × 3 requests = 30 calls max.
    const unknownUnitIds = items.map((bk) => bk.unit_id).filter((id) => !unitLabels[id]);
    const uniqueUnknown  = [...new Set(unknownUnitIds)];

    await Promise.allSettled(
      uniqueUnknown.map(async (unitId) => {
        try {
          const unitRes = await apiClient.get(`/units/${unitId}`);
          const u = unitRes.data;
          const bldgRes = await apiClient.get(`/buildings/${u.building_id}`);
          const bldg = bldgRes.data;
          const projRes = await apiClient.get(`/projects/${bldg.project_id}`);
          const proj = projRes.data;
          const label = `${u.unit_number} · ${bldg.name}, ${proj.name}`;
          unitLabels[unitId] = label;
          unitLabelCache.current[unitId] = label;
        } catch {
          unitLabels[unitId] = `Unit #${unitId}`;
        }
      })
    );

    setEnrichment({ leadNames, unitLabels, userNames });
  }, []);

  // ── Fetch bookings ─────────────────────────────────────────────────────────
  const fetchBookings = useCallback(async (pg: number, st: BookingStatus | '') => {
    setLoading(true);
    setListError('');
    try {
      const res = await listBookings({ page: pg, size: PAGE_SIZE, status: st || undefined });
      setBookings(res.items);
      setTotal(res.total);
      buildEnrichment(res.items);
    } catch (err) {
      setListError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [buildEnrichment]);

  useEffect(() => { fetchBookings(1, ''); }, [fetchBookings]);

  function handleStatusChange(v: BookingStatus | '') {
    setStatusFilter(v);
    setPage(1);
    fetchBookings(1, v);
  }

  function handlePageChange(next: number) {
    setPage(next);
    fetchBookings(next, statusFilter);
  }

  // ── Cancel ─────────────────────────────────────────────────────────────────
  async function confirmCancel() {
    if (!cancelTarget) return;
    setCancelling(true);
    setCancelError('');
    try {
      await cancelBooking(cancelTarget.id);
      toast('Booking cancelled successfully.');
      setCancelTarget(null);
      setDetailBooking(undefined);
      fetchBookings(page, statusFilter);
    } catch (err) {
      setCancelError(parseApiError(err));
    } finally {
      setCancelling(false);
    }
  }

  // ── Booking skeleton ───────────────────────────────────────────────────────
  const skeleton = (
    <div className="card border-0 shadow-sm">
      <div className="card-body p-0">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="d-flex align-items-center gap-3 px-3 py-3 border-bottom">
            <div className="skeleton rounded flex-grow-1" style={{ height: 14 }} />
            <div className="skeleton rounded" style={{ height: 14, width: 80 }} />
            <div className="skeleton rounded" style={{ height: 14, width: 60 }} />
          </div>
        ))}
      </div>
    </div>
  );

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Header */}
      <PageHeader title="Bookings" subtitle="Track and manage property bookings" icon="bi-calendar-check-fill">
        <button type="button" className="btn btn-primary btn-sm d-flex align-items-center gap-1"
          onClick={() => setShowForm(true)}>
          <i className="bi bi-calendar-plus-fill" aria-hidden="true" />New Booking
        </button>
      </PageHeader>

      {/* Filters */}
      <BookingFilters status={statusFilter} onStatusChange={handleStatusChange} />

      {/* Error */}
      {!loading && listError && (
        <div className="d-flex flex-column align-items-center py-5 text-center">
          <i className="bi bi-exclamation-triangle-fill fs-3 text-danger mb-2" aria-hidden="true" />
          <p className="fw-semibold mb-1">Unable to load bookings</p>
          <p className="text-muted small mb-3">{listError}</p>
          <button className="btn btn-sm btn-primary" onClick={() => fetchBookings(page, statusFilter)}>
            <i className="bi bi-arrow-clockwise me-1" aria-hidden="true" />Try again
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && skeleton}

      {/* Empty */}
      {!loading && !listError && bookings.length === 0 && (
        <EmptyState icon="bi-calendar-x"
          title="No bookings found"
          message={statusFilter
            ? 'Try changing your status filter.'
            : 'Bookings will appear here once a lead is successfully booked.'}>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>
            <i className="bi bi-calendar-plus-fill me-1" aria-hidden="true" />New Booking
          </button>
        </EmptyState>
      )}

      {/* Table */}
      {!loading && !listError && bookings.length > 0 && (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-0">
            <BookingTable
              bookings={bookings}
              enrichment={enrichment}
              isAdmin={isAdmin}
              onView={(b) => setDetailBooking(b)}
              onCancel={(b) => { setCancelTarget(b); setCancelError(''); }}
            />
          </div>

          {/* Pagination */}
          <div className="card-footer bg-transparent d-flex align-items-center justify-content-between flex-wrap gap-2 py-2">
            <span className="text-muted small">
              {total} booking{total !== 1 ? 's' : ''} · page {page} of {totalPages}
            </span>
            <div className="d-flex gap-1">
              <button type="button" className="btn btn-sm btn-outline-secondary"
                onClick={() => handlePageChange(page - 1)} disabled={page <= 1} aria-label="Previous page">
                <i className="bi bi-chevron-left" aria-hidden="true" />
              </button>
              <button type="button" className="btn btn-sm btn-outline-secondary"
                onClick={() => handlePageChange(page + 1)} disabled={page >= totalPages} aria-label="Next page">
                <i className="bi bi-chevron-right" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Booking form modal */}
      {showForm && (
        <BookingForm
          onSuccess={() => {
            setShowForm(false);
            toast('Booking created successfully.');
            fetchBookings(1, statusFilter);
            setPage(1);
          }}
          onCancel={() => setShowForm(false)} />
      )}

      {/* Cancel confirm */}
      {cancelTarget && (
        <ConfirmModal
          title="Cancel Booking?"
          message="Are you sure you want to cancel this booking?"
          subMessage="The unit will become available again. This action cannot be undone."
          confirmLabel="Cancel Booking"
          error={cancelError}
          busy={cancelling}
          onConfirm={confirmCancel}
          onCancel={() => setCancelTarget(null)} />
      )}

      {/* Booking detail drawer */}
      {detailBooking && (
        <BookingDetails
          booking={detailBooking}
          enrichment={enrichment}
          isAdmin={isAdmin}
          onClose={() => setDetailBooking(undefined)}
          onCancel={(b) => {
            setDetailBooking(undefined);
            setCancelTarget(b);
            setCancelError('');
          }} />
      )}
    </div>
  );
}
