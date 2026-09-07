/**
 * ProjectDetails — offcanvas drawer showing project info + buildings + units.
 *
 * Lazy-loads buildings when opened.
 * Lazy-loads units only when a building is expanded.
 */
import { useCallback, useEffect, useState } from 'react';
import type { Building, Project } from '../../api/propertiesApi';
import { deleteBuilding, listBuildings } from '../../api/propertiesApi';
import BuildingForm from './BuildingForm';
import UnitTable from './UnitTable';
import ConfirmModal from '../common/ConfirmModal';
import { parseApiError } from '../../hooks/useApiError';

interface ProjectDetailsProps {
  project: Project;
  isAdmin: boolean;
  onClose: () => void;
  onEdit: (project: Project) => void;
  onToast: (msg: string, type?: 'success' | 'danger') => void;
}

export default function ProjectDetails({ project, isAdmin, onClose, onEdit, onToast }: ProjectDetailsProps) {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [loadingBuildings, setLoadingBuildings] = useState(true);
  const [buildingError, setBuildingError]       = useState('');

  const [expandedBuildingId, setExpandedBuildingId] = useState<number | null>(null);

  type BuildingModal = 'none' | 'create' | 'edit';
  const [buildingModal, setBuildingModal] = useState<BuildingModal>('none');
  const [editBuilding, setEditBuilding]   = useState<Building | undefined>();
  const [deleteTarget, setDeleteTarget]   = useState<Building | null>(null);
  const [deleting, setDeleting]           = useState(false);
  const [deleteError, setDeleteError]     = useState('');

  const fetchBuildings = useCallback(async () => {
    setLoadingBuildings(true);
    setBuildingError('');
    try {
      const res = await listBuildings(project.id);
      setBuildings(res.items);
    } catch (err) {
      setBuildingError(parseApiError(err));
    } finally {
      setLoadingBuildings(false);
    }
  }, [project.id]);

  useEffect(() => { fetchBuildings(); }, [fetchBuildings]);

  async function confirmDeleteBuilding() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteBuilding(deleteTarget.id);
      onToast(`Building "${deleteTarget.name}" deleted.`);
      setDeleteTarget(null);
      if (expandedBuildingId === deleteTarget.id) setExpandedBuildingId(null);
      fetchBuildings();
    } catch (err) {
      setDeleteError(parseApiError(err));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="offcanvas-backdrop fade show" onClick={onClose} aria-hidden="true" />
      <div className="offcanvas offcanvas-end show" tabIndex={-1} role="dialog" aria-label="Project details"
        style={{ width: 'min(600px, 100vw)' }}>

        {/* Header */}
        <div className="offcanvas-header border-bottom">
          <div>
            <h5 className="offcanvas-title mb-0">{project.name}</h5>
            {project.location && <div className="text-muted small"><i className="bi bi-geo-alt me-1" aria-hidden="true" />{project.location}</div>}
          </div>
          <div className="d-flex gap-2">
            {isAdmin && (
              <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => onEdit(project)}>
                <i className="bi bi-pencil me-1" aria-hidden="true" />Edit
              </button>
            )}
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close" />
          </div>
        </div>

        <div className="offcanvas-body overflow-auto">

          {/* Project info */}
          {project.description && (
            <section className="mb-4">
              <p className="text-muted small mb-0">{project.description}</p>
            </section>
          )}

          <hr />

          {/* Buildings */}
          <section>
            <div className="d-flex align-items-center justify-content-between mb-3">
              <h6 className="fw-semibold mb-0 d-flex align-items-center gap-2">
                <i className="bi bi-buildings-fill text-primary" aria-hidden="true" />
                Buildings
                <span className="badge bg-secondary rounded-pill ms-1">{buildings.length}</span>
              </h6>
              {isAdmin && (
                <button type="button" className="btn btn-sm btn-outline-primary"
                  onClick={() => { setEditBuilding(undefined); setBuildingModal('create'); }}>
                  <i className="bi bi-plus" aria-hidden="true" />Add
                </button>
              )}
            </div>

            {buildingModal !== 'none' && (
              <BuildingForm
                mode={buildingModal}
                projectId={project.id}
                building={editBuilding}
                onSuccess={(b) => {
                  setBuildingModal('none');
                  onToast(buildingModal === 'create' ? `Building "${b.name}" created.` : `Building "${b.name}" updated.`);
                  fetchBuildings();
                }}
                onCancel={() => setBuildingModal('none')} />
            )}

            {loadingBuildings && (
              <div className="py-3 text-center">
                <div className="spinner-border spinner-border-sm text-primary" role="status"><span className="visually-hidden">Loading…</span></div>
              </div>
            )}

            {!loadingBuildings && buildingError && (
              <div className="text-center py-3">
                <p className="text-danger small mb-1">{buildingError}</p>
                <button className="btn btn-sm btn-outline-primary" onClick={fetchBuildings}>Retry</button>
              </div>
            )}

            {!loadingBuildings && !buildingError && buildings.length === 0 && (
              <p className="text-muted small text-center py-2">No buildings yet.</p>
            )}

            {!loadingBuildings && !buildingError && buildings.map((b) => {
              const isExpanded = expandedBuildingId === b.id;
              return (
                <div key={b.id} className="mb-2 border rounded-3 overflow-hidden">
                  {/* Building header row */}
                  <div className="d-flex align-items-center justify-content-between p-3 bg-light"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setExpandedBuildingId(isExpanded ? null : b.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && setExpandedBuildingId(isExpanded ? null : b.id)}
                    aria-expanded={isExpanded}
                    aria-label={`${b.name}, click to ${isExpanded ? 'collapse' : 'expand'}`}
                  >
                    <div>
                      <span className="fw-medium">{b.name}</span>
                      {b.total_floors && (
                        <span className="text-muted small ms-2">{b.total_floors} floors</span>
                      )}
                    </div>
                    <div className="d-flex align-items-center gap-2" onClick={(e) => e.stopPropagation()} role="presentation">
                      {isAdmin && (
                        <>
                          <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2"
                            onClick={() => { setEditBuilding(b); setBuildingModal('edit'); }} aria-label={`Edit ${b.name}`}>
                            <i className="bi bi-pencil" aria-hidden="true" />
                          </button>
                          <button type="button" className="btn btn-sm btn-outline-danger py-0 px-2"
                            onClick={() => { setDeleteTarget(b); setDeleteError(''); }} aria-label={`Delete ${b.name}`}>
                            <i className="bi bi-trash3" aria-hidden="true" />
                          </button>
                        </>
                      )}
                      <i className={`bi ${isExpanded ? 'bi-chevron-up' : 'bi-chevron-down'} text-muted small`} aria-hidden="true" />
                    </div>
                  </div>

                  {/* Units — shown only when expanded */}
                  {isExpanded && (
                    <div className="p-3 border-top">
                      <UnitTable buildingId={b.id} isAdmin={isAdmin} onToast={onToast} />
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        </div>
      </div>

      {/* Delete building confirm */}
      {deleteTarget && (
        <ConfirmModal
          title="Delete Building?"
          message={`Are you sure you want to delete "${deleteTarget.name}"?`}
          subMessage="This cannot be done if the building has units."
          confirmLabel="Delete Building"
          error={deleteError}
          busy={deleting}
          onConfirm={confirmDeleteBuilding}
          onCancel={() => setDeleteTarget(null)} />
      )}
    </>
  );
}
