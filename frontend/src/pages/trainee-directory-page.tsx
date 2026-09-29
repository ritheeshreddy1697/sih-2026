import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowRight, Filter, Search, UserRoundSearch } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type InstitutionRecord,
  type TraineeListItem,
  type TrainerListItem,
} from "../lib/api/client";

type DirectoryTab = "trainees" | "trainers";

const fieldClass =
  "h-11 rounded-md border bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary";

export function TraineeDirectoryPage() {
  const { user, logout, can } = useAuth();
  const [activeTab, setActiveTab] = useState<DirectoryTab>("trainees");
  const [trainees, setTrainees] = useState<TraineeListItem[]>([]);
  const [trainers, setTrainers] = useState<TrainerListItem[]>([]);
  const [institutions, setInstitutions] = useState<InstitutionRecord[]>([]);
  const [query, setQuery] = useState("");
  const [institutionId, setInstitutionId] = useState("");
  const [stateName, setStateName] = useState("");
  const [language, setLanguage] = useState("");
  const [skill, setSkill] = useState("");
  const [minimumCompletion, setMinimumCompletion] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canViewPrivateProfiles = can("profiles:view_private");

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (activeTab === "trainees") {
        const result = await apiClient.trainees({
          q: query || undefined,
          institution_id: institutionId || undefined,
          state: stateName || undefined,
          language: language || undefined,
          skill: skill || undefined,
          minimum_completion: minimumCompletion ? Number(minimumCompletion) : undefined,
          page,
          page_size: 12,
        });
        setTrainees(result.items);
        setPages(result.pages);
        setTotal(result.total);
      } else {
        const result = await apiClient.trainersDirectory({
          q: query || undefined,
          institution_id: institutionId || undefined,
          page,
          page_size: 12,
        });
        setTrainers(result.items);
        setPages(result.pages);
        setTotal(result.total);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : `Unable to load ${activeTab}.`);
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, institutionId, language, minimumCompletion, page, query, skill, stateName]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!canViewPrivateProfiles) return;
    void apiClient
      .institutions({ page_size: 100 })
      .then((result) => setInstitutions(result.items))
      .catch(() => setInstitutions([]));
  }, [canViewPrivateProfiles]);

  if (!user) return null;

  const search = (event: FormEvent) => {
    event.preventDefault();
    if (page === 1) void load();
    else setPage(1);
  };

  const selectTab = (tab: DirectoryTab) => {
    setActiveTab(tab);
    setPage(1);
  };

  const subject = activeTab === "trainees" ? "trainee" : "trainer";

  return (
    <AppShell user={user} onLogout={logout}>
      <div>
        <p className="text-sm font-semibold text-primary">Authorised administration</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">People directory</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          {canViewPrivateProfiles
            ? "Find trainees and trainers within your institution scope by name, email, or exact user ID."
            : "Find trainees enrolled in your assigned batches by name, email, or exact user ID."}
        </p>
      </div>

      <div className="mt-6 overflow-x-auto border-b" role="tablist" aria-label="People directory roles">
        <div className="flex min-w-max gap-1">
          {(canViewPrivateProfiles ? ["trainees", "trainers"] as const : ["trainees"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              className={`min-h-11 border-b-2 px-4 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                activeTab === tab
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => selectTab(tab)}
            >
              {tab === "trainees" ? "Trainees" : "Trainers"}
            </button>
          ))}
        </div>
      </div>

      <form
        className={`grid gap-3 border-b bg-card py-4 md:grid-cols-2 ${
          activeTab === "trainees"
            ? canViewPrivateProfiles ? "xl:grid-cols-6" : "xl:grid-cols-5"
            : "xl:grid-cols-[minmax(0,1fr)_minmax(220px,320px)_auto]"
        }`}
        onSubmit={search}
        aria-label={`${subject} filters`}
      >
        <Input
          aria-label={`Search ${activeTab}`}
          placeholder="Name, email, or exact user ID"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {canViewPrivateProfiles ? (
          <select
            className={fieldClass}
            aria-label="Institution"
            value={institutionId}
            onChange={(event) => setInstitutionId(event.target.value)}
          >
            <option value="">All institutions</option>
            {institutions.map((institution) => (
              <option key={institution.id} value={institution.id}>{institution.name}</option>
            ))}
          </select>
        ) : null}
        {activeTab === "trainees" ? (
          <>
            <Input aria-label="State" placeholder="State" value={stateName} onChange={(event) => setStateName(event.target.value)} />
            <Input aria-label="Preferred language" placeholder="Language" value={language} onChange={(event) => setLanguage(event.target.value)} />
            <Input aria-label="Skill" placeholder="Skill" value={skill} onChange={(event) => setSkill(event.target.value)} />
            <div className="flex gap-2">
              <select className={`${fieldClass} min-w-0 flex-1`} aria-label="Minimum completion" value={minimumCompletion} onChange={(event) => setMinimumCompletion(event.target.value)}>
                <option value="">All levels</option>
                <option value="25">25%+</option>
                <option value="50">50%+</option>
                <option value="75">75%+</option>
                <option value="100">Complete</option>
              </select>
              <Button type="submit" size="icon" variant="outline" aria-label="Apply trainee filters"><Search className="h-4 w-4" aria-hidden="true" /></Button>
            </div>
          </>
        ) : (
          <Button type="submit" variant="outline"><Search className="h-4 w-4" aria-hidden="true" />Search</Button>
        )}
      </form>

      <div className="mt-5 flex items-center gap-2 text-sm text-muted-foreground">
        <Filter className="h-4 w-4" aria-hidden="true" />
        {activeTab === "trainees"
          ? `${total} trainee profile${total === 1 ? "" : "s"}`
          : `${total} trainer${total === 1 ? "" : "s"}`}
      </div>
      <div className="mt-5" role="tabpanel" aria-label={activeTab} aria-live="polite">
        {isLoading ? <LoadingState label={`Loading ${activeTab}`} /> : null}
        {error ? <ErrorState title={`${activeTab === "trainees" ? "Trainees" : "Trainers"} could not be loaded`} description={error} onRetry={load} /> : null}
        {!isLoading && !error && activeTab === "trainees" && trainees.length === 0 ? (
          <EmptyState icon={UserRoundSearch} title="No trainees found" description="Try changing one or more filters." />
        ) : null}
        {!isLoading && !error && activeTab === "trainers" && trainers.length === 0 ? (
          <EmptyState icon={UserRoundSearch} title="No trainers found" description="Try changing the name, ID, or institution filter." />
        ) : null}
        {!isLoading && !error && activeTab === "trainees" && trainees.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {trainees.map((trainee) => (
              <article key={trainee.user_id} className="rounded-md border bg-card p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="truncate font-semibold">{trainee.full_name}</h2>
                      {trainee.is_demo ? <Badge className="bg-sky-100 text-sky-800">Demonstration data</Badge> : null}
                    </div>
                    <p className="mt-1 truncate text-sm text-muted-foreground">{trainee.email}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{trainee.institution?.name ?? "No institution assigned"}</p>
                    <p className="mt-2 break-all font-mono text-xs text-muted-foreground">ID: {trainee.user_id}</p>
                  </div>
                  <StatusBadge status={trainee.account_status} />
                </div>
                <div className="mt-5">
                  <div className="flex justify-between text-xs"><span>Profile completion</span><span className="font-semibold">{trainee.completion_percent}%</span></div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary" style={{ width: `${trainee.completion_percent}%` }} /></div>
                </div>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <div><dt className="text-xs text-muted-foreground">Location</dt><dd>{trainee.preferred_location ?? trainee.state ?? "Not recorded"}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Language</dt><dd>{trainee.preferred_language ?? "Not recorded"}</dd></div>
                </dl>
                <div className="mt-4 flex flex-wrap gap-2">
                  {trainee.skills.slice(0, 4).map((item) => <Badge key={item}>{item}</Badge>)}
                  {trainee.pending_documents ? <Badge className="bg-amber-100 text-amber-900">{trainee.pending_documents} document pending</Badge> : null}
                </div>
                {canViewPrivateProfiles ? (
                  <div className="mt-5 border-t pt-3 text-right">
                    <Button asChild variant="ghost" size="sm"><Link to={`/directory/trainees/${trainee.user_id}`}>Open private profile <ArrowRight className="h-4 w-4" aria-hidden="true" /></Link></Button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
        {!isLoading && !error && activeTab === "trainers" && trainers.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {trainers.map((trainer) => (
              <article key={trainer.user_id} className="rounded-md border bg-card p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate font-semibold">{trainer.full_name}</h2>
                    <p className="mt-1 truncate text-sm text-muted-foreground">{trainer.email}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{trainer.institution?.name ?? "No institution assigned"}</p>
                    <p className="mt-2 break-all font-mono text-xs text-muted-foreground">ID: {trainer.user_id}</p>
                  </div>
                  <StatusBadge status={trainer.account_status} />
                </div>
                <dl className="mt-5 grid gap-3 border-t pt-4 text-sm sm:grid-cols-2">
                  <div><dt className="text-xs text-muted-foreground">Designation</dt><dd>{trainer.designation ?? "Trainer"}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Phone</dt><dd>{trainer.phone ?? "Not recorded"}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : null}
      </div>
      {pages > 1 ? (
        <nav className="mt-6 flex items-center justify-between border-t pt-4" aria-label={`${subject === "trainee" ? "Trainee" : "Trainer"} pages`}>
          <Button type="button" variant="outline" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</Button>
          <span className="text-sm text-muted-foreground">Page {page} of {pages}</span>
          <Button type="button" variant="outline" disabled={page >= pages} onClick={() => setPage((current) => current + 1)}>Next</Button>
        </nav>
      ) : null}
    </AppShell>
  );
}

function StatusBadge({ status }: { status: TrainerListItem["account_status"] }) {
  return (
    <Badge className={status === "active" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}>
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
