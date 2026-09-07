/**
 * UsersPage — Phase 9.7
 *
 * Admin-only user management. Already protected by RoleProtectedRoute.
 *
 * Features:
 *   - Paginated user list with search + role + active-status filters (all backend-side)
 *   - Create user modal
 *   - Edit user modal
 *   - User detail offcanvas
 *   - Deactivate (PATCH /deactivate) with confirmation
 *   - Reactivate (PUT with is_active: true) inline
 *   - Last-admin protection: backend returns 400; shown as friendly message
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import EmptyState from '../components/common/EmptyState';
import ToastContainer from '../components/common/ToastContainer';
import ConfirmModal from '../components/common/ConfirmModal';
import UserFilters from '../components/users/UserFilters';
import UserTable from '../components/users/UserTable';
import UserForm from '../components/users/UserForm';
import UserDetails from '../components/users/UserDetails';
import {
  deactivateUser,
  listUsers,
  updateUser,
  type CrmUser,
} from '../api/usersApi';
import type { UserRole } from '../api/types';
import { parseApiError } from '../hooks/useApiError';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/useToast';

const PAGE_SIZE = 10;

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const currentUserId = currentUser?.id ?? 0;
  const { toasts, toast, dismissToast } = useToast();

  // ── List state ─────────────────────────────────────────────────────────────
  const [users, setUsers]     = useState<CrmUser[]>([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');

  // ── Filters ────────────────────────────────────────────────────────────────
  const [search, setSearch]         = useState('');
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('');
  const [activeFilter, setActiveFilter] = useState<boolean | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Modal state ────────────────────────────────────────────────────────────
  type ModalMode = 'none' | 'create' | 'edit';
  const [modalMode, setModalMode]   = useState<ModalMode>('none');
  const [editUser, setEditUser]     = useState<CrmUser | undefined>();
  const [detailUser, setDetailUser] = useState<CrmUser | undefined>();

  // ── Deactivate state ───────────────────────────────────────────────────────
  const [deactivateTarget, setDeactivateTarget] = useState<CrmUser | null>(null);
  const [deactivating, setDeactivating]         = useState(false);
  const [deactivateError, setDeactivateError]   = useState('');

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchUsers = useCallback(async (
    pg: number, q: string, role: UserRole | '', active: boolean | null
  ) => {
    setLoading(true);
    setListError('');
    try {
      const res = await listUsers({
        page:      pg,
        size:      PAGE_SIZE,
        search:    q || undefined,
        role:      role || undefined,
        is_active: active,
      });
      setUsers(res.items);
      setTotal(res.total);
    } catch (err) {
      setListError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(1, '', '', null); }, [fetchUsers]);

  // Search debounce
  function handleSearchChange(v: string) {
    setSearch(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { setPage(1); fetchUsers(1, v, roleFilter, activeFilter); }, 400);
  }

  function handleRoleChange(v: UserRole | '') {
    setRoleFilter(v); setPage(1); fetchUsers(1, search, v, activeFilter);
  }

  function handleActiveChange(v: boolean | null) {
    setActiveFilter(v); setPage(1); fetchUsers(1, search, roleFilter, v);
  }

  function handleClearFilters() {
    setSearch(''); setRoleFilter(''); setActiveFilter(null); setPage(1);
    fetchUsers(1, '', '', null);
  }

  function handlePageChange(next: number) { setPage(next); fetchUsers(next, search, roleFilter, activeFilter); }

  // ── Form success ───────────────────────────────────────────────────────────
  function handleFormSuccess(u: CrmUser) {
    setModalMode('none');
    toast(modalMode === 'create' ? `User "${u.name}" created.` : `User "${u.name}" updated.`);
    fetchUsers(page, search, roleFilter, activeFilter);
  }

  // ── Deactivate ─────────────────────────────────────────────────────────────
  async function confirmDeactivate() {
    if (!deactivateTarget) return;
    setDeactivating(true);
    setDeactivateError('');
    try {
      const updated = await deactivateUser(deactivateTarget.id);
      toast(`"${updated.name}" deactivated.`);
      setDeactivateTarget(null);
      setDetailUser(undefined);
      fetchUsers(page, search, roleFilter, activeFilter);
    } catch (err) {
      setDeactivateError(parseApiError(err));
    } finally {
      setDeactivating(false);
    }
  }

  // ── Reactivate (PUT with is_active: true) ──────────────────────────────────
  async function handleReactivate(u: CrmUser) {
    try {
      const updated = await updateUser(u.id, { is_active: true });
      toast(`"${updated.name}" reactivated.`);
      setDetailUser(undefined);
      fetchUsers(page, search, roleFilter, activeFilter);
    } catch (err) {
      toast(parseApiError(err), 'danger');
    }
  }

  // ── Computed ───────────────────────────────────────────────────────────────
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const hasFilters = !!search || !!roleFilter || activeFilter !== null;

  // ── Skeleton ───────────────────────────────────────────────────────────────
  const skeleton = (
    <div className="card border-0 shadow-sm">
      <div className="card-body p-0">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="d-flex align-items-center gap-3 px-3 py-3 border-bottom">
            <div className="skeleton rounded-circle flex-shrink-0" style={{ width: 36, height: 36 }} />
            <div className="flex-grow-1">
              <div className="skeleton rounded mb-1" style={{ height: 13, width: '40%' }} />
              <div className="skeleton rounded" style={{ height: 11, width: '60%' }} />
            </div>
            <div className="skeleton rounded" style={{ height: 22, width: 50 }} />
            <div className="skeleton rounded" style={{ height: 22, width: 60 }} />
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Header */}
      <PageHeader title="Users" subtitle="Manage CRM users and roles" icon="bi-person-lines-fill">
        <button type="button" className="btn btn-primary btn-sm d-flex align-items-center gap-1"
          onClick={() => { setEditUser(undefined); setModalMode('create'); }}>
          <i className="bi bi-person-plus-fill" aria-hidden="true" />Create User
        </button>
      </PageHeader>

      {/* Filters */}
      <UserFilters
        search={search} onSearchChange={handleSearchChange}
        role={roleFilter} onRoleChange={handleRoleChange}
        isActive={activeFilter} onActiveChange={handleActiveChange}
        onClear={handleClearFilters}
        hasActiveFilters={hasFilters}
      />

      {/* Error */}
      {!loading && listError && (
        <div className="d-flex flex-column align-items-center py-5 text-center">
          <i className="bi bi-exclamation-triangle-fill fs-3 text-danger mb-2" aria-hidden="true" />
          <p className="fw-semibold mb-1">Unable to load users</p>
          <p className="text-muted small mb-3">{listError}</p>
          <button className="btn btn-sm btn-primary"
            onClick={() => fetchUsers(page, search, roleFilter, activeFilter)}>
            <i className="bi bi-arrow-clockwise me-1" aria-hidden="true" />Try again
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && skeleton}

      {/* Empty */}
      {!loading && !listError && users.length === 0 && (
        <EmptyState icon="bi-people" title="No users found"
          message={hasFilters
            ? 'Try changing your search or filters.'
            : 'Create a user to give them access to the CRM.'}>
          {!hasFilters && (
            <button type="button" className="btn btn-primary btn-sm"
              onClick={() => { setEditUser(undefined); setModalMode('create'); }}>
              <i className="bi bi-person-plus-fill me-1" aria-hidden="true" />Create User
            </button>
          )}
        </EmptyState>
      )}

      {/* Table */}
      {!loading && !listError && users.length > 0 && (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-0">
            <UserTable
              users={users}
              currentUserId={currentUserId}
              onView={(u) => setDetailUser(u)}
              onEdit={(u) => { setEditUser(u); setModalMode('edit'); setDetailUser(undefined); }}
              onDeactivate={(u) => { setDeactivateTarget(u); setDeactivateError(''); }}
              onReactivate={handleReactivate}
            />
          </div>

          {/* Pagination */}
          <div className="card-footer bg-transparent d-flex align-items-center justify-content-between flex-wrap gap-2 py-2">
            <span className="text-muted small">
              {total} user{total !== 1 ? 's' : ''} · page {page} of {totalPages || 1}
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

      {/* Create / Edit modal */}
      {modalMode !== 'none' && (
        <UserForm mode={modalMode} user={editUser}
          onSuccess={handleFormSuccess}
          onCancel={() => setModalMode('none')} />
      )}

      {/* Deactivate confirmation */}
      {deactivateTarget && (
        <ConfirmModal
          title="Deactivate User?"
          message={`Are you sure you want to deactivate "${deactivateTarget.name}"?`}
          subMessage="They will no longer be able to access the CRM. You can reactivate them later."
          confirmLabel="Deactivate"
          error={deactivateError}
          busy={deactivating}
          onConfirm={confirmDeactivate}
          onCancel={() => setDeactivateTarget(null)} />
      )}

      {/* User detail drawer */}
      {detailUser && (
        <UserDetails
          user={detailUser}
          currentUserId={currentUserId}
          onClose={() => setDetailUser(undefined)}
          onEdit={(u) => { setDetailUser(undefined); setEditUser(u); setModalMode('edit'); }}
          onDeactivate={(u) => { setDetailUser(undefined); setDeactivateTarget(u); setDeactivateError(''); }}
          onReactivate={(u) => { setDetailUser(undefined); handleReactivate(u); }}
        />
      )}
    </div>
  );
}
