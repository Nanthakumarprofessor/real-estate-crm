/**
 * UnitForm — modal for creating or editing a unit.
 */
import { type FormEvent, useEffect, useState } from 'react';
import type { Unit, UnitCreateRequest, UnitStatus, UnitType } from '../../api/propertiesApi';
import { createUnit, updateUnit } from '../../api/propertiesApi';
import { UNIT_TYPE_OPTIONS } from './propertyConstants';
import { parseApiError } from '../../hooks/useApiError';

interface UnitFormProps {
  mode: 'create' | 'edit';
  buildingId: number;
  unit?: Unit;
  onSuccess: (unit: Unit) => void;
  onCancel: () => void;
}

interface FormState {
  unit_number: string;
  type: UnitType;
  floor: string;
  price: string;
  status: UnitStatus;
}

const empty = (): FormState => ({ unit_number: '', type: '2BHK', floor: '', price: '', status: 'AVAILABLE' });
const fromUnit = (u: Unit): FormState => ({
  unit_number: u.unit_number,
  type:        u.type,
  floor:       u.floor != null ? String(u.floor) : '',
  price:       u.price != null ? String(u.price) : '',
  status:      u.status,
});

export default function UnitForm({ mode, buildingId, unit, onSuccess, onCancel }: UnitFormProps) {
  const [form, setForm]       = useState<FormState>(mode === 'edit' && unit ? fromUnit(unit) : empty());
  const [errors, setErrors]   = useState<Partial<Record<keyof FormState, string>>>({});
  const [apiError, setApiError] = useState('');
  const [saving, setSaving]   = useState(false);

  useEffect(() => {
    setForm(mode === 'edit' && unit ? fromUnit(unit) : empty());
    setErrors({});
    setApiError('');
  }, [mode, unit]);

  function set<K extends keyof FormState>(key: K, v: string) {
    setForm((p) => ({ ...p, [key]: v }));
    setErrors((p) => ({ ...p, [key]: undefined }));
  }

  function validate() {
    const next: Partial<Record<keyof FormState, string>> = {};
    if (!form.unit_number.trim()) next.unit_number = 'Unit number is required.';
    if (form.floor !== '' && (isNaN(Number(form.floor)) || Number(form.floor) < 0)) {
      next.floor = 'Floor must be 0 or greater.';
    }
    if (form.price !== '' && (isNaN(Number(form.price)) || Number(form.price) < 0)) {
      next.price = 'Price must be non-negative.';
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
      const payload: UnitCreateRequest = {
        unit_number: form.unit_number.trim(),
        type:   form.type,
        status: form.status,
        ...(form.floor !== '' ? { floor: Number(form.floor) } : {}),
        ...(form.price !== '' ? { price: Number(form.price) } : {}),
      };
      const result = mode === 'create'
        ? await createUnit(buildingId, payload)
        : await updateUnit(unit!.id, payload);
      onSuccess(result);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  const title = mode === 'create' ? 'Add Unit' : 'Edit Unit';

  return (
    <div className="modal d-block" tabIndex={-1} role="dialog" aria-modal="true" aria-label={title}
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content border-0 shadow">
          <div className="modal-header">
            <h5 className="modal-title">
              <i className={`bi ${mode === 'create' ? 'bi-plus-circle-fill' : 'bi-pencil-fill'} me-2 text-primary`} aria-hidden="true" />
              {title}
            </h5>
            <button type="button" className="btn-close" onClick={onCancel} disabled={saving} aria-label="Close" />
          </div>
          <form id="unit-form" onSubmit={handleSubmit} noValidate>
            <div className="modal-body">
              {apiError && (
                <div className="alert alert-danger small py-2 d-flex align-items-center gap-2">
                  <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />{apiError}
                </div>
              )}
              <div className="mb-3">
                <label htmlFor="uf-num" className="form-label fw-medium">Unit Number <span className="text-danger">*</span></label>
                <input id="uf-num" type="text" className={`form-control ${errors.unit_number ? 'is-invalid' : ''}`}
                  value={form.unit_number} onChange={(e) => set('unit_number', e.target.value)} disabled={saving}
                  placeholder="e.g. A-101" />
                {errors.unit_number && <div className="invalid-feedback">{errors.unit_number}</div>}
              </div>
              <div className="row g-3 mb-3">
                <div className="col-6">
                  <label htmlFor="uf-type" className="form-label fw-medium">Type <span className="text-danger">*</span></label>
                  <select id="uf-type" className="form-select" value={form.type}
                    onChange={(e) => set('type', e.target.value as UnitType)} disabled={saving}>
                    {UNIT_TYPE_OPTIONS.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="col-6">
                  <label htmlFor="uf-status" className="form-label fw-medium">Status</label>
                  <select id="uf-status" className="form-select" value={form.status}
                    onChange={(e) => set('status', e.target.value as UnitStatus)} disabled={saving}>
                    <option value="AVAILABLE">Available</option>
                    <option value="BOOKED">Booked</option>
                  </select>
                </div>
              </div>
              <div className="row g-3">
                <div className="col-6">
                  <label htmlFor="uf-floor" className="form-label fw-medium">Floor</label>
                  <input id="uf-floor" type="number" min={0} className={`form-control ${errors.floor ? 'is-invalid' : ''}`}
                    value={form.floor} onChange={(e) => set('floor', e.target.value)} disabled={saving} placeholder="0" />
                  {errors.floor && <div className="invalid-feedback">{errors.floor}</div>}
                </div>
                <div className="col-6">
                  <label htmlFor="uf-price" className="form-label fw-medium">Price (₹)</label>
                  <input id="uf-price" type="number" min={0} className={`form-control ${errors.price ? 'is-invalid' : ''}`}
                    value={form.price} onChange={(e) => set('price', e.target.value)} disabled={saving} placeholder="0" />
                  {errors.price && <div className="invalid-feedback">{errors.price}</div>}
                </div>
              </div>
            </div>
          </form>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
            <button type="submit" form="unit-form" className="btn btn-primary" disabled={saving}>
              {saving ? <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />Saving…</> : mode === 'create' ? 'Create Unit' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
