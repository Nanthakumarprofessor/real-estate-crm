/**
 * Users API module.
 *
 * Wraps all user management endpoints (Admin only):
 *   GET   /api/users
 *   POST  /api/users
 *   GET   /api/users/{id}
 *   PUT   /api/users/{id}
 *   PATCH /api/users/{id}/deactivate
 *
 * Notes:
 *   - There is no separate reactivate endpoint.
 *   - Reactivation is done via PUT /api/users/{id} with { is_active: true }.
 *   - PATCH /deactivate only sets is_active = false.
 *   - Last-admin protection: deactivating/role-changing the last active admin
 *     returns 400 with error_code "LAST_ADMIN_PROTECTED".
 */
import apiClient from './axios';
import type { UserRole } from './types';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CrmUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  items: CrmUser[];
  total: number;
  page: number;
  size: number;
}

export interface UserListParams {
  page?: number;
  size?: number;
  search?: string;
  role?: UserRole | '';
  is_active?: boolean | null;
}

export interface UserCreateRequest {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  is_active?: boolean;
}

export interface UserUpdateRequest {
  name?: string;
  email?: string;
  password?: string;
  role?: UserRole;
  is_active?: boolean;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listUsers(params: UserListParams = {}): Promise<UserListResponse> {
  const { data } = await apiClient.get<UserListResponse>('/users', {
    params: {
      page: params.page ?? 1,
      size: params.size ?? 10,
      ...(params.search              ? { search:    params.search }    : {}),
      ...(params.role                ? { role:      params.role }      : {}),
      ...(params.is_active != null   ? { is_active: params.is_active } : {}),
    },
  });
  return data;
}

export async function getUser(id: number): Promise<CrmUser> {
  const { data } = await apiClient.get<CrmUser>(`/users/${id}`);
  return data;
}

export async function createUser(payload: UserCreateRequest): Promise<CrmUser> {
  const { data } = await apiClient.post<CrmUser>('/users', payload);
  return data;
}

export async function updateUser(id: number, payload: UserUpdateRequest): Promise<CrmUser> {
  const { data } = await apiClient.put<CrmUser>(`/users/${id}`, payload);
  return data;
}

export async function deactivateUser(id: number): Promise<CrmUser> {
  const { data } = await apiClient.patch<CrmUser>(`/users/${id}/deactivate`);
  return data;
}
