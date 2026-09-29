import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileSpreadsheet,
  Languages,
  MapPin,
  Pencil,
  Send,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { StatusBadge } from "../components/programmes/status-badge";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type EligibilityType,
  type Programme,
  type ProgrammeBatch,
} from "../lib/api/client";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(value),
  );
}

const eligibilityLabels: Record<EligibilityType, string> = {
  individual: "Individual trainees",
  pacs: "PACS nominees",
  shg: "SHG nominees",
  cooperative_institution: "Cooperative institutions",
};

export function ProgrammeDetailPage() {
  const { programmeId } = useParams();
  const { user, logout, can } = useAuth();
  const [programme, setProgramme] = useState<Programme | null>(null);
  const [trainers, setTrainers] = useState<Array<{ id: string; full_name: string; email: string }>>(
    [],
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [statement, setStatement] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [batch, setBatch] = useState({
    name: "",
    code: "",
    capacity: 1,
    start_date: "",
    end_date: "",
    location: "",
  });
  const [nomination, setNomination] = useState({
    nomination_type: "pacs" as EligibilityType,
    candidate_full_name: "",
    candidate_email: "",
    candidate_phone: "",
    member_identifier: "",
  });
  const [csvType, setCsvType] = useState<EligibilityType>("pacs");
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const load = useCallback(async () => {
    if (!programmeId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [detail, trainerOptions] = await Promise.all([
        apiClient.programme(programmeId),
        can("programmes:manage") ? apiClient.trainers() : Promise.resolve([]),
      ]);
      setProgramme(detail);
      setTrainers(trainerOptions);
      setBatch((current) => ({
        ...current,
        capacity: detail.capacity,
        start_date: detail.start_date,
        end_date: detail.end_date,
        location: detail.location ?? "",
      }));
      const eligibleNomination = detail.eligible_applicant_types.find(
        (item) => item !== "individual",
      );
      if (eligibleNomination) {
        setNomination((current) => ({ ...current, nomination_type: eligibleNomination }));
        setCsvType(eligibleNomination);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load this programme.");
    } finally {
      setIsLoading(false);
    }
  }, [can, programmeId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user) return null;

  const runAction = async (action: () => Promise<unknown>, message: string) => {
    setIsWorking(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(message);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The action could not be completed.");
    } finally {
      setIsWorking(false);
    }
  };

  const addBatch = (event: FormEvent) => {
    event.preventDefault();
    if (!programmeId) return;
    void runAction(
      () => apiClient.createBatch(programmeId, batch),
      "Batch added to the programme.",
    );
  };

  const apply = (event: FormEvent) => {
    event.preventDefault();
    if (!programmeId) return;
    void runAction(
      () => apiClient.apply(programmeId, statement),
      "Your application has been submitted.",
    );
  };

  const nominate = (event: FormEvent) => {
    event.preventDefault();
    if (!programmeId) return;
    void runAction(
      () => apiClient.nominate(programmeId, nomination),
      "Candidate nomination submitted.",
    );
  };

  const bulkNominate = (event: FormEvent) => {
    event.preventDefault();
    if (!programmeId || !csvFile) return;
    void runAction(
      async () => {
        const result = await apiClient.bulkNominate(programmeId, csvType, csvFile);
        setNotice(`${result.created} nominations were imported.`);
      },
      "Bulk nominations imported.",
    );
  };

  return (
    <AppShell user={user} onLogout={logout}>
      <Button asChild variant="ghost" size="sm" className="mb-4 -ml-3">
        <Link to="/programmes">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          All programmes
        </Link>
      </Button>

      {isLoading ? <LoadingState label="Loading programme details" /> : null}
      {error ? <ErrorState title="Programme action failed" description={error} onRetry={load} /> : null}
      {notice ? (
        <div className="mb-5 flex items-start gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800" role="status">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {notice}
        </div>
      ) : null}

      {programme ? (
        <div className="space-y-8">
          <header className="border-b pb-7">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={programme.status} />
              <span className="text-xs font-medium text-muted-foreground">
                {programme.institution.code} · {programme.code}
              </span>
            </div>
            <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <h1 className="text-2xl font-semibold tracking-normal sm:text-3xl">{programme.title}</h1>
                <p className="mt-3 text-base leading-7 text-muted-foreground">{programme.summary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {can("programmes:manage") && ["draft", "rejected"].includes(programme.status) ? (
                  <Button asChild variant="outline">
                    <Link to={`/programmes/${programme.id}/edit`}>
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                      Edit
                    </Link>
                  </Button>
                ) : null}
                {can("programmes:manage") && ["draft", "rejected"].includes(programme.status) ? (
                  <Button
                    disabled={isWorking || !programme.batches?.length}
                    onClick={() => void runAction(() => apiClient.transitionProgramme(programme.id, "submit"), "Programme submitted to NCCT.")}
                  >
                    <Send className="h-4 w-4" aria-hidden="true" />
                    Submit for approval
                  </Button>
                ) : null}
                {can("programmes:approve") && programme.status === "pending_approval" ? (
                  <Button disabled={isWorking} onClick={() => void runAction(() => apiClient.transitionProgramme(programme.id, "approve"), "Programme approved.")}>Approve</Button>
                ) : null}
                {can("programmes:manage") && programme.status === "approved" ? (
                  <Button disabled={isWorking} onClick={() => void runAction(() => apiClient.transitionProgramme(programme.id, "publish"), "Programme published to eligible applicants.")}>Publish</Button>
                ) : null}
                {can("programmes:manage") && !["draft", "pending_approval", "archived"].includes(programme.status) ? (
                  <Button variant="outline" disabled={isWorking} onClick={() => void runAction(() => apiClient.transitionProgramme(programme.id, "archive"), "Programme archived.")}>Archive</Button>
                ) : null}
              </div>
            </div>
          </header>

          {can("programmes:approve") && programme.status === "pending_approval" ? (
            <section className="border-l-4 border-l-amber-500 bg-amber-50 p-4" aria-labelledby="review-heading">
              <h2 id="review-heading" className="font-semibold">NCCT review</h2>
              <label className="mt-3 block space-y-2">
                <span className="text-sm font-medium">Reason when rejecting</span>
                <textarea className={fieldClass} rows={3} value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} />
              </label>
              <Button
                className="mt-3"
                variant="outline"
                disabled={isWorking || !rejectionReason.trim()}
                onClick={() => void runAction(() => apiClient.transitionProgramme(programme.id, "reject", rejectionReason), "Programme returned to the institute.")}
              >
                Reject with reason
              </Button>
            </section>
          ) : null}

          <section aria-labelledby="programme-overview">
            <h2 id="programme-overview" className="text-lg font-semibold">Programme overview</h2>
            <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="border-l-4 border-l-primary bg-card p-4">
                <CalendarDays className="h-5 w-5 text-primary" aria-hidden="true" />
                <dt className="mt-3 text-xs text-muted-foreground">Dates</dt>
                <dd className="mt-1 text-sm font-medium">{formatDate(programme.start_date)} to {formatDate(programme.end_date)}</dd>
              </div>
              <div className="border-l-4 border-l-sky-500 bg-card p-4">
                <BookOpen className="h-5 w-5 text-sky-600" aria-hidden="true" />
                <dt className="mt-3 text-xs text-muted-foreground">Delivery</dt>
                <dd className="mt-1 text-sm font-medium capitalize">{programme.mode} · {programme.duration_days} days</dd>
              </div>
              <div className="border-l-4 border-l-amber-500 bg-card p-4">
                <UsersRound className="h-5 w-5 text-amber-600" aria-hidden="true" />
                <dt className="mt-3 text-xs text-muted-foreground">Capacity</dt>
                <dd className="mt-1 text-sm font-medium">{programme.available_capacity} of {programme.capacity} available</dd>
              </div>
              <div className="border-l-4 border-l-emerald-500 bg-card p-4">
                <Languages className="h-5 w-5 text-emerald-600" aria-hidden="true" />
                <dt className="mt-3 text-xs text-muted-foreground">Language</dt>
                <dd className="mt-1 text-sm font-medium">{programme.language}</dd>
              </div>
            </dl>
            <div className="mt-6 grid gap-7 lg:grid-cols-[1.4fr_0.6fr]">
              <div>
                <h3 className="font-semibold">About this programme</h3>
                <p className="mt-2 whitespace-pre-line text-sm leading-7 text-muted-foreground">{programme.description}</p>
                <h3 className="mt-6 font-semibold">Eligibility</h3>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">{programme.eligibility_criteria}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {programme.eligible_applicant_types.map((type) => (
                    <span key={type} className="rounded-md bg-muted px-2.5 py-1 text-xs font-medium">{eligibilityLabels[type]}</span>
                  ))}
                </div>
              </div>
              <dl className="space-y-4 border-t pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
                <div>
                  <dt className="text-xs text-muted-foreground">Institution</dt>
                  <dd className="mt-1 text-sm font-medium">{programme.institution.name}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Application deadline</dt>
                  <dd className="mt-1 flex items-center gap-2 text-sm font-medium"><Clock3 className="h-4 w-4 text-primary" aria-hidden="true" />{formatDate(programme.application_deadline)}</dd>
                </div>
                {programme.location ? (
                  <div>
                    <dt className="text-xs text-muted-foreground">Location</dt>
                    <dd className="mt-1 flex items-start gap-2 text-sm font-medium"><MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />{programme.location}</dd>
                  </div>
                ) : null}
              </dl>
            </div>
          </section>

          {can("applications:apply") ? (
            <section className="border-t pt-7" aria-labelledby="apply-heading">
              <h2 id="apply-heading" className="text-lg font-semibold">Your application</h2>
              {programme.has_applied ? (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-md border bg-card p-4">
                  <p className="text-sm">Your application is already recorded.</p>
                  <Button asChild variant="outline" size="sm"><Link to="/applications">Track status</Link></Button>
                </div>
              ) : programme.can_apply ? (
                <form className="mt-4 max-w-2xl space-y-3" onSubmit={apply}>
                  <label className="block space-y-2">
                    <span className="text-sm font-medium">Why do you want to attend? <span className="font-normal text-muted-foreground">(optional)</span></span>
                    <textarea className={fieldClass} rows={4} maxLength={5000} value={statement} onChange={(event) => setStatement(event.target.value)} />
                  </label>
                  <Button type="submit" disabled={isWorking}>Submit application</Button>
                </form>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">Applications are not currently available for this programme.</p>
              )}
            </section>
          ) : null}

          {can("nominations:create") ? (
            <section className="border-t pt-7" aria-labelledby="nomination-heading">
              <h2 id="nomination-heading" className="text-lg font-semibold">Nominate candidates</h2>
              <div className="mt-5 grid gap-8 lg:grid-cols-2">
                <form className="space-y-4" onSubmit={nominate}>
                  <div className="flex items-center gap-2"><UserPlus className="h-5 w-5 text-primary" aria-hidden="true" /><h3 className="font-semibold">Individual nomination</h3></div>
                  <select className={fieldClass} aria-label="Nomination type" value={nomination.nomination_type} onChange={(event) => setNomination((current) => ({ ...current, nomination_type: event.target.value as EligibilityType }))}>
                    {programme.eligible_applicant_types.filter((type) => type !== "individual").map((type) => <option key={type} value={type}>{eligibilityLabels[type]}</option>)}
                  </select>
                  <Input aria-label="Candidate full name" placeholder="Candidate full name" required value={nomination.candidate_full_name} onChange={(event) => setNomination((current) => ({ ...current, candidate_full_name: event.target.value }))} />
                  <Input aria-label="Candidate email" type="email" placeholder="Candidate email" required value={nomination.candidate_email} onChange={(event) => setNomination((current) => ({ ...current, candidate_email: event.target.value }))} />
                  <Input aria-label="Candidate phone" placeholder="Phone (optional)" value={nomination.candidate_phone} onChange={(event) => setNomination((current) => ({ ...current, candidate_phone: event.target.value }))} />
                  <Input aria-label="Member identifier" placeholder="Member identifier (optional)" value={nomination.member_identifier} onChange={(event) => setNomination((current) => ({ ...current, member_identifier: event.target.value }))} />
                  <Button type="submit" disabled={isWorking}>Submit nomination</Button>
                </form>
                <form className="space-y-4 border-t pt-6 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0" onSubmit={bulkNominate}>
                  <div className="flex items-center gap-2"><FileSpreadsheet className="h-5 w-5 text-primary" aria-hidden="true" /><h3 className="font-semibold">Bulk CSV nomination</h3></div>
                  <p className="text-sm leading-6 text-muted-foreground">Use UTF-8 CSV headers: <code>full_name,email,phone,member_identifier</code>. Up to 500 rows are validated before import.</p>
                  <select className={fieldClass} aria-label="Bulk nomination type" value={csvType} onChange={(event) => setCsvType(event.target.value as EligibilityType)}>
                    {programme.eligible_applicant_types.filter((type) => type !== "individual").map((type) => <option key={type} value={type}>{eligibilityLabels[type]}</option>)}
                  </select>
                  <Input aria-label="Nomination CSV file" type="file" accept=".csv,text/csv" required onChange={(event) => setCsvFile(event.target.files?.[0] ?? null)} />
                  <Button type="submit" variant="outline" disabled={isWorking || !csvFile}>Validate and import</Button>
                </form>
              </div>
            </section>
          ) : null}

          <section className="border-t pt-7" aria-labelledby="batches-heading">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div><h2 id="batches-heading" className="text-lg font-semibold">Batches and trainers</h2><p className="mt-1 text-sm text-muted-foreground">{programme.batches?.length ?? 0} batches configured</p></div>
            </div>
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {programme.batches?.map((item) => (
                <BatchPanel key={item.id} batch={item} trainers={trainers} canManage={can("programmes:manage")} onAssign={(trainerId) => runAction(() => apiClient.assignTrainer(item.id, trainerId), "Trainer assigned to the batch.")} />
              ))}
            </div>
            {can("programmes:manage") && ["draft", "rejected"].includes(programme.status) ? (
              <details className="mt-5 rounded-md border bg-card p-4">
                <summary className="cursor-pointer font-medium">Add a batch</summary>
                <form className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={addBatch}>
                  <Input aria-label="Batch name" placeholder="Batch name" required value={batch.name} onChange={(event) => setBatch((current) => ({ ...current, name: event.target.value }))} />
                  <Input aria-label="Batch code" placeholder="Batch code" required value={batch.code} onChange={(event) => setBatch((current) => ({ ...current, code: event.target.value.toUpperCase() }))} />
                  <Input aria-label="Batch capacity" type="number" min={1} required value={batch.capacity} onChange={(event) => setBatch((current) => ({ ...current, capacity: Number(event.target.value) }))} />
                  <Input aria-label="Batch start date" type="date" required value={batch.start_date} onChange={(event) => setBatch((current) => ({ ...current, start_date: event.target.value }))} />
                  <Input aria-label="Batch end date" type="date" required value={batch.end_date} onChange={(event) => setBatch((current) => ({ ...current, end_date: event.target.value }))} />
                  <Input aria-label="Batch location" placeholder="Batch location" value={batch.location} onChange={(event) => setBatch((current) => ({ ...current, location: event.target.value }))} />
                  <Button type="submit" disabled={isWorking}>Add batch</Button>
                </form>
              </details>
            ) : null}
          </section>

          {can("applications:review") ? (
            <section className="flex flex-col gap-4 border-t pt-7 sm:flex-row sm:items-center sm:justify-between">
              <div><h2 className="text-lg font-semibold">Review submissions</h2><p className="mt-1 text-sm text-muted-foreground">{programme.application_count ?? 0} applications · {programme.nomination_count ?? 0} nominations</p></div>
              <div className="flex gap-2"><Button asChild variant="outline"><Link to={`/applications?programme_id=${programme.id}`}>Applications</Link></Button><Button asChild variant="outline"><Link to={`/nominations?programme_id=${programme.id}`}>Nominations</Link></Button></div>
            </section>
          ) : null}
        </div>
      ) : null}
    </AppShell>
  );
}

