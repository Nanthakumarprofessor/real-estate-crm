/**
 * LeadsPage — Phase 9.4
 *
 * Full lead management with:
 *   - Paginated list from GET /api/leads
 *   - Search + stage filter (backend-side)
 *   - Create / edit via modal form
 *   - Soft-delete (Admin only) with confirmation
 *   - Lead details offcanvas (notes + follow-ups)
 *   - Role-aware UI (Admin vs Sales)
 *   - Loading skeleton, error, empty states
 *   - Toast-style success feedback
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import EmptyState from '../components/common/EmptyState';
import ToastContainer from '../components/common/ToastContainer';
import LeadFilters from '../components/leads/LeadFilters';
import LeadTable from '../components/leads/LeadTable';
import LeadForm from '../components/leads/LeadForm';
import LeadDetails from '../components/leads/LeadDetails';
import {
  deleteLead,
  listLeads,
  listUsers,
  type Lead,
  type UserOption,
} from '../api/leadsApi';
import type { LeadStage } from '../api/types';
import { parseApiError } from '../hooks/useApiError';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/useToast';

const PAGE_SIZE = 10;

export default function LeadsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const currentUserId = user?.id ?? 0;
  const { toasts, toast, dismissToast } = useToast();

  // ── List state ─────────────────────────────────────────────────────────────
  const [leads, setLeads]     = useState<Lead[]>([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');

  // ── Filters ────────────────────────────────────────────────────────────────
  const [search, setSearch]     = useState('');
  const [stage, setStage]       = useState<LeadStage | ''>('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Users (for assignee dropdown — admin only) ─────────────────────────────
  const [users, setUsers] = useState<UserOption[]>([]);

  // ── Modal state ────────────────────────────────────────────────────────────
  type ModalMode = 'none' | 'create' | 'edit';
  const [modalMode, setModalMode]   = useState<ModalMode>('none');
  const [editLead, setEditLead]     = useState<Lead | undefined>();
  const [detailLead, setDetailLead] = useState<Lead | undefined>();

  // ── Delete confirmation ────────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<Lead | null>(null);
  const [deleting, setDeleting]         = useState(false);
  const [deleteError, setDeleteError]   = useState('');

  // ── Fetch helpers ──────────────────────────────────────────────────────────
  const fetchLeads = useCallback(async (pg: number, q: string, st: LeadStage | '') => {
    setLoading(true);
    setListError('');
    try {
      const res = await listLeads({
        page: pg,
        size: PAGE_SIZE,
        search: q || undefined,
        stage: st || undefined,
      });
      setLeads(res.items);
      setTotal(res.total);
    } catch (err) {
      setListError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    fetchLeads(page, search, stage);
    // Load users for admin assignee dropdown
    if (isAdmin) {
      listUsers().then(setUsers).catch(() => {/* non-critical */});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Search debounce
  function handleSearchChange(v: string) {
    setSearch(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetchLeads(1, v, stage);
    }, 400);
  }

  // Stage filter (immediate)
  function handleStageChange(v: LeadStage | '') {
    setStage(v);
    setPage(1);
    fetchLeads(1, search, v);
  }

  function handleClearFilters() {
    setSearch('');
    setStage('');
    setPage(1);
    fetchLeads(1, '', '');
  }

  function handlePageChange(next: number) {
    setPage(next);
    fetchLeads(next, search, stage);
  }

  // ── Create / edit handlers ─────────────────────────────────────────────────
  function openCreate() {
    setEditLead(undefined);
    setModalMode('create');
  }

  function openEdit(lead: Lead) {
    setEditLead(lead);
    setDetailLead(undefined); // close details if open
    setModalMode('edit');
  }

  function handleFormSuccess(lead: Lead) {
    setModalMode('none');
    toast(modalMode === 'create' ? `Lead "${lead.name}" created.` : `Lead "${lead.name}" updated.`);
    fetchLeads(page, search, stage);
  }

  // ── Delete handlers ────────────────────────────────────────────────────────
  function handleDeleteRequest(lead: Lead) {
    setDeleteTarget(lead);
    setDeleteError('');
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteLead(deleteTarget.id);
      toast(`Lead "${deleteTarget.name}" removed.`);
      setDeleteTarget(null);
      fetchLeads(page, search, stage);
    } catch (err) {
      setDeleteError(parseApiError(err));
    } finally {
      setDeleting(false);
    }
  }

  // ── Detail handlers ────────────────────────────────────────────────────────
  function openDetail(lead: Lead) {
    setDetailLead(lead);
  }

  // ── Computed ───────────────────────────────────────────────────────────────
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const hasFilters = !!search || !!stage;

  // ── Skeleton ───────────────────────────────────────────────────────────────
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

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* ── Page header ────────────────────────────────────────────────────── */}
      <PageHeader
        title="Leads"
        subtitle="Manage your sales pipeline"
        icon="bi-people-fill"
      >
        <button
          type="button"
          className="btn btn-primary btn-sm d-flex align-items-center gap-1"
          onClick={openCreate}
        >
          <i className="bi bi-person-plus-fill" aria-hidden="true" />
          Add Lead
        </button>
      </PageHeader>

      {/* ── Filters ────────────────────────────────────────────────────────── */}
      <LeadFilters
        search={search}
        onSearchChange={handleSearchChange}
        stage={stage}
        onStageChange={handleStageChange}
        onClear={handleClearFilters}
        hasActiveFilters={hasFilters}
      />

      {/* ── Error state ────────────────────────────────────────────────────── */}
      {!loading && listError && (
        <div className="d-flex flex-column align-items-center py-5 text-center">
          <i className="bi bi-exclamation-triangle-fill fs-3 text-danger mb-2" aria-hidden="true" />
          <p className="fw-semibold mb-1">Unable to load leads</p>
          <p className="text-muted small mb-3">{listError}</p>
          <button className="btn btn-sm btn-primary" onClick={() => fetchLeads(page, search, stage)}>
            <i className="bi bi-arrow-clockwise me-1" aria-hidden="true" />
            Try again
          </button>
        </div>
      )}

      {/* ── Loading ────────────────────────────────────────────────────────── */}
      {loading && skeleton}

      {/* ── Empty state ────────────────────────────────────────────────────── */}
      {!loading && !listError && leads.length === 0 && (
        <div className="card border-0 shadow-sm">
          <div className="card-body">
            <EmptyState
              icon="bi-people"
              title="No leads found"
              message={hasFilters
                ? 'Try changing your search or filters.'
                : 'Create your first lead to start managing your sales pipeline.'}
            >
              {!hasFilters && (
                <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
                  <i className="bi bi-person-plus-fill me-1" aria-hidden="true" />
                  Add Lead
                </button>
              )}
            </EmptyState>
          </div>
        </div>
      )}

      {/* ── Table ──────────────────────────────────────────────────────────── */}
      {!loading && !listError && leads.length > 0 && (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-0">
            <LeadTable
              leads={leads}
              isAdmin={isAdmin}
              currentUserId={currentUserId}
              users={users}
              onView={openDetail}
              onEdit={openEdit}
              onDelete={handleDeleteRequest}
            />
          </div>

          {/* ── Pagination ────────────────────────────────────────────────── */}
          <div className="card-footer bg-transparent d-flex align-items-center justify-content-between flex-wrap gap-2 py-2">
            <span className="text-muted small">
              {total} lead{total !== 1 ? 's' : ''} · page {page} of {totalPages}
            </span>
            <div className="d-flex gap-1">
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                aria-label="Previous page"
              >
                <i className="bi bi-chevron-left" aria-hidden="true" />
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages}
                aria-label="Next page"
              >
                <i className="bi bi-chevron-right" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Create / Edit modal ─────────────────────────────────────────────── */}
      {modalMode !== 'none' && (
        <LeadForm
          mode={modalMode}
          lead={editLead}
          isAdmin={isAdmin}
          users={users}
          onSuccess={handleFormSuccess}
          onCancel={() => setModalMode('none')}
        />
      )}

      {/* ── Delete confirmation modal ──────────────────────────────────────── */}
      {deleteTarget && (
        <div
          className="modal d-block"
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="Confirm delete"
          style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        >
          <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable" style={{ maxWidth: 400 }}>
            <div className="modal-content border-0 shadow">
              <div className="modal-header border-0 pb-0">
                <div className="d-flex align-items-center gap-2">
                  <div className="rounded-circle bg-danger bg-opacity-10 d-flex align-items-center justify-content-center" style={{ width: 36, height: 36 }}>
                    <i className="bi bi-trash3-fill text-danger" aria-hidden="true" />
                  </div>
                  <h5 className="modal-title">Remove Lead?</h5>
                </div>
              </div>
              <div className="modal-body pt-2">
                {deleteError && (
                  <div className="alert alert-danger small py-2 mb-2">{deleteError}</div>
                )}
                <p className="mb-1">
                  Are you sure you want to remove <strong>{deleteTarget.name}</strong>?
                </p>
                <p className="text-muted small mb-0">
                  This is a soft delete — the lead will be deactivated and removed from active lists,
                  but historical notes and follow-ups will be preserved.
                </p>
              </div>
              <div className="modal-footer border-0 pt-0">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => setDeleteTarget(null)}
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={confirmDelete}
                  disabled={deleting}
                >
                  {deleting
                    ? <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />Removing…</>
                    : 'Remove Lead'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Lead detail drawer ─────────────────────────────────────────────── */}
      {detailLead && (
        <LeadDetails
          lead={detailLead}
          currentUserId={currentUserId}
          isAdmin={isAdmin}
          users={users}
          onClose={() => setDetailLead(undefined)}
          onEdit={(lead) => {
            setDetailLead(undefined);
            openEdit(lead);
          }}
        />
      )}
    </div>
  );
}
