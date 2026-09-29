import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, apiClient, type AuthResponse, type User } from "../lib/api/client";
import { clearPrivateLearningData } from "../lib/pwa-db";
import { AuthContext, type AuthContextValue } from "./auth-context-value";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshAt, setRefreshAt] = useState<number | null>(null);
  const initialized = useRef(false);

  const acceptAuth = useCallback((auth: AuthResponse) => {
    setUser(auth.user);
    setRefreshAt(Date.now() + Math.max(auth.expires_in - 60, 1) * 1000);
  }, []);

  const clearAuth = useCallback(() => {
    apiClient.setAccessToken(null);
    setUser(null);
    setRefreshAt(null);
  }, []);

  const handleRefreshFailure = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError) {
        clearAuth();
        return;
      }
      setRefreshAt((current) => (current === null ? null : Date.now() + 60_000));
    },
    [clearAuth],
  );

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    void apiClient
      .refresh()
      .then(acceptAuth)
      .catch(handleRefreshFailure)
      .finally(() => setIsLoading(false));
  }, [acceptAuth, handleRefreshFailure]);

  useEffect(() => {
    if (refreshAt === null) return;
    const timeout = window.setTimeout(() => {
      void apiClient.refresh().then(acceptAuth).catch(handleRefreshFailure);
    }, Math.max(refreshAt - Date.now(), 0));
    return () => window.clearTimeout(timeout);
  }, [acceptAuth, handleRefreshFailure, refreshAt]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      login: async (email, password) => {
        acceptAuth(await apiClient.login(email, password));
      },
      logout: async () => {
        try {
          await apiClient.logout();
        } finally {
          await clearPrivateLearningData().catch(() => undefined);
          clearAuth();
        }
      },
      can: (permission) => Boolean(user?.permissions.includes(permission)),
      canAny: (permissions) => permissions.some((permission) => user?.permissions.includes(permission)),
    }),
    [acceptAuth, clearAuth, isLoading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
