/**
 * Properties API module.
 *
 * Wraps all project/building/unit backend endpoints.
 */
import apiClient from './axios';

// ── Enum types ────────────────────────────────────────────────────────────────

export type UnitType   = '1BHK' | '2BHK' | '3BHK' | '4BHK' | 'VILLA' | 'PLOT';
export type UnitStatus = 'AVAILABLE' | 'BOOKED';

// ── Project types ─────────────────────────────────────────────────────────────

export interface Project {
  id: number;
  name: string;
  location: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  size: number;
}

export interface ProjectCreateRequest {
  name: string;
  location?: string;
  description?: string;
}

export interface ProjectUpdateRequest {
  name?: string;
  location?: string | null;
  description?: string | null;
}

// ── Building types ────────────────────────────────────────────────────────────

export interface Building {
  id: number;
  project_id: number;
  name: string;
  total_floors: number | null;
  created_at: string;
  updated_at: string;
}

export interface BuildingListResponse {
  items: Building[];
  total: number;
}

export interface BuildingCreateRequest {
  name: string;
  total_floors?: number;
}

export interface BuildingUpdateRequest {
  name?: string;
  total_floors?: number;
}

// ── Unit types ────────────────────────────────────────────────────────────────

export interface Unit {
  id: number;
  building_id: number;
  unit_number: string;
  type: UnitType;
  floor: number | null;
  price: number | null;
  status: UnitStatus;
  created_at: string;
  updated_at: string;
}

export interface UnitListResponse {
  items: Unit[];
  total: number;
  page: number;
  size: number;
}

export interface UnitCreateRequest {
  unit_number: string;
  type: UnitType;
  floor?: number;
  price?: number;
  status?: UnitStatus;
}

export interface UnitUpdateRequest {
  unit_number?: string;
  type?: UnitType;
  floor?: number | null;
  price?: number | null;
  status?: UnitStatus;
}

export interface UnitListParams {
  page?: number;
  size?: number;
  status?: UnitStatus | '';
  type?: UnitType | '';
}

// ── Project API ───────────────────────────────────────────────────────────────

export async function listProjects(
  page = 1, size = 10, search?: string
): Promise<ProjectListResponse> {
  const { data } = await apiClient.get<ProjectListResponse>('/projects', {
    params: { page, size, ...(search ? { search } : {}) },
  });
  return data;
}

export async function getProject(id: number): Promise<Project> {
  const { data } = await apiClient.get<Project>(`/projects/${id}`);
  return data;
}

export async function createProject(payload: ProjectCreateRequest): Promise<Project> {
  const { data } = await apiClient.post<Project>('/projects', payload);
  return data;
}

export async function updateProject(id: number, payload: ProjectUpdateRequest): Promise<Project> {
  const { data } = await apiClient.put<Project>(`/projects/${id}`, payload);
  return data;
}

export async function deleteProject(id: number): Promise<void> {
  await apiClient.delete(`/projects/${id}`);
}

// ── Building API ──────────────────────────────────────────────────────────────

export async function listBuildings(projectId: number): Promise<BuildingListResponse> {
  const { data } = await apiClient.get<BuildingListResponse>(
    `/projects/${projectId}/buildings`
  );
  return data;
}

export async function createBuilding(
  projectId: number, payload: BuildingCreateRequest
): Promise<Building> {
  const { data } = await apiClient.post<Building>(
    `/projects/${projectId}/buildings`, payload
  );
  return data;
}

export async function updateBuilding(
  id: number, payload: BuildingUpdateRequest
): Promise<Building> {
  const { data } = await apiClient.put<Building>(`/buildings/${id}`, payload);
  return data;
}

export async function deleteBuilding(id: number): Promise<void> {
  await apiClient.delete(`/buildings/${id}`);
}

// ── Unit API ──────────────────────────────────────────────────────────────────

export async function listUnits(
  buildingId: number, params: UnitListParams = {}
): Promise<UnitListResponse> {
  const { data } = await apiClient.get<UnitListResponse>(
    `/buildings/${buildingId}/units`,
    {
      params: {
        page:   params.page  ?? 1,
        size:   params.size  ?? 20,
        ...(params.status ? { status: params.status } : {}),
        ...(params.type   ? { type:   params.type   } : {}),
      },
    }
  );
  return data;
}

export async function createUnit(
  buildingId: number, payload: UnitCreateRequest
): Promise<Unit> {
  const { data } = await apiClient.post<Unit>(
    `/buildings/${buildingId}/units`, payload
  );
  return data;
}

export async function updateUnit(id: number, payload: UnitUpdateRequest): Promise<Unit> {
  const { data } = await apiClient.put<Unit>(`/units/${id}`, payload);
  return data;
}

export async function deleteUnit(id: number): Promise<void> {
  await apiClient.delete(`/units/${id}`);
}
