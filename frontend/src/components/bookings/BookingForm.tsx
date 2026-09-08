/**
 * BookingForm — create booking modal.
 *
 * Flow:
 *   1. Load leads (scoped by role — backend returns only accessible ones)
 *   2. Load all projects for project selector
 *   3. On project select, load buildings; on building select, load units (AVAILABLE only)
 *   4. User picks lead + unit + optional amount → POST /api/bookings
 *
 * Role behaviour:
 *   Sales: backend already scopes their leads; unit list always filtered to AVAILABLE.
 *   Admin: same UI, backend returns all active leads.
 *
 * Concurrency: if backend returns 409, show "Unit no longer available" and reset unit.
 *
 * Scrollability: modal-dialog-scrollable ensures the form works on small screens.
 */
import { type FormEvent, useCallback, useEffect, useState } from 'react';
import type { Booking } from '../../api/bookingsApi';
import { createBooking } from '../../api/bookingsApi';
import type { Lead } from '../../api/leadsApi';
import { listLeads } from '../../api/leadsApi';
import type { Building, Project, Unit } from '../../api/propertiesApi';
import { listBuildings, listProjects, listUnits } from '../../api/propertiesApi';
import { UNIT_TYPE_LABEL } from '../properties/propertyConstants';
import { parseApiError } from '../../hooks/useApiError';
import { isAxiosError } from 'axios';

interface BookingFormProps {
  onSuccess: (booking: Booking) => void;
  onCancel: () => void;
}

function formatPrice(p: number | null): string {
  if (p == null) return '';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(p);
}

