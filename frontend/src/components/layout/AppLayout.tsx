/**
 * AppLayout — the main authenticated shell.
 *
 * Structure:
 *   ┌──────────────────────────────────┐
 *   │  Sidebar   │  Topbar             │
 *   │  (fixed)   │─────────────────────│
 *   │            │  <Outlet />         │
 *   │            │  (page content)     │
 *   └──────────────────────────────────┘
 *
 * Responsive behaviour:
 *   Desktop (≥992px): sidebar always visible, no overlay.
 *   Mobile  (<992px): sidebar hidden; hamburger in Topbar opens it as an
 *                     overlay panel. Clicking a nav item or the backdrop
 *                     closes it.
 */
import { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const openSidebar  = useCallback(() => setSidebarOpen(true),  []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  return (
    <div className="crm-shell">
      {/* ── Mobile backdrop ─────────────────────────────────────────────── */}
      {sidebarOpen && (
        <div
          className="crm-backdrop d-lg-none"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      {/* On desktop: always visible via CSS.
          On mobile:  crm-sidebar--open class slides it in. */}
      <div className={`crm-sidebar-wrapper${sidebarOpen ? ' crm-sidebar--open' : ''}`}>
        <Sidebar onNavClick={closeSidebar} />
      </div>

      {/* ── Main column ─────────────────────────────────────────────────── */}
      <div className="crm-main">
        <Topbar onMenuToggle={openSidebar} />

        <main className="crm-content" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
