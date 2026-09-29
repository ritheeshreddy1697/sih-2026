import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  ListChecks,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  ApiError,
  apiClient,
  type DashboardMetric,
  type DashboardResponse,
} from "../lib/api/client";
import { cn } from "../lib/utils";

const metricToneClasses: Record<DashboardMetric["tone"], string> = {
  neutral: "border-l-slate-400",
  success: "border-l-emerald-600",
  warning: "border-l-amber-500",
  accent: "border-l-primary",
};

const statusClasses = {
  scheduled: "bg-sky-100 text-sky-800",
  due: "bg-amber-100 text-amber-900",
  completed: "bg-emerald-100 text-emerald-800",
  pending: "bg-slate-100 text-slate-700",
  confirmed: "bg-emerald-100 text-emerald-800",
};

export function DashboardPage() {
  const { user, logout } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setDashboard(await apiClient.dashboard());
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Dashboard information is unavailable.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  if (!user) return null;

  return (
    <AppShell user={user} onLogout={logout} notifications={dashboard?.notifications}>
      {isLoading ? (
        <div className="mx-auto max-w-xl py-16">
          <LoadingState label="Loading your dashboard" />
        </div>
      ) : null}

      {error ? (
        <div className="mx-auto max-w-xl py-12">
          <ErrorState
            title="Dashboard could not be loaded"
            description={error}
            onRetry={loadDashboard}
          />
        </div>
      ) : null}

      {!isLoading && !error && dashboard ? (
        <div className="space-y-7">
          <header className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <Badge className="bg-emerald-100 text-emerald-800">Live workspace</Badge>
              <h1 className="mt-3 text-2xl font-semibold tracking-normal sm:text-3xl">
                {dashboard.title}
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                {dashboard.description}
              </p>
            </div>
            <p className="text-sm text-muted-foreground">
              Welcome,{" "}
              <span className="font-medium text-foreground">
                {user.profile?.full_name ?? user.email}
              </span>
            </p>
          </header>

          <section aria-labelledby="dashboard-summary-heading">
            <div className="mb-4 flex items-center justify-between">
              <h2 id="dashboard-summary-heading" className="text-base font-semibold">
                At a glance
              </h2>
              <span className="text-xs text-muted-foreground">Updated today</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {dashboard.metrics.map((metric) => (
                <Card
                  key={metric.label}
                  className={cn("border-l-4", metricToneClasses[metric.tone])}
                >
                  <CardContent className="p-5">
                    <p className="text-sm text-muted-foreground">{metric.label}</p>
                    <p className="mt-3 text-3xl font-semibold tracking-normal">{metric.value}</p>
                    <p className="mt-2 flex items-center gap-1.5 text-xs leading-5 text-muted-foreground">
                      <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                      {metric.change}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section aria-labelledby="quick-actions-heading">
            <h2 id="quick-actions-heading" className="mb-4 text-base font-semibold">
              Quick actions
            </h2>
            <div className="grid gap-4 md:grid-cols-3">
              {dashboard.quick_actions.map((action) => (
                <Link
                  key={action.href}
                  to={action.href}
                  className="group flex min-h-32 items-start justify-between gap-4 rounded-lg border bg-card p-5 shadow-sm transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <div>
                    <p className="font-semibold">{action.label}</p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {action.description}
                    </p>
                  </div>
                  <ArrowUpRight
                    className="h-5 w-5 shrink-0 text-muted-foreground transition-colors group-hover:text-primary"
                    aria-hidden="true"
                  />
                </Link>
              ))}
            </div>
          </section>

          <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle>{dashboard.schedule_title}</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Dates and actions that need attention.
                  </p>
                </div>
                <CalendarDays className="h-5 w-5 text-primary" aria-hidden="true" />
              </CardHeader>
              <CardContent>
                {dashboard.schedule.length ? (
                  <ul className="divide-y">
                    {dashboard.schedule.map((item) => (
                      <li
                        key={`${item.date_label}-${item.title}`}
                        className="grid gap-3 py-4 first:pt-1 sm:grid-cols-[80px_1fr_auto] sm:items-center"
                      >
                        <p className="text-sm font-semibold text-primary">{item.date_label}</p>
                        <div>
                          <p className="text-sm font-medium">{item.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{item.meta}</p>
                        </div>
                        <Badge
                          className={cn("w-fit capitalize", statusClasses[item.status])}
                        >
                          {item.status}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState title="No upcoming items" description="Your schedule is clear." />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle>Recent activity</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Latest updates in your workspace.
                  </p>
                </div>
                <ListChecks className="h-5 w-5 text-primary" aria-hidden="true" />
              </CardHeader>
              <CardContent>
                {dashboard.activity.length ? (
                  <ul className="space-y-5">
                    {dashboard.activity.map((activity, index) => (
                      <li key={`${activity.title}-${activity.time_label}`} className="flex gap-3">
                        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-primary">
                          {index === 0 ? (
                            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <Clock3 className="h-4 w-4" aria-hidden="true" />
                          )}
                        </span>
                        <div>
                          <p className="text-sm font-medium">{activity.title}</p>
                          <p className="mt-1 text-xs leading-5 text-muted-foreground">
                            {activity.description}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {activity.time_label}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState title="No recent activity" description="New updates appear here." />
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
