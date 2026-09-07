/**
 * RoleProtectedRoute — renders children only when the user has a required role.
 *
 * If the role requirement is not met, shows a clean 403 page.
 * This is a UI-level guard. The backend is the actual security boundary.
 *
 * Usage:
 *   <Route element={<RoleProtectedRoute allowedRoles={['ADMIN']} />}>
 *     <Route path="/users" element={<UsersPage />} />
 *   </Route>
 */
import { Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { UserRole } from '../api/authApi';

interface RoleProtectedRouteProps {
  allowedRoles: UserRole[];
}

export default function RoleProtectedRoute({ allowedRoles }: RoleProtectedRouteProps) {
  const { user } = useAuth();

  if (!user || !allowedRoles.includes(user.role)) {
    return (
      <div className="d-flex flex-column align-items-center justify-content-center text-center py-5">
        <div
          className="d-inline-flex align-items-center justify-content-center rounded-circle bg-danger bg-opacity-10 mb-4"
          style={{ width: 72, height: 72 }}
        >
          <i className="bi bi-shield-exclamation fs-2 text-danger" aria-hidden="true" />
        </div>
        <h2 className="h3 fw-bold mb-2">403 — Access Denied</h2>
        <p className="text-muted mb-0" style={{ maxWidth: 360 }}>
          You do not have permission to view this page.
          Please contact your administrator if you believe this is an error.
        </p>
      </div>
    );
  }

  return <Outlet />;
}
