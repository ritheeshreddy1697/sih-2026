import { useCallback, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { ApiError, apiClient } from "../lib/api/client";

export function AdminPage() {
  const { user, logout } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);

  const verifyAuthorization = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.adminCheck();
      setAuthorized(result.authorized);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Authorization check failed.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void verifyAuthorization();
  }, [verifyAuthorization]);

  if (!user) return null;

  return (
    <AppShell user={user} onLogout={logout}>
      <div className="mx-auto max-w-3xl space-y-6">
        <header>
          <p className="text-sm font-medium text-primary">NCCT administration</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Platform controls</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            This boundary is available only to the NCCT super administrator role.
          </p>
        </header>

        {isLoading ? <LoadingState label="Verifying server-side permission" /> : null}
        {error ? (
          <ErrorState title="Authorization failed" description={error} onRetry={verifyAuthorization} />
        ) : null}
        {!isLoading && !error && authorized ? (
          <Card>
            <CardHeader>
              <ShieldCheck className="h-6 w-6 text-primary" aria-hidden="true" />
              <CardTitle>Server authorization confirmed</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-6 text-muted-foreground">
                Future NCCT governance modules can be mounted here without relying on client-side
                role checks for security.
              </p>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </AppShell>
  );
}
