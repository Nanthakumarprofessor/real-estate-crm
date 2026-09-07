/**
 * Token storage helpers.
 *
 * Uses localStorage for persistence across page refreshes.
 * NOTE: localStorage is acceptable for this CRM assignment (internal tool,
 * short-lived JWT). For higher-security public apps consider httpOnly cookies.
 *
 * Passwords are NEVER stored here.
 */

const TOKEN_KEY = 'crm_access_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}
