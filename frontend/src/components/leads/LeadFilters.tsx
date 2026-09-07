/**
 * LeadFilters — search box + stage dropdown + clear button.
 *
 * Parent is responsible for debouncing the search and resetting page to 1
 * when filters change.
 */
import type { LeadStage } from '../../api/types';
import { STAGE_OPTIONS } from './leadConstants';

interface LeadFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  stage: LeadStage | '';
  onStageChange: (v: LeadStage | '') => void;
  onClear: () => void;
  hasActiveFilters: boolean;
}

export default function LeadFilters({
  search,
  onSearchChange,
  stage,
  onStageChange,
  onClear,
  hasActiveFilters,
}: LeadFiltersProps) {
  return (
    <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
      {/* Search */}
      <div className="input-group input-group-sm" style={{ maxWidth: 280 }}>
        <span className="input-group-text border-end-0 bg-white">
          <i className="bi bi-search text-muted" aria-hidden="true" />
        </span>
        <input
          type="search"
          className="form-control border-start-0"
          placeholder="Search name, email, phone…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Search leads"
        />
      </div>

      {/* Stage filter */}
      <select
        className="form-select form-select-sm"
        style={{ maxWidth: 160 }}
        value={stage}
        onChange={(e) => onStageChange(e.target.value as LeadStage | '')}
        aria-label="Filter by stage"
      >
        <option value="">All Stages</option>
        {STAGE_OPTIONS.map(({ value, label }) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>

      {/* Clear */}
      {hasActiveFilters && (
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
          onClick={onClear}
        >
          <i className="bi bi-x" aria-hidden="true" />
          Clear
        </button>
      )}
    </div>
  );
}
