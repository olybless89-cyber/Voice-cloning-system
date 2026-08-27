import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api as api } from '../api/client';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  initializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>(null as unknown as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('vc_token');
    const cached = localStorage.getItem('vc_user');
    setUser(cached ? (JSON.parse(cached) as User) : null);
    if (token) {
      api
        .me()
        .then((fresh) => {
          setUser(fresh);
          localStorage.setItem('vc_user', JSON.stringify(fresh));
        })
        .catch(() => {
          localStorage.removeItem('vc_token');
          localStorage.removeItem('vc_user');
          setUser(null);
        })
        .finally(() => setInitializing(false));
    } else {
      setInitializing(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login({ email, password });
    localStorage.setItem('vc_token', res.access_token);
    localStorage.setItem('vc_user', JSON.stringify(res.user));
    setUser(res.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const res = await api.register({ email, password, full_name: fullName });
      localStorage.setItem('vc_token', res.access_token);
      localStorage.setItem('vc_user', JSON.stringify(res.user));
      setUser(res.user);
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem('vc_token');
    localStorage.removeItem('vc_user');
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, initializing, login, register, logout }),
    [user, initializing, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}