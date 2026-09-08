/**
 * ProjectForm — modal for creating or editing a project.
 */
import { type FormEvent, useEffect, useState } from 'react';
import type { Project, ProjectCreateRequest } from '../../api/propertiesApi';
import { createProject, updateProject } from '../../api/propertiesApi';
import { parseApiError } from '../../hooks/useApiError';

interface ProjectFormProps {
  mode: 'create' | 'edit';
  project?: Project;
  onSuccess: (project: Project) => void;
  onCancel: () => void;
}

interface FormState { name: string; location: string; description: string; }
const empty = (): FormState => ({ name: '', location: '', description: '' });
const fromProject = (p: Project): FormState => ({
  name: p.name, location: p.location ?? '', description: p.description ?? '',
});

export default function ProjectForm({ mode, project, onSuccess, onCancel }: ProjectFormProps) {
  const [form, setForm]       = useState<FormState>(mode === 'edit' && project ? fromProject(project) : empty());
  const [errors, setErrors]   = useState<Partial<FormState>>({});
  const [apiError, setApiError] = useState('');
  const [saving, setSaving]   = useState(false);

  useEffect(() => {
    setForm(mode === 'edit' && project ? fromProject(project) : empty());
    setErrors({});
    setApiError('');
  }, [mode, project]);

  function set<K extends keyof FormState>(key: K, v: string) {
    setForm((p) => ({ ...p, [key]: v }));
    setErrors((p) => ({ ...p, [key]: undefined }));
  }

  function validate() {
    const next: Partial<FormState> = {};
    if (!form.name.trim()) next.name = 'Project name is required.';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setApiError('');
    if (!validate()) return;
    setSaving(true);
    try {
      const payload: ProjectCreateRequest = {
        name:        form.name.trim(),
        location:    form.location.trim()    || undefined,
        description: form.description.trim() || undefined,
      };
      const result = mode === 'create'
        ? await createProject(payload)
        : await updateProject(project!.id, payload);
      onSuccess(result);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  const title = mode === 'create' ? 'Add Project' : 'Edit Project';

  return (
    <div className="modal d-block" tabIndex={-1} role="dialog" aria-modal="true" aria-label={title}
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content border-0 shadow">
          <div className="modal-header">
            <h5 className="modal-title">
              <i className={`bi ${mode === 'create' ? 'bi-building-add' : 'bi-pencil-fill'} me-2 text-primary`} aria-hidden="true" />
              {title}
            </h5>
            <button type="button" className="btn-close" onClick={onCancel} disabled={saving} aria-label="Close" />
          </div>
          <form id="project-form" onSubmit={handleSubmit} noValidate>
            <div className="modal-body">
              {apiError && (
                <div className="alert alert-danger small py-2 d-flex align-items-center gap-2">
                  <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />{apiError}
                </div>
              )}
              <div className="mb-3">
                <label htmlFor="pf-name" className="form-label fw-medium">Name <span className="text-danger">*</span></label>
                <input id="pf-name" type="text" className={`form-control ${errors.name ? 'is-invalid' : ''}`}
                  value={form.name} onChange={(e) => set('name', e.target.value)} disabled={saving} />
                {errors.name && <div className="invalid-feedback">{errors.name}</div>}
              </div>
              <div className="mb-3">
                <label htmlFor="pf-loc" className="form-label fw-medium">Location</label>
                <input id="pf-loc" type="text" className="form-control" value={form.location}
                  onChange={(e) => set('location', e.target.value)} disabled={saving} placeholder="e.g. Bandra West, Mumbai" />
              </div>
              <div className="mb-3">
                <label htmlFor="pf-desc" className="form-label fw-medium">Description</label>
                <textarea id="pf-desc" className="form-control" rows={3} value={form.description}
                  onChange={(e) => set('description', e.target.value)} disabled={saving} />
              </div>
            </div>
          </form>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
            <button type="submit" form="project-form" className="btn btn-primary" disabled={saving}>
              {saving ? <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />Saving…</> : mode === 'create' ? 'Create Project' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
