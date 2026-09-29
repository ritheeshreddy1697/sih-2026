import {
  ArrowDownToLine,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Filter,
  Info,
  MapPinned,
  RotateCcw,
} from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  ApiError,
  apiClient,
  type AnalyticsDashboard,
  type AnalyticsDrilldown,
  type AnalyticsFilterOptions,
  type AnalyticsFilters,
  type AnalyticsGeographyRow,
  type AnalyticsMetric,
  type AnalyticsMetricKey,
  type AnalyticsPerformanceRow,
} from "../lib/api/client";
import { cn } from "../lib/utils";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function errorMessage(caught: unknown) {
  return caught instanceof ApiError ? caught.message : "Analytics could not be loaded.";
}

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatMetric(metric: AnalyticsMetric) {
  const value = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(metric.value);
  if (metric.unit === "percent") return `${value}%`;
  if (metric.unit === "percentage_points") return `${value} pp`;
  return value;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function MetricGrid({
  metrics,
  selected,
  onSelect,
}: {
  metrics: AnalyticsMetric[];
  selected: AnalyticsMetricKey | null;
  onSelect: (metric: AnalyticsMetricKey) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Analytics summary">
      {metrics.map((metric) => (
        <button
          key={metric.key}
          type="button"
          aria-label={`${metric.label} ${formatMetric(metric)}. Open detailed records`}
          aria-pressed={selected === metric.key}
          className={cn(
            "min-h-36 rounded-md border bg-card p-4 text-left shadow-sm transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
            selected === metric.key && "border-primary ring-1 ring-primary",
          )}
          onClick={() => onSelect(metric.key)}
        >
          <span className="block text-sm font-medium text-muted-foreground">{metric.label}</span>
          <span className="mt-3 block text-2xl font-semibold tracking-normal">
            {formatMetric(metric)}
          </span>
          <span className="mt-2 block text-xs leading-5 text-muted-foreground">
            {metric.denominator === null
              ? "Open detailed records"
              : metric.key === "assessment_improvement"
                ? `${metric.denominator} matched assessment pairs`
                : `${metric.numerator} of ${metric.denominator}`}
          </span>
        </button>
      ))}
    </div>
  );
}

function BarList({
  rows,
  valueKey,
  valueLabel,
}: {
  rows: AnalyticsPerformanceRow[];
  valueKey: "approved_participants" | "course_completion_rate";
  valueLabel: string;
}) {
  if (!rows.length) return null;
  const maximum = Math.max(...rows.map((row) => row[valueKey]), 1);
  return (
    <div
      className="space-y-4"
      role="img"
      aria-label={`${valueLabel} comparison. Exact values are listed for each row.`}
    >
      {rows.slice(0, 8).map((row) => {
        const value = row[valueKey];
        const width = `${Math.max((value / maximum) * 100, value > 0 ? 3 : 0)}%`;
        return (
          <div key={row.id}>
            <div className="mb-1.5 flex items-end justify-between gap-4 text-sm">
              <span className="truncate font-medium">{row.label}</span>
              <span className="shrink-0 tabular-nums">
                {value}
                {valueKey === "course_completion_rate" ? "%" : ""}
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-sm bg-muted" aria-hidden="true">
              <div className="h-full bg-primary" style={{ width }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PerformanceTable({
  rows,
  caption,
}: {
  rows: AnalyticsPerformanceRow[];
  caption: string;
}) {
  return (
    <div className="mt-6 overflow-x-auto rounded-md border">
      <table className="w-full min-w-[1320px] text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-muted text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3" scope="col">Name</th>
            <th className="px-4 py-3 text-right" scope="col">Registrations</th>
            <th className="px-4 py-3 text-right" scope="col">Approved</th>
            <th className="px-4 py-3 text-right" scope="col">Enrolments</th>
            <th className="px-4 py-3 text-right" scope="col">Attendance</th>
            <th className="px-4 py-3 text-right" scope="col">Completion</th>
            <th className="px-4 py-3 text-right" scope="col">Improvement</th>
            <th className="px-4 py-3 text-right" scope="col">Dropout</th>
            <th className="px-4 py-3 text-right" scope="col">Certificates</th>
            <th className="px-4 py-3 text-right" scope="col">Applications</th>
            <th className="px-4 py-3 text-right" scope="col">Interviews</th>
            <th className="px-4 py-3 text-right" scope="col">Placements</th>
          </tr>
        </thead>
        <tbody className="divide-y bg-card">
          {rows.map((row) => (
            <tr key={row.id}>
              <th className="px-4 py-3 font-medium" scope="row">
                <span className="flex items-center gap-2">
                  {row.label}
                  {row.is_demo ? <Badge className="bg-amber-100 text-amber-900">Demo</Badge> : null}
                </span>
                <span className="mt-1 block text-xs font-normal text-muted-foreground">
                  {row.secondary_label}
                </span>
              </th>
              <td className="px-4 py-3 text-right tabular-nums">{row.registrations}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.approved_participants}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.enrollments}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.attendance_percentage}%</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.course_completion_rate}%</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.assessment_improvement} pp</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.dropout_rate}%</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.certificates_issued}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.job_applications}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.interviews}</td>
              <td className="px-4 py-3 text-right tabular-nums">{row.placements}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerformanceSection({
  title,
  description,
  rows,
  view,
  onExport,
  exporting,
}: {
  title: string;
  description: string;
  rows: AnalyticsPerformanceRow[];
  view: "institution" | "programme";
  onExport: (view: "institution" | "programme" | "geography") => void;
  exporting: string | null;
}) {
  return (
    <section className="border-t pt-8" aria-labelledby={`${view}-performance-heading`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id={`${view}-performance-heading`} className="text-lg font-semibold">{title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        <Button
          variant="outline"
          onClick={() => onExport(view)}
          disabled={exporting !== null || !rows.length}
        >
          <ArrowDownToLine className="h-4 w-4" aria-hidden="true" />
          {exporting === view ? "Preparing CSV" : "Export CSV"}
        </Button>
      </div>
      {rows.length ? (
        <>
          <div className="mt-6 rounded-md border bg-card p-4 sm:p-5">
            <h3 className="text-sm font-semibold">Approved participant comparison</h3>
            <div className="mt-5">
              <BarList rows={rows} valueKey="approved_participants" valueLabel={title} />
            </div>
          </div>
          <PerformanceTable rows={rows} caption={`${title} summary table`} />
        </>
      ) : (
        <div className="mt-6">
          <EmptyState
            icon={BarChart3}
            title={`No ${view} results`}
            description="Adjust the filters to include programmes with persisted activity."
          />
        </div>
      )}
    </section>
  );
}

function GeographySection({
  rows,
  onExport,
  exporting,
}: {
  rows: AnalyticsGeographyRow[];
  onExport: (view: "geography") => void;
  exporting: string | null;
}) {
  const maximum = Math.max(...rows.map((row) => row.enrollments), 1);
  return (
    <section className="border-t pt-8" aria-labelledby="geography-heading">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id="geography-heading" className="text-lg font-semibold">Geographic distribution</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Participant home state from trainee profiles. Missing locations remain visible as Not provided.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => onExport("geography")}
          disabled={exporting !== null || !rows.length}
        >
          <ArrowDownToLine className="h-4 w-4" aria-hidden="true" />
          {exporting === "geography" ? "Preparing CSV" : "Export CSV"}
        </Button>
      </div>
      {rows.length ? (
        <>
          <div
            className="mt-6 space-y-4 rounded-md border bg-card p-4 sm:p-5"
            role="img"
            aria-label="Enrolments by participant home state. Exact values are listed for each state."
          >
            {rows.slice(0, 10).map((row) => (
              <div key={row.state}>
                <div className="mb-1.5 flex justify-between gap-4 text-sm">
                  <span className="font-medium">{row.state}</span>
                  <span className="tabular-nums">{row.enrollments}</span>
                </div>
                <div className="h-3 overflow-hidden rounded-sm bg-muted" aria-hidden="true">
                  <div
                    className="h-full bg-emerald-600"
                    style={{ width: `${Math.max((row.enrollments / maximum) * 100, 3)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 overflow-x-auto rounded-md border">
            <table className="w-full min-w-[760px] text-left text-sm">
              <caption className="sr-only">Geographic distribution summary</caption>
              <thead className="bg-muted text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3" scope="col">State</th>
                  <th className="px-4 py-3 text-right" scope="col">Registrations</th>
                  <th className="px-4 py-3 text-right" scope="col">Approved</th>
                  <th className="px-4 py-3 text-right" scope="col">Enrolments</th>
                  <th className="px-4 py-3 text-right" scope="col">Certificates</th>
                  <th className="px-4 py-3 text-right" scope="col">Placements</th>
                </tr>
              </thead>
              <tbody className="divide-y bg-card">
                {rows.map((row) => (
                  <tr key={row.state}>
                    <th className="px-4 py-3 font-medium" scope="row">{row.state}</th>
                    <td className="px-4 py-3 text-right tabular-nums">{row.registrations}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{row.approved_participants}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{row.enrollments}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{row.certificates_issued}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{row.placements}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="mt-6">
          <EmptyState
            icon={MapPinned}
            title="No geographic results"
            description="No participant profile locations match the current filters."
          />
        </div>
      )}
    </section>
  );
}

function DrilldownSection({
  data,
  loading,
  error,
  onPage,
}: {
  data: AnalyticsDrilldown | null;
  loading: boolean;
  error: string | null;
  onPage: (page: number) => void;
}) {
  if (loading) return <LoadingState label="Loading metric detail" />;
  if (error) return <ErrorState title="Metric detail unavailable" description={error} />;
  if (!data) return null;
  return (
    <section className="border-t pt-8" aria-labelledby="drilldown-heading">
      <h2 id="drilldown-heading" className="text-lg font-semibold" tabIndex={-1}>
        {data.title}
      </h2>
      <p className="mt-1 max-w-4xl text-sm leading-6 text-muted-foreground">{data.definition}</p>
      {data.rows.length ? (
        <div className="mt-5 overflow-x-auto rounded-md border">
          <table className="w-full min-w-[780px] text-left text-sm">
            <caption className="sr-only">{data.title}</caption>
            <thead className="bg-muted text-xs uppercase text-muted-foreground">
              <tr>
                {data.columns.map((column) => (
                  <th className="px-4 py-3" key={column.key} scope="col">{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y bg-card">
              {data.rows.map((row, index) => (
                <tr key={`${data.metric}-${data.page}-${index}`}>
                  {data.columns.map((column) => (
                    <td className="px-4 py-3" key={column.key}>
                      {row[column.key] === null || row[column.key] === ""
                        ? "Not provided"
                        : String(row[column.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mt-5">
          <EmptyState
            title="No detailed records"
            description="The metric has no measurable records for the current filters."
          />
        </div>
      )}
      {data.pages > 1 ? (
        <div className="mt-4 flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} records
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon"
              aria-label="Previous detail page"
              disabled={data.page <= 1}
              onClick={() => onPage(data.page - 1)}
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Next detail page"
              disabled={data.page >= data.pages}
              onClick={() => onPage(data.page + 1)}
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function AnalyticsPage() {
  const { user, logout } = useAuth();
  const [options, setOptions] = useState<AnalyticsFilterOptions | null>(null);
  const [dashboard, setDashboard] = useState<AnalyticsDashboard | null>(null);
  const [draftFilters, setDraftFilters] = useState<AnalyticsFilters>({});
  const [appliedFilters, setAppliedFilters] = useState<AnalyticsFilters>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState<AnalyticsMetricKey | null>(null);
  const [drilldown, setDrilldown] = useState<AnalyticsDrilldown | null>(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [drilldownError, setDrilldownError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);
  const drilldownRef = useRef<HTMLDivElement>(null);

  const loadDashboard = useCallback(async (filters: AnalyticsFilters) => {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await apiClient.analyticsDashboard(filters));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([apiClient.analyticsOptions(), apiClient.analyticsDashboard()])
      .then(([nextOptions, nextDashboard]) => {
        if (!active) return;
        setOptions(nextOptions);
        setDashboard(nextDashboard);
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleProgrammes = useMemo(
    () =>
      options?.programmes.filter(
        (programme) =>
          !draftFilters.institution_id || programme.institution_id === draftFilters.institution_id,
      ) ?? [],
    [draftFilters.institution_id, options],
  );

  const applyFilters = (event: FormEvent) => {
    event.preventDefault();
    setAppliedFilters(draftFilters);
    setSelectedMetric(null);
    setDrilldown(null);
    void loadDashboard(draftFilters);
  };

  const resetFilters = () => {
    setDraftFilters({});
    setAppliedFilters({});
    setSelectedMetric(null);
    setDrilldown(null);
    void loadDashboard({});
  };

  const loadDrilldown = useCallback(
    async (metric: AnalyticsMetricKey, page = 1) => {
      setSelectedMetric(metric);
      setDrilldownLoading(true);
      setDrilldownError(null);
      try {
        setDrilldown(await apiClient.analyticsDrilldown(metric, appliedFilters, page));
      } catch (caught) {
        setDrilldownError(errorMessage(caught));
      } finally {
        setDrilldownLoading(false);
      }
    },
    [appliedFilters],
  );

  const exportCsv = async (view: "institution" | "programme" | "geography") => {
    setExporting(view);
    setError(null);
    try {
      const blob = await apiClient.analyticsCsv(view, appliedFilters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ncct-analytics-${view}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setExporting(null);
    }
  };

  if (!user) return null;

  return (
    <AppShell user={user} onLogout={logout}>
      <div className="space-y-8">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">Reporting</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">Training analytics</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Persisted programme, learning, attendance, certification and employment outcomes.
            </p>
          </div>
          {dashboard ? (
            <p className="text-xs text-muted-foreground">
              Updated {formatDateTime(dashboard.generated_at)}
            </p>
          ) : null}
        </header>

        {error && !dashboard ? (
          <ErrorState
            title="Analytics unavailable"
            description={error}
            onRetry={() => loadDashboard(appliedFilters)}
          />
        ) : null}

        {options ? (
          <form className="border-y bg-card py-5" onSubmit={applyFilters}>
            <div className="mb-4 flex items-center gap-2">
              <Filter className="h-5 w-5 text-primary" aria-hidden="true" />
              <h2 className="text-base font-semibold">Filters</h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <label className="text-sm font-medium">
                Institution
                <select
                  className={fieldClass}
                  value={draftFilters.institution_id ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      institution_id: event.target.value || undefined,
                      programme_id: undefined,
                    }))
                  }
                >
                  <option value="">All in my scope</option>
                  {options.institutions.map((institution) => (
                    <option key={institution.id} value={institution.id}>
                      {institution.name}{institution.is_demo ? " (Demo)" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium" htmlFor="analytics-programme-filter">
                Programme
                <select
                  id="analytics-programme-filter"
                  className={fieldClass}
                  value={draftFilters.programme_id ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      programme_id: event.target.value || undefined,
                    }))
                  }
                >
                  <option value="">All programmes</option>
                  {visibleProgrammes.map((programme) => (
                    <option key={programme.id} value={programme.id}>
                      {programme.title}{programme.is_demo ? " (Demo)" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium">
                Programme start date from
                <input
                  className={fieldClass}
                  type="date"
                  min={options.start_date_min ?? undefined}
                  max={options.start_date_max ?? undefined}
                  value={draftFilters.start_date ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      start_date: event.target.value || undefined,
                    }))
                  }
                />
              </label>
              <label className="text-sm font-medium">
                Programme start date to
                <input
                  className={fieldClass}
                  type="date"
                  min={options.start_date_min ?? undefined}
                  max={options.start_date_max ?? undefined}
                  value={draftFilters.end_date ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      end_date: event.target.value || undefined,
                    }))
                  }
                />
              </label>
              <label className="text-sm font-medium">
                Participant state
                <select
                  className={fieldClass}
                  value={draftFilters.state ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      state: event.target.value || undefined,
                    }))
                  }
                >
                  <option value="">All states</option>
                  {options.states.map((state) => <option key={state}>{state}</option>)}
                </select>
              </label>
              <label className="text-sm font-medium">
                Gender
                <select
                  className={fieldClass}
                  value={draftFilters.gender ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      gender: event.target.value || undefined,
                    }))
                  }
                >
                  <option value="">All genders</option>
                  {options.genders.map((gender) => <option key={gender}>{gender}</option>)}
                </select>
              </label>
              <label className="text-sm font-medium">
                Participant category
                <select
                  className={fieldClass}
                  value={draftFilters.participant_category ?? ""}
                  onChange={(event) =>
                    setDraftFilters((current) => ({
                      ...current,
                      participant_category:
                        (event.target.value as AnalyticsFilters["participant_category"]) || undefined,
                    }))
                  }
                >
                  <option value="">All categories</option>
                  {options.participant_categories.map((category) => (
                    <option key={category} value={category}>{labelize(category)}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button type="submit" disabled={loading}>
                <Filter className="h-4 w-4" aria-hidden="true" />
                Apply filters
              </Button>
              <Button type="button" variant="outline" onClick={resetFilters} disabled={loading}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reset
              </Button>
            </div>
          </form>
        ) : null}

        {loading ? <LoadingState label="Calculating persisted analytics" /> : null}

        {!loading && dashboard ? (
          <>
            <section aria-labelledby="summary-heading">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 id="summary-heading" className="text-lg font-semibold">Summary</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Scope: {dashboard.scope_label}</p>
                </div>
                {dashboard.contains_demo_data ? (
                  <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                    Seeded demonstration data is included in this view.
                  </div>
                ) : null}
              </div>
              <MetricGrid
                metrics={dashboard.metrics}
                selected={selectedMetric}
                onSelect={(metric) => void loadDrilldown(metric)}
              />
              <details className="mt-5 rounded-md border bg-card p-4">
                <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-semibold">
                  <Info className="h-4 w-4 text-primary" aria-hidden="true" />
                  Metric definitions
                </summary>
                <dl className="mt-3 grid gap-4 border-t pt-4 md:grid-cols-2">
                  {dashboard.metrics.map((metric) => (
                    <div key={metric.key}>
                      <dt className="text-sm font-semibold">{metric.label}</dt>
                      <dd className="mt-1 text-sm leading-6 text-muted-foreground">
                        {metric.definition}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="mt-4 border-t pt-4 text-sm text-muted-foreground">
                  Date filters select programmes by programme start date. All outcomes are then calculated for those programme cohorts.
                </p>
              </details>
            </section>

            <div ref={drilldownRef}>
              <DrilldownSection
                data={drilldown}
                loading={drilldownLoading}
                error={drilldownError}
                onPage={(page) => selectedMetric && void loadDrilldown(selectedMetric, page)}
              />
            </div>

            <PerformanceSection
              title="Institution-wise performance"
              description="Compares institutions in the signed-in administrator's authorized hierarchy."
              rows={dashboard.institution_performance}
              view="institution"
              onExport={(view) => void exportCsv(view)}
              exporting={exporting}
            />
            <PerformanceSection
              title="Programme-wise performance"
              description="Shows each selected programme using the same definitions as the summary metrics."
              rows={dashboard.programme_performance}
              view="programme"
              onExport={(view) => void exportCsv(view)}
              exporting={exporting}
            />
            <GeographySection
              rows={dashboard.geographic_distribution}
              onExport={(view) => void exportCsv(view)}
              exporting={exporting}
            />
          </>
        ) : null}

        {error && dashboard ? (
          <ErrorState title="One analytics action failed" description={error} />
        ) : null}
      </div>
    </AppShell>
  );
}
