/**
 * Topbar — top navigation bar.
 *
 * Left:  hamburger button (mobile) + current page title
 * Right: user name + role badge + logout dropdown
 */
import { useAuth } from '../../context/AuthContext';

const ROLE_BADGE_CLASS: Record<string, string> = {
  ADMIN:  'bg-danger',
  SALES:  'bg-success',
};

interface TopbarProps {
  /** Called when the mobile menu button is clicked. */
  onMenuToggle: () => void;
}

export default function Topbar({ onMenuToggle }: TopbarProps) {
  const { user, logout } = useAuth();
  const badgeClass = ROLE_BADGE_CLASS[user?.role ?? ''] ?? 'bg-secondary';

  return (
    <header className="crm-topbar d-flex align-items-center justify-content-between px-3 px-md-4">
      {/* Left — mobile hamburger */}
      <div className="d-flex align-items-center gap-2">
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-lg-none"
          onClick={onMenuToggle}
          aria-label="Toggle navigation menu"
        >
          <i className="bi bi-list fs-5" aria-hidden="true" />
        </button>
        {/* Brand visible on mobile (sidebar hidden) */}
        <span className="fw-semibold text-primary d-lg-none">Real Estate CRM</span>
      </div>

      {/* Right — user + logout */}
      <div className="d-flex align-items-center gap-2 gap-md-3">
        {/* User info */}
        <div className="d-flex align-items-center gap-2">
          <div className="text-end d-none d-sm-block">
            <div className="fw-semibold small lh-sm">{user?.name}</div>
            <div>
              <span className={`badge ${badgeClass}`} style={{ fontSize: 10 }}>
                {user?.role}
              </span>
            </div>
          </div>
          {/* Avatar circle */}
          <div
            className="d-flex align-items-center justify-content-center rounded-circle bg-primary text-white flex-shrink-0"
            style={{ width: 36, height: 36, fontSize: 14 }}
            aria-hidden="true"
          >
            {user?.name?.charAt(0).toUpperCase()}
          </div>
        </div>

        {/* Logout button */}
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
          onClick={logout}
          aria-label="Sign out"
        >
          <i className="bi bi-box-arrow-right" aria-hidden="true" />
          <span className="d-none d-md-inline">Sign out</span>
        </button>
      </div>
    </header>
  );
}
