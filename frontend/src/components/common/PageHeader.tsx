/**
 * PageHeader — consistent page title block reused on every page.
 */
import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: string;
  children?: ReactNode;
}

export default function PageHeader({ title, subtitle, icon, children }: PageHeaderProps) {
  return (
    <div className="d-flex align-items-start justify-content-between mb-4 flex-wrap gap-3">
      <div className="d-flex align-items-center gap-3">
        {icon && (
          <div
            className="d-flex align-items-center justify-content-center rounded-3 bg-primary bg-opacity-10 flex-shrink-0"
            style={{ width: 44, height: 44 }}
          >
            <i className={`bi ${icon} fs-5 text-primary`} aria-hidden="true" />
          </div>
        )}
        <div>
          <h1 className="h4 fw-semibold mb-0">{title}</h1>
          {subtitle && <p className="text-muted small mb-0 mt-1">{subtitle}</p>}
        </div>
      </div>
      {children && <div className="d-flex gap-2">{children}</div>}
    </div>
  );
}
