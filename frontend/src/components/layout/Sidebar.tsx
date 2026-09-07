/**
 * Sidebar — primary navigation panel.
 *
 * - Shows role-appropriate nav items (Admin sees Users, Sales does not).
 * - Uses React Router NavLink so the active item is highlighted automatically.
 * - Accepts `onNavClick` so mobile callers can close the sidebar after navigation.
 */
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface NavItem {
  to: string;
  label: string;
  icon: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/',           label: 'Dashboard',  icon: 'bi-grid-1x2-fill' },
  { to: '/leads',      label: 'Leads',      icon: 'bi-people-fill' },
  { to: '/properties', label: 'Properties', icon: 'bi-buildings-fill' },
  { to: '/bookings',   label: 'Bookings',   icon: 'bi-calendar-check-fill' },
  { to: '/users',      label: 'Users',      icon: 'bi-person-lines-fill', adminOnly: true },
];

interface SidebarProps {
  onNavClick?: () => void;
}

export default function Sidebar({ onNavClick }: SidebarProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const visibleItems = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);

  return (
    <aside className="crm-sidebar d-flex flex-column">
      {/* Brand */}
      <div className="crm-sidebar__brand">
        <i className="bi bi-buildings me-2 fs-5" aria-hidden="true" />
        <span className="fw-bold">Real Estate CRM</span>
      </div>

      {/* Navigation */}
      <nav aria-label="Primary navigation" className="flex-grow-1 overflow-auto">
        <ul className="nav flex-column px-2 pt-2" role="list">
          {visibleItems.map((item) => (
            <li key={item.to} className="nav-item" role="listitem">
              <NavLink
                to={item.to}
                end={item.to === '/'}   // exact match for root only
                onClick={onNavClick}
                className={({ isActive }) =>
                  `crm-nav-link nav-link d-flex align-items-center gap-2 rounded-2 px-3 py-2 mb-1${
                    isActive ? ' crm-nav-link--active' : ''
                  }`
                }
              >
                <i className={`bi ${item.icon} flex-shrink-0`} aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer — user chip */}
      <div className="crm-sidebar__footer">
        <div className="d-flex align-items-center gap-2 overflow-hidden">
          <div
            className="d-flex align-items-center justify-content-center rounded-circle bg-primary text-white flex-shrink-0"
            style={{ width: 32, height: 32, fontSize: 13 }}
            aria-hidden="true"
          >
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div className="overflow-hidden">
            <div className="fw-medium text-truncate small lh-sm">{user?.name}</div>
            <div className="text-muted" style={{ fontSize: 11 }}>{user?.role}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
