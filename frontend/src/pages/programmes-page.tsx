import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowRight, CalendarDays, MapPin, Plus, Search, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { StatusBadge } from "../components/programmes/status-badge";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type Programme,
  type ProgrammeMode,
  type ProgrammeStatus,
} from "../lib/api/client";

const fieldClass =
  "h-11 rounded-md border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(value),
  );
}

export function ProgrammesPage() {
  const { user, logout, can } = useAuth();
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<ProgrammeMode | "">("");
  const [status, setStatus] = useState<ProgrammeStatus | "">("");
  const [institutionId, setInstitutionId] = useState("");
  const [institutions, setInstitutions] = useState<Array<{ id: string; name: string; code: string }>>(
    [],
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.programmes({
        q: query || undefined,
        mode: mode || undefined,
        status: status || undefined,
        institution_id: institutionId || undefined,
      });
      setProgrammes(result.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load programmes.");
    } finally {
      setIsLoading(false);
    }
  }, [institutionId, mode, query, status]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!can("programmes:approve")) return;
    void apiClient.trainingInstitutions().then(setInstitutions).catch(() => setInstitutions([]));
  }, [can]);

  if (!user) return null;

  const handleSearch = (event: FormEvent) => {
    event.preventDefault();
    void load();
  };

  const showStatusFilter = can("programmes:manage") || can("programmes:approve");

  return (
    <AppShell user={user} onLogout={logout}>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-primary">Training directory</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Programmes</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Find upcoming cooperative training or manage your institution&apos;s programme pipeline.
          </p>
        </div>
        {can("programmes:manage") && !can("programmes:approve") ? (
          <Button asChild className="shrink-0">
            <Link to="/programmes/new">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Create programme
            </Link>
          </Button>
        ) : null}
      </div>

      <form
        className="mt-7 grid gap-3 border-y bg-card py-4 md:grid-cols-2 xl:grid-cols-[minmax(220px,1fr)_170px_180px_220px_auto]"
        onSubmit={handleSearch}
        aria-label="Programme filters"
      >
        <label className="sr-only" htmlFor="programme-search">
          Search programmes
        </label>
        <Input
          id="programme-search"
          placeholder="Search by title or code"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label className="sr-only" htmlFor="programme-mode">
          Delivery mode
        </label>
        <select
          id="programme-mode"
          className={fieldClass}
          value={mode}
          onChange={(event) => setMode(event.target.value as ProgrammeMode | "")}
        >
          <option value="">All delivery modes</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="hybrid">Hybrid</option>
        </select>
        {showStatusFilter ? (
          <select
            className={fieldClass}
            aria-label="Programme status"
            value={status}
            onChange={(event) => setStatus(event.target.value as ProgrammeStatus | "")}
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="pending_approval">Pending approval</option>
            <option value="approved">Approved</option>
            <option value="published">Published</option>
            <option value="rejected">Rejected</option>
            <option value="archived">Archived</option>
          </select>
        ) : (
          <div className="hidden xl:block" />
        )}
        {can("programmes:approve") ? (
          <select
            className={fieldClass}
            aria-label="Training institution"
            value={institutionId}
            onChange={(event) => setInstitutionId(event.target.value)}
          >
            <option value="">All institutions</option>
            {institutions.map((institution) => (
              <option key={institution.id} value={institution.id}>
                {institution.name}
              </option>
            ))}
          </select>
        ) : (
          <div className="hidden xl:block" />
        )}
        <Button type="submit" variant="outline">
          <Search className="h-4 w-4" aria-hidden="true" />
          Search
        </Button>
      </form>

      <div className="mt-6" aria-live="polite">
        {isLoading ? <LoadingState label="Loading programmes" /> : null}
        {error ? (
          <ErrorState title="Programmes could not be loaded" description={error} onRetry={load} />
        ) : null}
        {!isLoading && !error && programmes.length === 0 ? (
          <EmptyState
            title="No programmes found"
            description="Try changing the search filters or create the first programme for your institution."
          />
        ) : null}
        {!isLoading && !error && programmes.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {programmes.map((programme) => (
              <article key={programme.id} className="rounded-lg border bg-card p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase text-muted-foreground">
                      {programme.institution.code} · {programme.code}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold">{programme.title}</h2>
                  </div>
                  <StatusBadge status={programme.status} />
                </div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{programme.summary}</p>
                <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-primary" aria-hidden="true" />
                    <div>
                      <dt className="sr-only">Dates</dt>
                      <dd>{formatDate(programme.start_date)} · {programme.duration_days} days</dd>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <UsersRound className="h-4 w-4 text-primary" aria-hidden="true" />
                    <div>
                      <dt className="sr-only">Available capacity</dt>
                      <dd>{programme.available_capacity} of {programme.capacity} seats available</dd>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 sm:col-span-2">
                    <MapPin className="h-4 w-4 text-primary" aria-hidden="true" />
                    <div>
                      <dt className="sr-only">Mode and location</dt>
                      <dd className="capitalize">
                        {programme.mode}{programme.location ? ` · ${programme.location}` : ""}
                      </dd>
                    </div>
                  </div>
                </dl>
                <div className="mt-5 flex items-center justify-between border-t pt-4">
                  <span className="text-xs text-muted-foreground">
                    Apply by {formatDate(programme.application_deadline)}
                  </span>
                  <Button asChild variant="ghost" size="sm">
                    <Link to={`/programmes/${programme.id}`}>
                      View details <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
