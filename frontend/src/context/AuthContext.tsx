/**
 * AuthContext — application-wide authentication state.
 *
 * Exposes:
 *   user          — the authenticated CurrentUser or null
 *   token         — the raw JWT string or null
 *   isAuthenticated — derived boolean
 *   isLoading     — true while the initial session restore is in progress
 *   login(email, password) — authenticate and store session
 *   logout()      — clear session and redirect to /login
 *
 * Session restore on startup:
 *   1. Read token from localStorage.
 *   2. If present, call GET /api/auth/me.
 *   3. If /me succeeds → restore user; if it fails (expired/invalid) → clear.
 *   4. Set isLoading = false so the router can decide where to send the user.
 *
 * Components must not render protected content until isLoading is false.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { getMe, login as apiLogin, type CurrentUser } from '../api/authApi';
import { getToken, removeToken, setToken } from '../utils/token';

// ── Context shape ─────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: CurrentUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [token, setTokenState] = useState<string | null>(getToken());
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Restore session on mount
  useEffect(() => {
    const storedToken = getToken();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    getMe()
      .then((currentUser) => {
        setUser(currentUser);
        setTokenState(storedToken);
      })
      .catch(() => {
        // Token is invalid or expired — clear it
        removeToken();
        setTokenState(null);
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiLogin({ email, password });
    setToken(access_token);
    setTokenState(access_token);
    const currentUser = await getMe();
    setUser(currentUser);
    navigate('/', { replace: true });
  }, [navigate]);

  const logout = useCallback(() => {
    removeToken();
    setTokenState(null);
    setUser(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  const value: AuthContextValue = {
    user,
    token,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
