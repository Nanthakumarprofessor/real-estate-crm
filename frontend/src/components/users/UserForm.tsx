/**
 * UserForm — modal for creating or editing a CRM user.
 *
 * Create: all fields required except is_active (defaults to true).
 * Edit:   all fields optional — only populated/changed fields are sent.
 *         Password left blank = unchanged (not sent to backend).
 *
 * Backend rules respected here:
 *   - Email normalised to lowercase by backend; we trim it client-side.
 *   - Password must be ≥ 6 characters.
 *   - Cannot change last active admin's role to SALES.
 *   - Duplicate email → 409.
 */
import { type FormEvent, useEffect, useState } from 'react';
import type { CrmUser, UserCreateRequest, UserUpdateRequest } from '../../api/usersApi';
import { createUser, updateUser } from '../../api/usersApi';
import type { UserRole } from '../../api/types';
import { parseApiError } from '../../hooks/useApiError';

interface UserFormProps {
  mode: 'create' | 'edit';
  user?: CrmUser;
  onSuccess: (user: CrmUser) => void;
  onCancel: () => void;
}

interface FormState {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  is_active: boolean;
}

const empty = (): FormState => ({
  name: '', email: '', password: '', role: 'SALES', is_active: true,
});

const fromUser = (u: CrmUser): FormState => ({
  name: u.name, email: u.email, password: '', role: u.role, is_active: u.is_active,
});

export default function UserForm({ mode, user, onSuccess, onCancel }: UserFormProps) {
  const [form, setForm]       = useState<FormState>(mode === 'edit' && user ? fromUser(user) : empty());
  const [errors, setErrors]   = useState<Partial<Record<keyof FormState, string>>>({});
  const [apiError, setApiError] = useState('');
  const [saving, setSaving]   = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    setForm(mode === 'edit' && user ? fromUser(user) : empty());
    setErrors({});
    setApiError('');
  }, [mode, user]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((p) => ({ ...p, [key]: value }));
    setErrors((p) => ({ ...p, [key]: undefined }));
  }

  function validate(): boolean {
    const next: Partial<Record<keyof FormState, string>> = {};
    if (!form.name.trim()) next.name = 'Name is required.';
    if (!form.email.trim()) next.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      next.email = 'Enter a valid email address.';
    }
    if (mode === 'create') {
      if (!form.password) next.password = 'Password is required.';
      else if (form.password.length < 6) next.password = 'Password must be at least 6 characters.';
    } else if (form.password && form.password.length < 6) {
      next.password = 'Password must be at least 6 characters.';
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
      let result: CrmUser;
      if (mode === 'create') {
        const payload: UserCreateRequest = {
          name:      form.name.trim(),
          email:     form.email.trim().toLowerCase(),
          password:  form.password,
          role:      form.role,
          is_active: form.is_active,
        };
        result = await createUser(payload);
      } else {
        const payload: UserUpdateRequest = {
          name:      form.name.trim() || undefined,
          email:     form.email.trim().toLowerCase() || undefined,
          role:      form.role,
          is_active: form.is_active,
          ...(form.password ? { password: form.password } : {}),
        };
        result = await updateUser(user!.id, payload);
      }
      onSuccess(result);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  const title = mode === 'create' ? 'Create User' : 'Edit User';

  return (
    <div className="modal d-block" tabIndex={-1} role="dialog" aria-modal="true" aria-label={title}
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content border-0 shadow">
          <div className="modal-header">
            <h5 className="modal-title">
              <i className={`bi ${mode === 'create' ? 'bi-person-plus-fill' : 'bi-pencil-fill'} me-2 text-primary`} aria-hidden="true" />
              {title}
            </h5>
            <button type="button" className="btn-close" onClick={onCancel} disabled={saving} aria-label="Close" />
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className="modal-body">
              {apiError && (
                <div className="alert alert-danger small py-2 d-flex align-items-center gap-2 mb-3">
                  <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />
                  {apiError}
                </div>
              )}

              {/* Name */}
              <div className="mb-3">
                <label htmlFor="uf-name" className="form-label fw-medium">
                  Name <span className="text-danger">*</span>
                </label>
                <input id="uf-name" type="text"
                  className={`form-control ${errors.name ? 'is-invalid' : ''}`}
                  value={form.name} onChange={(e) => set('name', e.target.value)}
                  disabled={saving} autoComplete="off" />
                {errors.name && <div className="invalid-feedback">{errors.name}</div>}
              </div>

              {/* Email */}
              <div className="mb-3">
                <label htmlFor="uf-email" className="form-label fw-medium">
                  Email <span className="text-danger">*</span>
                </label>
                <input id="uf-email" type="email"
                  className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                  value={form.email} onChange={(e) => set('email', e.target.value)}
                  disabled={saving} autoComplete="off" />
                {errors.email && <div className="invalid-feedback">{errors.email}</div>}
              </div>

              {/* Password */}
              <div className="mb-3">
                <label htmlFor="uf-password" className="form-label fw-medium">
                  Password {mode === 'edit' && <span className="text-muted fw-normal small">(leave blank to keep current)</span>}
                  {mode === 'create' && <span className="text-danger"> *</span>}
                </label>
                <div className="input-group">
                  <input id="uf-password" type={showPassword ? 'text' : 'password'}
                    className={`form-control ${errors.password ? 'is-invalid' : ''}`}
                    value={form.password} onChange={(e) => set('password', e.target.value)}
                    disabled={saving} autoComplete="new-password"
                    placeholder={mode === 'edit' ? 'Leave blank to keep current' : 'Min 6 characters'} />
                  <button type="button" className="btn btn-outline-secondary"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1} disabled={saving}>
                    <i className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`} aria-hidden="true" />
                  </button>
                  {errors.password && <div className="invalid-feedback">{errors.password}</div>}
                </div>
              </div>

              {/* Role + Active row */}
              <div className="row g-3">
                <div className="col-6">
                  <label htmlFor="uf-role" className="form-label fw-medium">Role</label>
                  <select id="uf-role" className="form-select" value={form.role}
                    onChange={(e) => set('role', e.target.value as UserRole)} disabled={saving}>
                    <option value="SALES">Sales</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </div>
                <div className="col-6 d-flex align-items-end pb-1">
                  <div className="form-check form-switch">
                    <input id="uf-active" className="form-check-input" type="checkbox"
                      role="switch" checked={form.is_active}
                      onChange={(e) => set('is_active', e.target.checked)} disabled={saving} />
                    <label htmlFor="uf-active" className="form-check-label fw-medium">
                      {form.is_active ? 'Active' : 'Inactive'}
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving
                  ? <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />Saving…</>
                  : mode === 'create' ? 'Create User' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
