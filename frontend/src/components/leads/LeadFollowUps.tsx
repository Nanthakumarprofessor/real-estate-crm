/**
 * LeadFollowUps — follow-up list + create/update forms inside Lead Details.
 *
 * Rules:
 *   - follow_up_at must be a future datetime.
 *   - Status can be updated via PUT /api/follow-ups/{id}.
 *   - Backend enforces access rights; 403 shown on rejection.
 */
import { type FormEvent, useCallback, useEffect, useState } from 'react';
import type { FollowUp } from '../../api/leadsApi';
import { createFollowUp, listFollowUps, updateFollowUp } from '../../api/leadsApi';
import type { FollowUpStatus } from '../../api/types';
import { FOLLOW_UP_STATUS_BADGE, FOLLOW_UP_STATUS_LABEL } from './leadConstants';
import { parseApiError } from '../../hooks/useApiError';

interface LeadFollowUpsProps {
  leadId: number;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/** Convert local datetime string to a UTC ISO string the backend accepts. */
function localToISO(localDt: string): string {
  return new Date(localDt).toISOString();
}


export default function LeadFollowUps({ leadId }: LeadFollowUpsProps) {
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [createDt, setCreateDt]     = useState('');
  const [createNotes, setCreateNotes] = useState('');
  const [creating, setCreating]     = useState(false);
  const [createError, setCreateError] = useState('');

  // Inline status update
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchFollowUps = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listFollowUps(leadId);
      setFollowUps(res.items);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => { fetchFollowUps(); }, [fetchFollowUps]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreateError('');
    if (!createDt) {
      setCreateError('Date and time is required.');
      return;
    }
    const dt = new Date(createDt);
    if (dt <= new Date()) {
      setCreateError('Follow-up date must be in the future.');
      return;
    }
    setCreating(true);
    try {
      await createFollowUp(leadId, {
        follow_up_at: localToISO(createDt),
        notes: createNotes.trim() || undefined,
      });
      setShowCreate(false);
      setCreateDt('');
      setCreateNotes('');
      await fetchFollowUps();
    } catch (err) {
      setCreateError(parseApiError(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(fu: FollowUp, status: FollowUpStatus) {
    setUpdatingId(fu.id);
    try {
      const updated = await updateFollowUp(fu.id, { status });
      setFollowUps((prev) => prev.map((f) => (f.id === fu.id ? updated : f)));
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div>
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h6 className="fw-semibold mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-calendar-check-fill text-info" aria-hidden="true" />
          Follow-ups
          <span className="badge bg-secondary rounded-pill ms-1">{followUps.length}</span>
        </h6>
        <button
          type="button"
          className="btn btn-sm btn-outline-primary"
          onClick={() => setShowCreate((v) => !v)}
        >
          <i className="bi bi-plus" aria-hidden="true" />
          {showCreate ? 'Cancel' : 'Add'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="p-3 mb-3 rounded-3 border bg-light">
          {createError && (
            <div className="alert alert-danger small py-2 mb-2">{createError}</div>
          )}
          <div className="mb-2">
            <label htmlFor="fu-dt" className="form-label small fw-medium">Date & Time <span className="text-danger">*</span></label>
            <input
              id="fu-dt"
              type="datetime-local"
              className="form-control form-control-sm"
              value={createDt}
              onChange={(e) => setCreateDt(e.target.value)}
              disabled={creating}
            />
          </div>
          <div className="mb-2">
            <label htmlFor="fu-notes" className="form-label small fw-medium">Notes</label>
            <textarea
              id="fu-notes"
              className="form-control form-control-sm"
              rows={2}
              value={createNotes}
              onChange={(e) => setCreateNotes(e.target.value)}
              disabled={creating}
              placeholder="Optional note…"
            />
          </div>
          <button type="submit" className="btn btn-sm btn-primary" disabled={creating}>
            {creating
              ? <><span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />Saving…</>
              : 'Create Follow-up'}
          </button>
        </form>
      )}

      {error && <div className="alert alert-warning small py-2">{error}</div>}

      {/* Follow-up list */}
      {loading ? (
        <div className="py-3 text-center">
          <div className="spinner-border spinner-border-sm text-primary" role="status">
            <span className="visually-hidden">Loading…</span>
          </div>
        </div>
      ) : followUps.length === 0 ? (
        <p className="text-muted small">No follow-ups yet.</p>
      ) : (
        <div className="d-flex flex-column gap-2">
          {followUps.map((fu) => {
            const isOverdue = fu.status === 'PENDING' && new Date(fu.follow_up_at) < new Date();
            return (
              <div
                key={fu.id}
                className={`p-3 rounded-3 border ${isOverdue ? 'border-warning bg-warning bg-opacity-10' : 'bg-light'}`}
              >
                <div className="d-flex justify-content-between align-items-start gap-2">
                  <div className="flex-grow-1">
                    <div className="small fw-medium">
                      {isOverdue && <i className="bi bi-exclamation-circle-fill text-warning me-1" aria-label="Overdue" />}
                      {formatDate(fu.follow_up_at)}
                    </div>
                    {fu.notes && <p className="text-muted small mb-1 mt-1">{fu.notes}</p>}
                  </div>
                  <div className="d-flex align-items-center gap-2 flex-shrink-0">
                    <span className={`badge ${FOLLOW_UP_STATUS_BADGE[fu.status]}`} style={{ fontSize: 10 }}>
                      {FOLLOW_UP_STATUS_LABEL[fu.status]}
                    </span>
                    {fu.status === 'PENDING' && (
                      <div className="dropdown">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary py-0 px-1"
                          data-bs-toggle="dropdown"
                          aria-expanded="false"
                          disabled={updatingId === fu.id}
                          aria-label="Update status"
                        >
                          {updatingId === fu.id
                            ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                            : <i className="bi bi-three-dots" aria-hidden="true" />}
                        </button>
                        <ul className="dropdown-menu dropdown-menu-end shadow-sm" style={{ minWidth: 140 }}>
                          <li>
                            <button className="dropdown-item small" type="button"
                              onClick={() => handleStatusChange(fu, 'COMPLETED')}>
                              <i className="bi bi-check-circle me-2 text-success" aria-hidden="true" />Mark Completed
                            </button>
                          </li>
                          <li>
                            <button className="dropdown-item small" type="button"
                              onClick={() => handleStatusChange(fu, 'CANCELLED')}>
                              <i className="bi bi-x-circle me-2 text-secondary" aria-hidden="true" />Cancel
                            </button>
                          </li>
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
