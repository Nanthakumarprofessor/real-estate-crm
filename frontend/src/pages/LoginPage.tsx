/**
 * LoginPage — professional CRM login screen.
 *
 * Features:
 *   - Email + password fields with accessible labels
 *   - Client-side validation (required, email format)
 *   - Loading / disabled state while the request is in flight
 *   - Friendly error messages from the API (no raw stack traces)
 *   - Redirects authenticated users away from /login
 *   - Responsive — works on desktop and mobile
 */
import { type FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { parseApiError } from '../hooks/useApiError';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [apiError, setApiError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Redirect already-authenticated users
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  // ── Client-side validation ──────────────────────────────────────────────────
  function validate(): boolean {
    const next: { email?: string; password?: string } = {};
    if (!email.trim()) {
      next.email = 'Email is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      next.email = 'Please enter a valid email address.';
    }
    if (!password) {
      next.password = 'Password is required.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  // ── Submit ──────────────────────────────────────────────────────────────────
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setApiError('');
    if (!validate()) return;

    setSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
      // AuthContext.login navigates to / on success
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  // Don't render the form while session restore is in progress
  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center vh-100">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center bg-light py-5">
      <div className="container">
        <div className="row justify-content-center">
          <div className="col-12 col-sm-10 col-md-7 col-lg-5 col-xl-4">

            {/* Card */}
            <div className="card shadow-sm border-0 rounded-3">
              <div className="card-body p-4 p-md-5">

                {/* Logo / heading */}
                <div className="text-center mb-4">
                  <div
                    className="d-inline-flex align-items-center justify-content-center rounded-circle bg-primary bg-opacity-10 mb-3"
                    style={{ width: 56, height: 56 }}
                  >
                    <i className="bi bi-buildings fs-3 text-primary" aria-hidden="true" />
                  </div>
                  <h1 className="h4 fw-semibold mb-1">Real Estate CRM</h1>
                  <p className="text-muted small mb-0">Sign in to your account</p>
                </div>

                {/* API error alert */}
                {apiError && (
                  <div className="alert alert-danger d-flex align-items-center gap-2 py-2" role="alert">
                    <i className="bi bi-exclamation-circle-fill flex-shrink-0" aria-hidden="true" />
                    <span className="small">{apiError}</span>
                  </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} noValidate>

                  {/* Email */}
                  <div className="mb-3">
                    <label htmlFor="email" className="form-label fw-medium">
                      Email address
                    </label>
                    <input
                      id="email"
                      type="email"
                      className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (errors.email) setErrors((p) => ({ ...p, email: undefined }));
                      }}
                      autoComplete="email"
                      autoFocus
                      disabled={submitting}
                    />
                    {errors.email && (
                      <div className="invalid-feedback">{errors.email}</div>
                    )}
                  </div>

                  {/* Password */}
                  <div className="mb-4">
                    <label htmlFor="password" className="form-label fw-medium">
                      Password
                    </label>
                    <div className="input-group">
                      <input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        className={`form-control ${errors.password ? 'is-invalid' : ''}`}
                        placeholder="Enter your password"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          if (errors.password) setErrors((p) => ({ ...p, password: undefined }));
                        }}
                        autoComplete="current-password"
                        disabled={submitting}
                      />
                      <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        tabIndex={-1}
                        disabled={submitting}
                      >
                        <i
                          className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`}
                          aria-hidden="true"
                        />
                      </button>
                      {errors.password && (
                        <div className="invalid-feedback">{errors.password}</div>
                      )}
                    </div>
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    className="btn btn-primary w-100"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <span
                          className="spinner-border spinner-border-sm me-2"
                          role="status"
                          aria-hidden="true"
                        />
                        Signing in…
                      </>
                    ) : (
                      'Sign in'
                    )}
                  </button>
                </form>

              </div>
            </div>

            {/* Footer note */}
            <p className="text-center text-muted small mt-3">
              Real Estate CRM &copy; {new Date().getFullYear()}
            </p>

          </div>
        </div>
      </div>
    </div>
  );
}
