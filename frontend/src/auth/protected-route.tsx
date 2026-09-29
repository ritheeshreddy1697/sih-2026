import { Navigate, useLocation } from "react-router-dom";

import { LoadingState } from "../components/states/loading-state";
import type { PermissionCode } from "../lib/api/client";
import { useAuth } from "./auth-context-value";

type ProtectedRouteProps = {
  children: React.ReactNode;
  requiredPermission?: PermissionCode;
  requiredAnyPermissions?: PermissionCode[];
};

export function ProtectedRoute({
  children,
  requiredPermission,
  requiredAnyPermissions,
}: ProtectedRouteProps) {
  const { user, isLoading, can, canAny } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md">
          <LoadingState label="Restoring your secure session" />
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requiredPermission && !can(requiredPermission)) {
    return <Navigate to="/forbidden" replace />;
  }

  if (requiredAnyPermissions && !canAny(requiredAnyPermissions)) {
    return <Navigate to="/forbidden" replace />;
  }

  return children;
}
