/**
 * BuildingForm — inline form (not a modal) for adding/editing a building.
 * Rendered inside ProjectDetails so it stays contextual.
 */
import { type FormEvent, useEffect, useState } from 'react';
import type { Building, BuildingCreateRequest } from '../../api/propertiesApi';
import { createBuilding, updateBuilding } from '../../api/propertiesApi';
import { parseApiError } from '../../hooks/useApiError';

interface BuildingFormProps {
  mode: 'create' | 'edit';
  projectId: number;
  building?: Building;
  onSuccess: (b: Building) => void;
  onCancel: () => void;
}

interface FormState { name: string; total_floors: string; }
const empty = (): FormState => ({ name: '', total_floors: '' });
const fromBuilding = (b: Building): FormState => ({
  name: b.name, total_floors: b.total_floors != null ? String(b.total_floors) : '',
});

export default function BuildingForm({ mode, projectId, building, onSuccess, onCancel }: BuildingFormProps) {
  const [form, setForm]       = useState<FormState>(mode === 'edit' && building ? fromBuilding(building) : empty());
  const [errors, setErrors]   = useState<Partial<FormState>>({});
  const [apiError, setApiError] = useState('');
  const [saving, setSaving]   = useState(false);

  useEffect(() => {
    setForm(mode === 'edit' && building ? fromBuilding(building) : empty());
    setErrors({});
    setApiError('');
  }, [mode, building]);

  function set<K extends keyof FormState>(key: K, v: string) {
    setForm((p) => ({ ...p, [key]: v }));
    setErrors((p) => ({ ...p, [key]: undefined }));
  }

  function validate() {
    const next: Partial<FormState> = {};
    if (!form.name.trim()) next.name = 'Building name is required.';
    if (form.total_floors && (isNaN(Number(form.total_floors)) || Number(form.total_floors) < 1)) {
      next.total_floors = 'Total floors must be at least 1.';
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
      const payload: BuildingCreateRequest = {
        name: form.name.trim(),
        ...(form.total_floors ? { total_floors: Number(form.total_floors) } : {}),
      };
      const result = mode === 'create'
        ? await createBuilding(projectId, payload)
        : await updateBuilding(building!.id, payload);
      onSuccess(result);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="p-3 rounded-3 border bg-light mb-3">
      <div className="fw-medium small mb-2">
        {mode === 'create' ? 'Add Building' : 'Edit Building'}
      </div>
      {apiError && (
        <div className="alert alert-danger small py-2 mb-2">{apiError}</div>
      )}
      <div className="row g-2">
        <div className="col-12 col-sm-6">
          <label htmlFor="bf-name" className="form-label form-label-sm">Name <span className="text-danger">*</span></label>
          <input id="bf-name" type="text" className={`form-control form-control-sm ${errors.name ? 'is-invalid' : ''}`}
            value={form.name} onChange={(e) => set('name', e.target.value)} disabled={saving} />
          {errors.name && <div className="invalid-feedback">{errors.name}</div>}
        </div>
        <div className="col-12 col-sm-4">
          <label htmlFor="bf-floors" className="form-label form-label-sm">Total Floors</label>
          <input id="bf-floors" type="number" min={1} className={`form-control form-control-sm ${errors.total_floors ? 'is-invalid' : ''}`}
            value={form.total_floors} onChange={(e) => set('total_floors', e.target.value)} disabled={saving} />
          {errors.total_floors && <div className="invalid-feedback">{errors.total_floors}</div>}
        </div>
        <div className="col-12 col-sm-2 d-flex align-items-end gap-1">
          <button type="submit" className="btn btn-sm btn-primary" disabled={saving}>
            {saving ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> : 'Save'}
          </button>
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={onCancel} disabled={saving}>✕</button>
        </div>
      </div>
    </form>
  );
}
