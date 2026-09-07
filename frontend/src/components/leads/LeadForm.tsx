/**
 * LeadForm — Bootstrap modal for creating or editing a lead.
 *
 * Behaviour:
 *   mode='create' → empty form, POST /api/leads
 *   mode='edit'   → pre-filled from `lead` prop, PUT /api/leads/{id}
 *
 * Role logic:
 *   ADMIN: can see and set assigned_to (user list loaded once, cached in prop).
 *   SALES: no assigned_to field — backend forces assignment to themselves.
 */
import { type FormEvent, useEffect, useState } from 'react';
import type { Lead, LeadCreateRequest, LeadUpdateRequest, UserOption } from '../../api/leadsApi';
import { createLead, updateLead } from '../../api/leadsApi';
import type { LeadSource, LeadStage } from '../../api/types';
import { STAGE_OPTIONS, SOURCE_OPTIONS } from './leadConstants';
import { parseApiError } from '../../hooks/useApiError';

interface LeadFormProps {
  mode: 'create' | 'edit';
  lead?: Lead;             // required for edit
  isAdmin: boolean;
  users: UserOption[];     // for assignee dropdown (admin only)
  onSuccess: (lead: Lead) => void;
  onCancel: () => void;
}

interface FormState {
  name: string;
  email: string;
  phone: string;
  source: LeadSource | '';
  stage: LeadStage;
  assigned_to: string;   // stored as string for <select>, converted to int on submit
}

function emptyForm(): FormState {
  return { name: '', email: '', phone: '', source: '', stage: 'NEW', assigned_to: '' };
}

function leadToForm(lead: Lead): FormState {
  return {
    name:        lead.name,
    email:       lead.email ?? '',
    phone:       lead.phone ?? '',
    source:      lead.source ?? '',
    stage:       lead.stage,
    assigned_to: lead.assigned_to != null ? String(lead.assigned_to) : '',
  };
}

export default function LeadForm({
  mode,
  lead,
  isAdmin,
  users,
  onSuccess,
  onCancel,
}: LeadFormProps) {
  const [form, setForm]       = useState<FormState>(mode === 'edit' && lead ? leadToForm(lead) : emptyForm());
  const [errors, setErrors]   = useState<Partial<Record<keyof FormState, string>>>({});
  const [apiError, setApiError] = useState('');
  const [saving, setSaving]   = useState(false);

  // Reset when modal re-opens with a different lead
  useEffect(() => {
    setForm(mode === 'edit' && lead ? leadToForm(lead) : emptyForm());
    setErrors({});
    setApiError('');
  }, [mode, lead]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((p) => ({ ...p, [key]: value }));
    setErrors((p) => ({ ...p, [key]: undefined }));
  }

  function validate(): boolean {
    const next: Partial<Record<keyof FormState, string>> = {};
    if (!form.name.trim()) {
      next.name = 'Name is required.';
    }
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      next.email = 'Enter a valid email address.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setApiError('');
    if (!validate()) return;
    setSaving(true);
    try {
      let result: Lead;
      if (mode === 'create') {
        const payload: LeadCreateRequest = {
          name:   form.name.trim(),
          ...(form.email  ? { email:  form.email.trim() }  : {}),
          ...(form.phone  ? { phone:  form.phone.trim() }  : {}),
          ...(form.source ? { source: form.source as LeadSource } : {}),
          stage:  form.stage,
          ...(isAdmin && form.assigned_to ? { assigned_to: Number(form.assigned_to) } : {}),
        };
        result = await createLead(payload);
      } else {
        const payload: LeadUpdateRequest = {
          name:   form.name.trim() || undefined,
          email:  form.email.trim() || null,
          phone:  form.phone.trim() || null,
          source: (form.source as LeadSource) || null,
          stage:  form.stage,
          ...(isAdmin ? { assigned_to: form.assigned_to ? Number(form.assigned_to) : null } : {}),
        };
        result = await updateLead(lead!.id, payload);
      }
      onSuccess(result);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  const title = mode === 'create' ? 'Add Lead' : 'Edit Lead';

  return (
    <div
      className="modal d-block"
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
    >
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content border-0 shadow">
          <div className="modal-header">
            <h5 className="modal-title">
              <i className={`bi ${mode === 'create' ? 'bi-person-plus-fill' : 'bi-pencil-fill'} me-2 text-primary`} aria-hidden="true" />
              {title}
            </h5>
            <button type="button" className="btn-close" onClick={onCancel} aria-label="Close" disabled={saving} />
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className="modal-body">
              {apiError && (
                <div className="alert alert-danger small py-2 d-flex align-items-center gap-2">
                  <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />
                  {apiError}
                </div>
              )}

              {/* Name */}
              <div className="mb-3">
                <label htmlFor="lf-name" className="form-label fw-medium">Name <span className="text-danger">*</span></label>
                <input
                  id="lf-name"
                  type="text"
                  className={`form-control ${errors.name ? 'is-invalid' : ''}`}
                  value={form.name}
                  onChange={(e) => set('name', e.target.value)}
                  disabled={saving}
                />
                {errors.name && <div className="invalid-feedback">{errors.name}</div>}
              </div>

              {/* Email */}
              <div className="mb-3">
                <label htmlFor="lf-email" className="form-label fw-medium">Email</label>
                <input
                  id="lf-email"
                  type="email"
                  className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                  disabled={saving}
                />
                {errors.email && <div className="invalid-feedback">{errors.email}</div>}
              </div>

              {/* Phone */}
              <div className="mb-3">
                <label htmlFor="lf-phone" className="form-label fw-medium">Phone</label>
                <input
                  id="lf-phone"
                  type="tel"
                  className="form-control"
                  value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                  disabled={saving}
                />
              </div>

              {/* Source + Stage row */}
              <div className="row g-3 mb-3">
                <div className="col-6">
                  <label htmlFor="lf-source" className="form-label fw-medium">Source</label>
                  <select
                    id="lf-source"
                    className="form-select"
                    value={form.source}
                    onChange={(e) => set('source', e.target.value as LeadSource | '')}
                    disabled={saving}
                  >
                    <option value="">— Select —</option>
                    {SOURCE_OPTIONS.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="col-6">
                  <label htmlFor="lf-stage" className="form-label fw-medium">Stage</label>
                  <select
                    id="lf-stage"
                    className="form-select"
                    value={form.stage}
                    onChange={(e) => set('stage', e.target.value as LeadStage)}
                    disabled={saving}
                  >
                    {STAGE_OPTIONS.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Assigned to — Admin only */}
              {isAdmin && (
                <div className="mb-3">
                  <label htmlFor="lf-assigned" className="form-label fw-medium">Assigned To</label>
                  <select
                    id="lf-assigned"
                    className="form-select"
                    value={form.assigned_to}
                    onChange={(e) => set('assigned_to', e.target.value)}
                    disabled={saving}
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? (
                  <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />Saving…</>
                ) : mode === 'create' ? 'Create Lead' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
