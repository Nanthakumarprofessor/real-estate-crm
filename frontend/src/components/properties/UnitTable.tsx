/**
 * UnitTable — paginated unit list for a building.
 *
 * Includes inline status/type filters and pagination.
 * Calls the backend directly (no client-side filtering).
 */
import { useCallback, useEffect, useState } from 'react';
import type { Unit, UnitStatus, UnitType } from '../../api/propertiesApi';
import { deleteUnit, listUnits } from '../../api/propertiesApi';
import { UNIT_STATUS_BADGE, UNIT_STATUS_LABEL, UNIT_TYPE_LABEL, UNIT_TYPE_OPTIONS } from './propertyConstants';
import UnitForm from './UnitForm';
import ConfirmModal from '../common/ConfirmModal';
import EmptyState from '../common/EmptyState';
import { parseApiError } from '../../hooks/useApiError';

const PAGE_SIZE = 10;

interface UnitTableProps {
  buildingId: number;
  isAdmin: boolean;
  onToast: (msg: string, type?: 'success' | 'danger') => void;
}

export default function UnitTable({ buildingId, isAdmin, onToast }: UnitTableProps) {
  const [units, setUnits]     = useState<Unit[]>([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const [statusFilter, setStatusFilter] = useState<UnitStatus | ''>('');
  const [typeFilter, setTypeFilter]     = useState<UnitType | ''>('');

  type ModalMode = 'none' | 'create' | 'edit';
  const [modalMode, setModalMode] = useState<ModalMode>('none');
  const [editUnit, setEditUnit]   = useState<Unit | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<Unit | null>(null);
  const [deleting, setDeleting]         = useState(false);
  const [deleteError, setDeleteError]   = useState('');

  const fetchUnits = useCallback(async (pg: number, st: UnitStatus | '', ty: UnitType | '') => {
    setLoading(true);
    setError('');
    try {
      const res = await listUnits(buildingId, { page: pg, size: PAGE_SIZE, status: st || undefined, type: ty || undefined });
      setUnits(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [buildingId]);

  useEffect(() => { fetchUnits(1, '', ''); }, [fetchUnits]);

  function applyStatus(v: UnitStatus | '') { setStatusFilter(v); setPage(1); fetchUnits(1, v, typeFilter); }
  function applyType(v: UnitType | '')     { setTypeFilter(v);   setPage(1); fetchUnits(1, statusFilter, v); }
  function clearFilters()                   { setStatusFilter(''); setTypeFilter(''); setPage(1); fetchUnits(1, '', ''); }
  function changePage(p: number)            { setPage(p); fetchUnits(p, statusFilter, typeFilter); }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteUnit(deleteTarget.id);
      onToast(`Unit "${deleteTarget.unit_number}" deleted.`);
      setDeleteTarget(null);
      fetchUnits(page, statusFilter, typeFilter);
    } catch (err) {
      setDeleteError(parseApiError(err));
    } finally {
      setDeleting(false);
    }
  }

  function formatPrice(p: number | null): string {
    if (p == null) return '—';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(p);
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const hasFilters = !!statusFilter || !!typeFilter;

  return (
    <div>
      {/* Filters */}
      <div className="d-flex flex-wrap gap-2 mb-3 align-items-center">
        <select className="form-select form-select-sm" style={{ maxWidth: 140 }} value={statusFilter}
          onChange={(e) => applyStatus(e.target.value as UnitStatus | '')} aria-label="Filter by status">
          <option value="">All Status</option>
          <option value="AVAILABLE">Available</option>
          <option value="BOOKED">Booked</option>
        </select>
        <select className="form-select form-select-sm" style={{ maxWidth: 140 }} value={typeFilter}
          onChange={(e) => applyType(e.target.value as UnitType | '')} aria-label="Filter by type">
          <option value="">All Types</option>
          {UNIT_TYPE_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        {hasFilters && (
          <button type="button" className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1" onClick={clearFilters}>
            <i className="bi bi-x" aria-hidden="true" />Clear
          </button>
        )}
        {isAdmin && (
          <button type="button" className="btn btn-sm btn-success ms-auto d-flex align-items-center gap-1"
            onClick={() => { setEditUnit(undefined); setModalMode('create'); }}>
            <i className="bi bi-plus-circle" aria-hidden="true" />Add Unit
          </button>
        )}
      </div>

      {/* Error */}
      {!loading && error && (
        <div className="text-center py-4">
          <p className="text-danger small mb-2">{error}</p>
          <button className="btn btn-sm btn-outline-primary" onClick={() => fetchUnits(page, statusFilter, typeFilter)}>Retry</button>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="d-flex gap-3 py-2 border-bottom">
              <div className="skeleton rounded flex-grow-1" style={{ height: 14 }} />
              <div className="skeleton rounded" style={{ width: 60, height: 14 }} />
              <div className="skeleton rounded" style={{ width: 80, height: 14 }} />
            </div>
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && units.length === 0 && (
        <EmptyState icon="bi-door-closed" title="No units found"
          message={hasFilters ? 'Try changing your filters.' : 'Add the first unit to this building.'} />
      )}

      {/* Desktop table */}
      {!loading && !error && units.length > 0 && (
        <>
          <div className="d-none d-md-block table-responsive">
            <table className="table table-hover align-middle mb-0 small">
              <thead className="table-light">
                <tr>
                  <th>Unit</th><th>Type</th><th>Floor</th><th>Price</th><th>Status</th>
                  {isAdmin && <th style={{ width: 80 }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {units.map((u) => (
                  <tr key={u.id}>
                    <td className="fw-medium">{u.unit_number}</td>
                    <td>{UNIT_TYPE_LABEL[u.type]}</td>
                    <td>{u.floor ?? '—'}</td>
                    <td>{formatPrice(u.price)}</td>
                    <td><span className={`badge ${UNIT_STATUS_BADGE[u.status]}`} style={{ fontSize: 11 }}>{UNIT_STATUS_LABEL[u.status]}</span></td>
                    {isAdmin && (
                      <td>
                        <div className="d-flex gap-1">
                          <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2"
                            onClick={() => { setEditUnit(u); setModalMode('edit'); }} aria-label={`Edit unit ${u.unit_number}`}>
                            <i className="bi bi-pencil" aria-hidden="true" />
                          </button>
                          <button type="button" className="btn btn-sm btn-outline-danger py-0 px-2"
                            onClick={() => { setDeleteTarget(u); setDeleteError(''); }} aria-label={`Delete unit ${u.unit_number}`}>
                            <i className="bi bi-trash3" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="d-md-none d-flex flex-column gap-2">
            {units.map((u) => (
              <div key={u.id} className="card border-0 shadow-sm">
                <div className="card-body py-3">
                  <div className="d-flex justify-content-between align-items-start mb-1">
                    <span className="fw-semibold">{u.unit_number}</span>
                    <span className={`badge ${UNIT_STATUS_BADGE[u.status]}`} style={{ fontSize: 10 }}>{UNIT_STATUS_LABEL[u.status]}</span>
                  </div>
                  <div className="text-muted small">
                    {UNIT_TYPE_LABEL[u.type]} · Floor {u.floor ?? '—'} · {formatPrice(u.price)}
                  </div>
                  {isAdmin && (
                    <div className="d-flex gap-2 mt-2">
                      <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2"
                        onClick={() => { setEditUnit(u); setModalMode('edit'); }}
                        aria-label={`Edit unit ${u.unit_number}`}>
                        <i className="bi bi-pencil" aria-hidden="true" />
                      </button>
                      <button type="button" className="btn btn-sm btn-outline-danger py-0 px-2"
                        onClick={() => { setDeleteTarget(u); setDeleteError(''); }}
                        aria-label={`Delete unit ${u.unit_number}`}>
                        <i className="bi bi-trash3" aria-hidden="true" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mt-3 pt-2 border-top">
              <span className="text-muted small">{total} unit{total !== 1 ? 's' : ''} · page {page} of {totalPages}</span>
              <div className="d-flex gap-1">
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => changePage(page - 1)} disabled={page <= 1} aria-label="Previous"><i className="bi bi-chevron-left" /></button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => changePage(page + 1)} disabled={page >= totalPages} aria-label="Next"><i className="bi bi-chevron-right" /></button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Unit form modal */}
      {modalMode !== 'none' && (
        <UnitForm mode={modalMode} buildingId={buildingId} unit={editUnit}
          onSuccess={(u) => { setModalMode('none'); onToast(modalMode === 'create' ? `Unit "${u.unit_number}" created.` : `Unit "${u.unit_number}" updated.`); fetchUnits(page, statusFilter, typeFilter); }}
          onCancel={() => setModalMode('none')} />
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <ConfirmModal
          title="Delete Unit?"
          message={`Are you sure you want to delete unit "${deleteTarget.unit_number}"?`}
          subMessage="This cannot be done if the unit has booking records."
          confirmLabel="Delete Unit"
          error={deleteError}
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)} />
      )}
    </div>
  );
}
