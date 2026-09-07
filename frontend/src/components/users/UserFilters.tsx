/**
 * UserFilters — search + role + active-status filters for the user list.
 *
 * All filters hit backend query parameters; no client-side filtering.
 */
import type { UserRole } from '../../api/types';

interface UserFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  role: UserRole | '';
  onRoleChange: (v: UserRole | '') => void;
  isActive: boolean | null;
  onActiveChange: (v: boolean | null) => void;
  onClear: () => void;
  hasActiveFilters: boolean;
}

export default function UserFilters({
  search, onSearchChange,
  role, onRoleChange,
  isActive, onActiveChange,
  onClear, hasActiveFilters,
}: UserFiltersProps) {
  return (
    <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
      {/* Search */}
      <div className="input-group input-group-sm" style={{ maxWidth: 260 }}>
        <span className="input-group-text border-end-0 bg-white">
          <i className="bi bi-search text-muted" aria-hidden="true" />
        </span>
        <input
          type="search"
          className="form-control border-start-0"
          placeholder="Search name or email…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Search users"
        />
      </div>

      {/* Role filter */}
      <select
        className="form-select form-select-sm"
        style={{ maxWidth: 140 }}
        value={role}
        onChange={(e) => onRoleChange(e.target.value as UserRole | '')}
        aria-label="Filter by role"
      >
        <option value="">All Roles</option>
        <option value="ADMIN">Admin</option>
        <option value="SALES">Sales</option>
      </select>

      {/* Active status filter */}
      <select
        className="form-select form-select-sm"
        style={{ maxWidth: 150 }}
        value={isActive == null ? '' : String(isActive)}
        onChange={(e) => {
          const v = e.target.value;
          onActiveChange(v === '' ? null : v === 'true');
        }}
        aria-label="Filter by status"
      >
        <option value="">All Status</option>
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>

      {/* Clear */}
      {hasActiveFilters && (
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
          onClick={onClear}
        >
          <i className="bi bi-x" aria-hidden="true" />Clear
        </button>
      )}
    </div>
  );
}