function BatchPanel({
  batch,
  trainers,
  canManage,
  onAssign,
}: {
  batch: ProgrammeBatch;
  trainers: Array<{ id: string; full_name: string; email: string }>;
  canManage: boolean;
  onAssign: (trainerId: string) => Promise<unknown>;
}) {
  const [trainerId, setTrainerId] = useState("");
  return (
    <article className="rounded-md border bg-card p-4">
      <div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold">{batch.name}</h3><p className="mt-1 text-xs text-muted-foreground">{batch.code}</p></div><span className="text-sm font-medium">{batch.capacity} seats</span></div>
      <p className="mt-3 text-sm text-muted-foreground">{formatDate(batch.start_date)} to {formatDate(batch.end_date)}{batch.location ? ` · ${batch.location}` : ""}</p>
      <div className="mt-4 border-t pt-3">
        <p className="text-xs font-medium text-muted-foreground">Assigned trainers</p>
        {batch.trainers.length ? <ul className="mt-2 space-y-1 text-sm">{batch.trainers.map((assignment) => <li key={assignment.id}>{assignment.trainer.full_name}</li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">No trainer assigned.</p>}
        {canManage && trainers.length ? (
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <select className={fieldClass} aria-label={`Trainer for ${batch.name}`} value={trainerId} onChange={(event) => setTrainerId(event.target.value)}><option value="">Select trainer</option>{trainers.map((trainer) => <option key={trainer.id} value={trainer.id}>{trainer.full_name}</option>)}</select>
            <Button type="button" variant="outline" disabled={!trainerId} onClick={() => { void onAssign(trainerId); setTrainerId(""); }}>Assign</Button>
          </div>
        ) : null}
      </div>
    </article>
  );
}
