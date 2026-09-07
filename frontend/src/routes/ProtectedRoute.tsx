/**
 * ProtectedRoute — redirects unauthenticated users to /login.
 *
 * Renders nothing (spinner) while the initial session restore is in progress
 * so protected pages never flash briefly before the redirect.
 */
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  // Session restore in progress — show a full-screen spinner rather than
  // flashing the login page or the protected content.
  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center vh-100">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading…</span>
        </div>
      </div>
    );
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
