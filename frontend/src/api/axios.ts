/**
 * Shared Axios instance.
 *
 * - Base URL comes from VITE_API_BASE_URL (falls back to /api so the Vite
 *   proxy works in development without the env var set).
 * - Request interceptor: attaches `Authorization: Bearer <token>` when a
 *   stored token exists.
 * - Response interceptor: on 401, clears the token so the AuthContext can
 *   detect the stale session on next render.
 */
import axios from 'axios';
import { getToken, removeToken } from '../utils/token';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor — attach JWT ─────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — handle 401 ────────────────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Remove stale token so AuthContext re-checks on next navigation.
      removeToken();
    }
    return Promise.reject(error);
  },
);

export default apiClient;
