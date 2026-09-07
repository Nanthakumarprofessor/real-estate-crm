/**
 * Authentication API module.
 *
 * Wraps POST /api/auth/login and GET /api/auth/me.
 * All other API modules should follow this pattern.
 */
import apiClient from './axios';

// ── Types ─────────────────────────────────────────────────────────────────────

export type UserRole = 'ADMIN' | 'SALES';

export interface CurrentUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

/**
 * POST /api/auth/login
 * Returns the JWT access token on success.
 */
export async function login(credentials: LoginCredentials): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', credentials);
  return data;
}

/**
 * GET /api/auth/me
 * Returns the currently authenticated user.
 * Requires a valid Bearer token to already be set in the Axios instance.
 */
export async function getMe(): Promise<CurrentUser> {
  const { data } = await apiClient.get<CurrentUser>('/auth/me');
  return data;
}
