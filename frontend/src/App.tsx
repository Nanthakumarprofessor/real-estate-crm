/**
 * App — root route tree.
 *
 * Route structure:
 *   /login             → LoginPage          (public)
 *   /                  → ProtectedRoute
 *                           └── AppLayout   (authenticated shell)
 *                                 ├── /              → DashboardPage
 *                                 ├── /leads         → LeadsPage
 *                                 ├── /properties    → PropertiesPage
 *                                 ├── /bookings      → BookingsPage
 *                                 └── RoleProtectedRoute [ADMIN]
 *                                       └── /users   → UsersPage
 *   *                  → redirect to /
 */
import { Route, Routes, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import LeadsPage from './pages/LeadsPage';
import PropertiesPage from './pages/PropertiesPage';
import BookingsPage from './pages/BookingsPage';
import UsersPage from './pages/UsersPage';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './routes/ProtectedRoute';
import RoleProtectedRoute from './routes/RoleProtectedRoute';

export default function App() {
  return (
    <Routes>
      {/* ── Public ────────────────────────────────────────────────────── */}
      <Route path="/login" element={<LoginPage />} />

      {/* ── Protected (requires authentication) ───────────────────────── */}
      <Route element={<ProtectedRoute />}>
        {/* AppLayout renders Sidebar + Topbar + <Outlet /> */}
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="leads"      element={<LeadsPage />} />
          <Route path="properties" element={<PropertiesPage />} />
          <Route path="bookings"   element={<BookingsPage />} />

          {/* Admin-only route — Sales sees 403 */}
          <Route element={<RoleProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>

      {/* ── Fallback ──────────────────────────────────────────────────── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
