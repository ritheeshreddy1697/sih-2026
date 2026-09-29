import { LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { Button } from "../components/ui/button";

export function ForbiddenPage() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <AppShell user={user} onLogout={logout}>
      <section className="mx-auto flex max-w-xl flex-col items-center py-20 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <LockKeyhole className="h-6 w-6" aria-hidden="true" />
        </span>
        <h1 className="mt-5 text-2xl font-semibold tracking-normal">Access not permitted</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Your current role does not include permission for this area.
        </p>
        <Button asChild className="mt-6">
          <Link to="/dashboard">Return to dashboard</Link>
        </Button>
      </section>
    </AppShell>
  );
}
