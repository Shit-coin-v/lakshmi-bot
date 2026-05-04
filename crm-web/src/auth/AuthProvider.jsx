import { createContext, useContext } from 'react';
import { useMe } from '../hooks/useAuth.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const { data: user, isLoading, isFetching } = useMe();
  const value = {
    user: user ?? null,
    isAuthenticated: !!user,
    isLoading: isLoading,
    isFetching,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