export default function BookingForm({ onSuccess, onCancel }: BookingFormProps) {
  // ── Lead selection ─────────────────────────────────────────────────────────
  const [leads, setLeads]           = useState<Lead[]>([]);
  const [leadSearch, setLeadSearch] = useState('');
  const [leadsLoading, setLeadsLoading] = useState(false);
  const [leadsError, setLeadsError] = useState('');
  const [selectedLeadId, setSelectedLeadId] = useState<number | ''>('');
  const [leadListOpen, setLeadListOpen] = useState(false);

  // ── Project → Building → Unit cascade ─────────────────────────────────────
  const [projects, setProjects]           = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | ''>('');
  const [buildings, setBuildings]         = useState<Building[]>([]);
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | ''>('');
  const [units, setUnits]                 = useState<Unit[]>([]);
  const [selectedUnitId, setSelectedUnitId] = useState<number | ''>('');

  const [loadingBuildings, setLoadingBuildings] = useState(false);
  const [loadingUnits, setLoadingUnits]         = useState(false);

  // ── Amount ─────────────────────────────────────────────────────────────────
  const [amount, setAmount] = useState('');

  // ── Submit state ───────────────────────────────────────────────────────────
  const [saving, setSaving]     = useState(false);
  const [apiError, setApiError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ lead?: string; unit?: string; amount?: string }>({});

  // Load leads on mount — use size:200 to cover large pipelines for MVP.
  // Backend scopes by role: Sales users only receive their own assigned leads.
  const loadLeads = useCallback(() => {
    setLeadsLoading(true);
    setLeadsError('');
    listLeads({ size: 100, is_active: true })
      .then((res) => setLeads(res.items))
      .catch((err) => {
        setLeadsError(parseApiError(err));
      })
      .finally(() => setLeadsLoading(false));
  }, []);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  // Load projects on mount
  useEffect(() => {
    listProjects(1, 100)
      .then((res) => setProjects(res.items))
      .catch(() => {/* non-critical */});
  }, []);

  // Load buildings when project changes
  const loadBuildings = useCallback(async (projectId: number) => {
    setLoadingBuildings(true);
    setBuildings([]);
    setSelectedBuildingId('');
    setUnits([]);
    setSelectedUnitId('');
    try {
      const res = await listBuildings(projectId);
      setBuildings(res.items);
    } finally {
      setLoadingBuildings(false);
    }
  }, []);

  // Load AVAILABLE units when building changes
  const loadUnits = useCallback(async (buildingId: number) => {
    setLoadingUnits(true);
    setUnits([]);
    setSelectedUnitId('');
    try {
      const res = await listUnits(buildingId, { status: 'AVAILABLE', size: 100 });
      setUnits(res.items);
    } finally {
      setLoadingUnits(false);
    }
  }, []);

  function handleProjectChange(id: number | '') {
    setSelectedProjectId(id);
    setSelectedBuildingId('');
    setUnits([]);
    setSelectedUnitId('');
    if (id) loadBuildings(id as number);
    else setBuildings([]);
  }

  function handleBuildingChange(id: number | '') {
    setSelectedBuildingId(id);
    setUnits([]);
    setSelectedUnitId('');
    if (id) loadUnits(id as number);
  }

  // Filter leads by search (client-side on the already-fetched 50 leads)
  const filteredLeads = leads.filter((l) =>
    !leadSearch || l.name.toLowerCase().includes(leadSearch.toLowerCase()) ||
    (l.email ?? '').toLowerCase().includes(leadSearch.toLowerCase())
  );

  const selectedUnit = units.find((u) => u.id === selectedUnitId);

  function validate(): boolean {
    const next: typeof fieldErrors = {};
    if (!selectedLeadId) next.lead = 'Please select a lead.';
    if (!selectedUnitId) next.unit = 'Please select an available unit.';
    if (amount && (isNaN(Number(amount)) || Number(amount) < 0)) {
      next.amount = 'Amount must be a non-negative number.';
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setApiError('');
    if (!validate()) return;
    setSaving(true);
    try {
      const result = await createBooking({
        lead_id: selectedLeadId as number,
        unit_id: selectedUnitId as number,
        ...(amount ? { amount: Number(amount) } : {}),
      });
      onSuccess(result);
    } catch (err) {
      // 409 = unit no longer available
      if (isAxiosError(err) && err.response?.status === 409) {
        setApiError('This unit is no longer available. Please select another unit.');
        // Reset unit selection and reload
        setSelectedUnitId('');
        if (selectedBuildingId) loadUnits(selectedBuildingId as number);
      } else {
        setApiError(parseApiError(err));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal d-block" tabIndex={-1} role="dialog" aria-modal="true"
      aria-label="Create Booking" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content border-0 shadow">
          <div className="modal-header">
            <h5 className="modal-title">
              <i className="bi bi-calendar-plus-fill me-2 text-primary" aria-hidden="true" />
              Create Booking
            </h5>
            <button type="button" className="btn-close" onClick={onCancel} disabled={saving} aria-label="Close" />
          </div>

          <form id="booking-form" onSubmit={handleSubmit} noValidate>
            <div className="modal-body">
              {apiError && (
                <div className="alert alert-danger small py-2 d-flex align-items-center gap-2 mb-3">
                  <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />
                  {apiError}
                </div>
              )}

              {/* ── Lead selection ──────────────────────────────────────────── */}
              <div className="mb-3">
                <label htmlFor="bk-lead-search" className="form-label fw-medium">
                  Customer / Lead <span className="text-danger">*</span>
                </label>
                {leadsError ? (
                  <div className="alert alert-warning small py-2 d-flex align-items-center gap-2">
                    <i className="bi bi-exclamation-triangle-fill flex-shrink-0" aria-hidden="true" />
                    <span className="flex-grow-1">Failed to load leads: {leadsError}</span>
                    <button type="button" className="btn btn-sm btn-outline-warning py-0 px-2 flex-shrink-0"
                      onClick={loadLeads} disabled={leadsLoading}>
                      Retry
                    </button>
                  </div>
                ) : (
                  <>
                    {/* Search input — opens the list on focus */}
                    <input
                      id="bk-lead-search"
                      type="text"
                      className="form-control form-control-sm mb-1"
                      placeholder={selectedLeadId !== '' ? 'Change lead…' : 'Search leads…'}
                      value={leadSearch}
                      onChange={(e) => { setLeadSearch(e.target.value); setLeadListOpen(true); }}
                      onFocus={() => setLeadListOpen(true)}
                      onBlur={() => setLeadListOpen(false)}
                      disabled={saving || leadsLoading}
                      autoComplete="off"
                    />
                    {/* Selected lead badge — shown when list is closed */}
                    {selectedLeadId !== '' && !leadListOpen && (() => {
                      const picked = leads.find((l) => l.id === selectedLeadId);
                      return picked ? (
                        <div
                          className="d-flex align-items-center gap-2 px-2 py-1 rounded bg-primary bg-opacity-10 border border-primary border-opacity-25 small"
                          style={{ cursor: 'pointer' }}
                          onClick={() => !saving && setLeadListOpen(true)}
                        >
                          <i className="bi bi-person-check-fill text-primary flex-shrink-0" aria-hidden="true" />
                          <span className="flex-grow-1 fw-medium">{picked.name}{picked.email ? ` (${picked.email})` : ''}</span>
                          <button
                            type="button"
                            className="btn-close"
                            style={{ fontSize: '0.55rem' }}
                            aria-label="Clear lead selection"
                            onClick={(e) => { e.stopPropagation(); setSelectedLeadId(''); setLeadListOpen(false); setLeadSearch(''); setFieldErrors((p) => ({ ...p, lead: undefined })); }}
                            disabled={saving}
                          />
                        </div>
                      ) : null;
                    })()}
                    {/* Dropdown list — only when open */}
                    {leadListOpen && (
                      <div
                        className={`border rounded overflow-auto ${fieldErrors.lead ? 'border-danger' : ''}`}
                        style={{ maxHeight: 160 }}
                        role="listbox"
                        aria-label="Lead list"
                      >
                        {leadsLoading ? (
                          <div className="px-3 py-2 text-muted small">Loading leads…</div>
                        ) : filteredLeads.length === 0 ? (
                          <div className="px-3 py-2 text-muted small">
                            {leadSearch ? 'No leads match your search.' : 'No active leads found.'}
                          </div>
                        ) : (
                          filteredLeads.map((l) => {
                            const isSelected = selectedLeadId === l.id;
                            return (
                              <div
                                key={l.id}
                                id={`bk-lead-opt-${l.id}`}
                                role="option"
                                aria-selected={isSelected}
                                className={`px-3 py-2 small d-flex align-items-center gap-2 ${isSelected ? 'bg-primary text-white' : 'hover-bg'}`}
                                style={{ cursor: saving ? 'not-allowed' : 'pointer', userSelect: 'none' }}
                                onMouseDown={(e) => e.preventDefault()} // prevent input blur before click registers
                                onClick={() => {
                                  if (saving) return;
                                  setSelectedLeadId(l.id);
                                  setLeadListOpen(false);
                                  setLeadSearch('');
                                  setFieldErrors((p) => ({ ...p, lead: undefined }));
                                }}
                              >
                                {isSelected
                                  ? <i className="bi bi-check2 flex-shrink-0" aria-hidden="true" />
                                  : <i className="bi bi-person flex-shrink-0 text-muted" aria-hidden="true" />
                                }
                                <span>{l.name}{l.email ? ` (${l.email})` : ''}</span>
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                    {fieldErrors.lead && <div className="text-danger small mt-1">{fieldErrors.lead}</div>}
                  </>
                )}
              </div>

              {/* ── Project → Building → Unit cascade ───────────────────────── */}
              <fieldset className={`mb-3 p-3 rounded-3 border ${fieldErrors.unit ? 'border-danger' : ''}`}>
                <legend className="form-label fw-medium float-none w-auto px-1 small">
                  Unit <span className="text-danger">*</span>
                </legend>

                {/* Project */}
                <div className="mb-2">
                  <label htmlFor="bk-project" className="form-label form-label-sm">Project</label>
                  <select id="bk-project" className="form-select form-select-sm"
                    value={selectedProjectId}
                    onChange={(e) => handleProjectChange(e.target.value ? Number(e.target.value) : '')}
                    disabled={saving}>
                    <option value="">— Select project —</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>

                {/* Building */}
                {selectedProjectId !== '' && (
                  <div className="mb-2">
                    <label htmlFor="bk-building" className="form-label form-label-sm">Building</label>
                    <select id="bk-building" className="form-select form-select-sm"
                      value={selectedBuildingId}
                      onChange={(e) => handleBuildingChange(e.target.value ? Number(e.target.value) : '')}
                      disabled={saving || loadingBuildings}>
                      <option value="">— Select building —</option>
                      {buildings.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                    </select>
                    {loadingBuildings && <div className="text-muted small mt-1">Loading buildings…</div>}
                  </div>
                )}

                {/* Unit */}
                {selectedBuildingId !== '' && (
                  <div>
                    <label htmlFor="bk-unit" className="form-label form-label-sm">Available Unit</label>
                    <select id="bk-unit" className="form-select form-select-sm"
                      value={selectedUnitId}
                      onChange={(e) => { setSelectedUnitId(e.target.value ? Number(e.target.value) : ''); setFieldErrors((p) => ({...p, unit: undefined})); setApiError(''); }}
                      disabled={saving || loadingUnits}>
                      <option value="">— Select unit —</option>
                      {units.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.unit_number} · {UNIT_TYPE_LABEL[u.type]}{u.floor != null ? ` · Floor ${u.floor}` : ''}{u.price ? ` · ${new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:0}).format(u.price)}` : ''}
                        </option>
                      ))}
                    </select>
                    {loadingUnits && <div className="text-muted small mt-1">Loading units…</div>}
                    {!loadingUnits && !!selectedBuildingId && units.length === 0 && (
                      <div className="text-warning small mt-1">
                        <i className="bi bi-exclamation-triangle me-1" aria-hidden="true" />
                        No available units in this building.
                      </div>
                    )}
                  </div>
                )}

                {/* Selected unit preview */}
                {selectedUnit && (
                  <div className="mt-2 p-2 rounded-3 bg-success bg-opacity-10 small">
                    <i className="bi bi-check-circle-fill text-success me-1" aria-hidden="true" />
                    <strong>{selectedUnit.unit_number}</strong> · {UNIT_TYPE_LABEL[selectedUnit.type]}
                    {selectedUnit.price && ` · ${formatPrice(selectedUnit.price)}`}
                    <span className="ms-2 badge bg-success" style={{ fontSize: 10 }}>Available</span>
                  </div>
                )}

                {fieldErrors.unit && <div className="text-danger small mt-1">{fieldErrors.unit}</div>}
              </fieldset>

              {/* ── Amount ──────────────────────────────────────────────────── */}
              <div className="mb-3">
                <label htmlFor="bk-amount" className="form-label fw-medium">Amount (₹) <span className="text-muted fw-normal small">optional</span></label>
                <input id="bk-amount" type="number" min={0} step="any"
                  className={`form-control ${fieldErrors.amount ? 'is-invalid' : ''}`}
                  value={amount}
                  onChange={(e) => { setAmount(e.target.value); setFieldErrors((p) => ({...p, amount: undefined})); }}
                  disabled={saving}
                  placeholder={selectedUnit?.price ? String(selectedUnit.price) : '0'} />
                {fieldErrors.amount && <div className="invalid-feedback">{fieldErrors.amount}</div>}
                {selectedUnit?.price && !amount && (
                  <div className="form-text">Suggested: {formatPrice(selectedUnit.price)}</div>
                )}
              </div>
            </div>
          </form>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
            <button type="submit" form="booking-form" className="btn btn-primary" disabled={saving}>
              {saving
                ? <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />Booking…</>
                : <><i className="bi bi-calendar-check me-1" aria-hidden="true" />Create Booking</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
