/**
 * PropertiesPage — Phase 9.5
 *
 * Shows a paginated, searchable project list.
 * Admin: full CRUD on projects, buildings, units.
 * Sales: read-only.
 *
 * Lazy-loading hierarchy:
 *   Load projects on mount
 *   → open project → load its buildings
 *   → expand building → load its units
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import EmptyState from '../components/common/EmptyState';
import ToastContainer from '../components/common/ToastContainer';
import ConfirmModal from '../components/common/ConfirmModal';
import ProjectForm from '../components/properties/ProjectForm';
import ProjectDetails from '../components/properties/ProjectDetails';
import { deleteProject, listProjects, type Project } from '../api/propertiesApi';
import { parseApiError } from '../hooks/useApiError';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/useToast';

const PAGE_SIZE = 10;

export default function PropertiesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const { toasts, toast, dismissToast } = useToast();

  // ── List state ─────────────────────────────────────────────────────────────
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [loading, setLoading]   = useState(true);
  const [listError, setListError] = useState('');

  const [search, setSearch]     = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Modal state ────────────────────────────────────────────────────────────
  type ModalMode = 'none' | 'create' | 'edit';
  const [modalMode, setModalMode]     = useState<ModalMode>('none');
  const [editProject, setEditProject] = useState<Project | undefined>();
  const [detailProject, setDetailProject] = useState<Project | undefined>();

  // ── Delete state ───────────────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleting, setDeleting]         = useState(false);
  const [deleteError, setDeleteError]   = useState('');

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchProjects = useCallback(async (pg: number, q: string) => {
    setLoading(true);
    setListError('');
    try {
      const res = await listProjects(pg, PAGE_SIZE, q || undefined);
      setProjects(res.items);
      setTotal(res.total);
    } catch (err) {
      setListError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(1, ''); }, [fetchProjects]);

  function handleSearchChange(v: string) {
    setSearch(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { setPage(1); fetchProjects(1, v); }, 400);
  }

  function handlePageChange(next: number) { setPage(next); fetchProjects(next, search); }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteProject(deleteTarget.id);
      toast(`Project "${deleteTarget.name}" deleted.`);
      setDeleteTarget(null);
      // If deleted the last item on the current page, step back one page
      const newTotal = total - 1;
      const newTotalPages = Math.ceil(newTotal / PAGE_SIZE) || 1;
      const nextPage = Math.min(page, newTotalPages);
      setPage(nextPage);
      fetchProjects(nextPage, search);
    } catch (err) {
      setDeleteError(parseApiError(err));
    } finally {
      setDeleting(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ── Skeleton ───────────────────────────────────────────────────────────────
  const skeleton = (
    <div className="row g-3">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="col-12 col-md-6 col-xl-4">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-body">
              <div className="skeleton rounded mb-2" style={{ height: 18, width: '60%' }} />
              <div className="skeleton rounded mb-2" style={{ height: 12, width: '40%' }} />
              <div className="skeleton rounded" style={{ height: 12, width: '80%' }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Header */}
      <PageHeader title="Properties" subtitle="Manage projects, buildings and units" icon="bi-buildings-fill">
        {isAdmin && (
          <button type="button" className="btn btn-primary btn-sm d-flex align-items-center gap-1"
            onClick={() => { setEditProject(undefined); setModalMode('create'); }}>
            <i className="bi bi-building-add" aria-hidden="true" />Add Project
          </button>
        )}
      </PageHeader>

      {/* Search */}
      <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
        <div className="input-group input-group-sm" style={{ maxWidth: 280 }}>
          <span className="input-group-text border-end-0 bg-white">
            <i className="bi bi-search text-muted" aria-hidden="true" />
          </span>
          <input type="search" className="form-control border-start-0"
            placeholder="Search by name or location…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            aria-label="Search projects" />
        </div>
        {search && (
          <button type="button" className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
            onClick={() => { setSearch(''); setPage(1); fetchProjects(1, ''); }}>
            <i className="bi bi-x" aria-hidden="true" />Clear
          </button>
        )}
      </div>

      {/* Error */}
      {!loading && listError && (
        <div className="d-flex flex-column align-items-center py-5 text-center">
          <i className="bi bi-exclamation-triangle-fill fs-3 text-danger mb-2" aria-hidden="true" />
          <p className="fw-semibold mb-1">Unable to load properties</p>
          <p className="text-muted small mb-3">{listError}</p>
          <button className="btn btn-sm btn-primary" onClick={() => fetchProjects(page, search)}>
            <i className="bi bi-arrow-clockwise me-1" aria-hidden="true" />Try again
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && skeleton}

      {/* Empty */}
      {!loading && !listError && projects.length === 0 && (
        <EmptyState icon="bi-buildings" title="No projects found"
          message={search
            ? 'Try changing your search.'
            : isAdmin
              ? 'Create your first project to start managing properties.'
              : 'No properties are available yet.'}>
          {isAdmin && !search && (
            <button type="button" className="btn btn-primary btn-sm"
              onClick={() => { setEditProject(undefined); setModalMode('create'); }}>
              <i className="bi bi-building-add me-1" aria-hidden="true" />Add Project
            </button>
          )}
        </EmptyState>
      )}

      {/* Project cards grid */}
      {!loading && !listError && projects.length > 0 && (
        <>
          <div className="row g-3 mb-3">
            {projects.map((p) => (
              <div key={p.id} className="col-12 col-md-6 col-xl-4">
                <div className="card border-0 shadow-sm h-100 crm-project-card"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setDetailProject(p)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setDetailProject(p)}
                  aria-label={`View project ${p.name}`}>
                  <div className="card-body">
                    <div className="d-flex align-items-start justify-content-between gap-2">
                      <div className="flex-grow-1 min-w-0">
                        <h6 className="fw-semibold mb-1 text-truncate">{p.name}</h6>
                        {p.location && (
                          <div className="text-muted small mb-1">
                            <i className="bi bi-geo-alt me-1" aria-hidden="true" />{p.location}
                          </div>
                        )}
                        {p.description && (
                          <p className="text-muted small mb-0 crm-line-clamp-2">{p.description}</p>
                        )}
                      </div>
                      {/* Admin actions — stop click from bubbling to card */}
                      {isAdmin && (
                        <div className="d-flex flex-column gap-1 flex-shrink-0"
                          onClick={(e) => e.stopPropagation()} role="presentation">
                          <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2"
                            onClick={() => { setEditProject(p); setModalMode('edit'); }} aria-label={`Edit ${p.name}`}>
                            <i className="bi bi-pencil" aria-hidden="true" />
                          </button>
                          <button type="button" className="btn btn-sm btn-outline-danger py-0 px-2"
                            onClick={() => { setDeleteTarget(p); setDeleteError(''); }} aria-label={`Delete ${p.name}`}>
                            <i className="bi bi-trash3" aria-hidden="true" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="card-footer bg-transparent border-top-0 pt-0 pb-2 px-3">
                    <span className="text-muted" style={{ fontSize: 11 }}>
                      <i className="bi bi-calendar me-1" aria-hidden="true" />
                      {new Date(p.created_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="d-flex align-items-center justify-content-between flex-wrap gap-2">
            <span className="text-muted small">{total} project{total !== 1 ? 's' : ''} · page {page} of {totalPages}</span>
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
        </>
      )}

      {/* Project form modal */}
      {modalMode !== 'none' && (
        <ProjectForm
          mode={modalMode}
          project={editProject}
          onSuccess={(p) => {
            setModalMode('none');
            toast(modalMode === 'create' ? `Project "${p.name}" created.` : `Project "${p.name}" updated.`);
            fetchProjects(page, search);
          }}
          onCancel={() => setModalMode('none')} />
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <ConfirmModal
          title="Delete Project?"
          message={`Are you sure you want to delete "${deleteTarget.name}"?`}
          subMessage="This cannot be done if the project contains buildings."
          confirmLabel="Delete Project"
          error={deleteError}
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)} />
      )}

      {/* Project details offcanvas */}
      {detailProject && (
        <ProjectDetails
          project={detailProject}
          isAdmin={isAdmin}
          onClose={() => setDetailProject(undefined)}
          onEdit={(p) => { setDetailProject(undefined); setEditProject(p); setModalMode('edit'); }}
          onToast={toast} />
      )}
    </div>
  );
}
