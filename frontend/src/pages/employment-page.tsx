import {
  BadgeCheck,
  BriefcaseBusiness,
  CalendarClock,
  Check,
  Download,
  FileSearch,
  Heart,
  LockKeyhole,
  MapPin,
  Search,
  ShieldCheck,
  Upload,
  UserRoundSearch,
  X,
} from "lucide-react";
import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

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
  type Candidate,
  type CertificateVerification,
  type EmployerProfile,
  type EmployerWorkspace,
  type EmploymentProfilePayload,
  type Job,
  type JobApplication,
  type JobApplicationStatus,
  type JobPayload,
  type TraineeEmploymentWorkspace,
} from "../lib/api/client";
import { cn } from "../lib/utils";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string | null) {
  if (!value) return "No deadline";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value));
}

function errorMessage(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

function statusTone(value: string) {
  if (["verified", "published", "hired", "offered", "valid"].includes(value)) {
    return "bg-emerald-100 text-emerald-800";
  }
  if (["rejected", "closed", "withdrawn", "revoked", "expired"].includes(value)) {
    return "bg-red-100 text-red-800";
  }
  return "bg-amber-100 text-amber-900";
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="text-sm font-medium">
      {label}
      <span className="mt-2 block">{children}</span>
    </label>
  );
}

function TabBar<Tab extends string>({
  tabs,
  active,
  onChange,
  label,
}: {
  tabs: readonly Tab[];
  active: Tab;
  onChange: (tab: Tab) => void;
  label: string;
}) {
  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!(["ArrowLeft", "ArrowRight"] as string[]).includes(event.key)) return;
    event.preventDefault();
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const next = (index + direction + tabs.length) % tabs.length;
    onChange(tabs[next]);
    document.getElementById(`employment-tab-${tabs[next]}`)?.focus();
  };
  return (
    <div className="mt-6 overflow-x-auto border-b" role="tablist" aria-label={label}>
      <div className="flex min-w-max gap-1">
        {tabs.map((tab, index) => (
          <button
            id={`employment-tab-${tab}`}
            key={tab}
            type="button"
            role="tab"
            aria-selected={active === tab}
            tabIndex={active === tab ? 0 : -1}
            className={cn(
              "min-h-11 border-b-2 px-4 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              active === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onChange(tab)}
            onKeyDown={(event) => move(event, index)}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  );
}

function PageHeading({ title, description }: { title: string; description: string }) {
  return (
    <header>
      <p className="text-sm font-semibold text-primary">Employment exchange</p>
      <h1 className="mt-1 text-2xl font-semibold sm:text-3xl">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
    </header>
  );
}

function MatchDetails({ job }: { job: Job }) {
  if (!job.match) return null;
  return (
    <div className="mt-4 border-t pt-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold">Why this matches</p>
        <span className="text-lg font-semibold text-primary">{job.match.score}/100</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <span>Skills {job.match.skill_score}/40</span>
        <span>Course {job.match.course_score}/25</span>
        <span>Location {job.match.location_score}/20</span>
        <span>Interests {job.match.interest_score}/15</span>
      </div>
      <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
        {job.match.reasons.map((reason) => (
          <li className="flex gap-2" key={reason}>
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" aria-hidden="true" />
            {reason}
          </li>
        ))}
        {job.match.gaps.map((gap) => (
          <li className="flex gap-2" key={gap}>
            <X className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
            {gap}
          </li>
        ))}
      </ul>
    </div>
  );
}

function JobCard({
  job,
  onSave,
  onApply,
}: {
  job: Job;
  onSave?: (job: Job) => void;
  onApply?: (job: Job) => void;
}) {
  return (
    <article id={`job-${job.id}`} tabIndex={-1} className="rounded-md border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{job.company_name}</p>
          <h3 className="mt-1 text-lg font-semibold">{job.title}</h3>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1"><MapPin className="h-4 w-4" aria-hidden="true" />{job.location}</span>
            <span>{labelize(job.workplace_mode)}</span>
            <span>{labelize(job.employment_type)}</span>
          </div>
        </div>
        <Badge className={statusTone(job.application_status ?? job.status)}>
          {labelize(job.application_status ?? job.status)}
        </Badge>
      </div>
      <p className="mt-4 text-sm leading-6 text-muted-foreground">{job.description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {job.required_skills.map((skill) => <Badge className="border bg-transparent" key={skill}>{skill}</Badge>)}
      </div>
      <p className="mt-4 text-xs text-muted-foreground">Apply by {formatDate(job.application_deadline)}</p>
      <MatchDetails job={job} />
      {onSave || onApply ? (
        <div className="mt-5 flex flex-wrap gap-2 border-t pt-4">
          {onSave ? (
            <Button variant="outline" onClick={() => onSave(job)}>
              <Heart className={cn("h-4 w-4", job.saved && "fill-current")} aria-hidden="true" />
              {job.saved ? "Saved" : "Save"}
            </Button>
          ) : null}
          {onApply && !job.application_status ? (
            <Button onClick={() => onApply(job)}>Apply now</Button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function AdminEmployment() {
  const [employers, setEmployers] = useState<EmployerProfile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(async () => {
    setError(null);
    try { setEmployers(await apiClient.adminEmployers()); }
    catch (caught) { setError(errorMessage(caught, "Unable to load employer registrations.")); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const decide = async (profile: EmployerProfile, status: "verified" | "rejected") => {
    const notes = status === "rejected"
      ? window.prompt("Reason for rejection")?.trim()
      : "Company registration reviewed by NCCT.";
    if (status === "rejected" && !notes) return;
    try {
      await apiClient.verifyEmployer(profile.id, { status, notes });
      setMessage(`${profile.company_name} marked ${status}.`);
      await load();
    } catch (caught) { setError(errorMessage(caught, "Verification could not be updated.")); }
  };

  if (!employers && !error) return <LoadingState label="Loading employer registrations" />;
  if (error && !employers) return <ErrorState title="Employer registrations unavailable" description={error} onRetry={load} />;
  return (
    <>
      <PageHeading title="Employer verification" description="Review company registrations before recruiters can publish vacancies or search certified trainees." />
      {message ? <p className="mt-5 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      <div className="mt-7 space-y-4">
        {employers?.map((profile) => (
          <article className="rounded-md border bg-card p-5" key={profile.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><h2 className="font-semibold">{profile.company_name}</h2><p className="mt-1 text-sm text-muted-foreground">{profile.industry} · {profile.headquarters}</p></div>
              <Badge className={statusTone(profile.verification_status)}>{labelize(profile.verification_status)}</Badge>
            </div>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">{profile.description}</p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <div><dt className="text-xs text-muted-foreground">Contact</dt><dd>{profile.contact_name}<br />{profile.contact_email}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Registration</dt><dd>{profile.registration_number || "Not provided"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Company size</dt><dd>{profile.company_size || "Not provided"}</dd></div>
            </dl>
            {profile.verification_status === "pending" ? (
              <div className="mt-5 flex gap-2 border-t pt-4">
                <Button onClick={() => void decide(profile, "verified")}><ShieldCheck className="h-4 w-4" aria-hidden="true" />Verify</Button>
                <Button variant="outline" onClick={() => void decide(profile, "rejected")}>Reject</Button>
              </div>
            ) : profile.verification_notes ? <p className="mt-4 text-sm text-muted-foreground">Review note: {profile.verification_notes}</p> : null}
          </article>
        ))}
        {!employers?.length ? <EmptyState icon={ShieldCheck} title="No employer registrations" description="New employer registration requests will appear here." /> : null}
      </div>
    </>
  );
}

const employerTabs = ["Jobs", "Candidates", "Applications", "Company", "Verify certificate"] as const;
type EmployerTab = (typeof employerTabs)[number];

const blankJob: JobPayload = {
  title: "", description: "", location: "", employment_type: "full_time",
  workplace_mode: "on_site", required_skills: [], preferred_skills: [],
  minimum_experience_years: 0, vacancies: 1, salary_minimum: null,
  salary_maximum: null, application_deadline: null, required_programme_ids: [],
};

function EmployerEmployment() {
  const [workspace, setWorkspace] = useState<EmployerWorkspace | null>(null);
  const [active, setActive] = useState<EmployerTab>("Jobs");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [jobForm, setJobForm] = useState<JobPayload>(blankJob);
  const [showJobForm, setShowJobForm] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [candidateFilters, setCandidateFilters] = useState({
    job_id: "", skill: "", location: "", course_id: "", certificate_number: "",
  });
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateLoading, setCandidateLoading] = useState(false);
  const [verificationToken, setVerificationToken] = useState("");
  const [verification, setVerification] = useState<CertificateVerification | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setWorkspace(await apiClient.employerWorkspace()); }
    catch (caught) { setError(errorMessage(caught, "Unable to load the employer workspace.")); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const submitJob = async (event: FormEvent) => {
    event.preventDefault(); setError(null);
    try {
      if (editingJob) await apiClient.updateJob(editingJob.id, jobForm);
      else await apiClient.createJob(jobForm);
      setJobForm(blankJob); setShowJobForm(false); setEditingJob(null);
      setMessage(editingJob ? "Job changes saved." : "Draft job created."); await load();
    } catch (caught) { setError(errorMessage(caught, "Job could not be created.")); }
  };
  const editJob = (job: Job) => {
    setEditingJob(job);
    setJobForm({
      title: job.title,
      description: job.description,
      location: job.location,
      employment_type: job.employment_type,
      workplace_mode: job.workplace_mode,
      required_skills: job.required_skills,
      preferred_skills: job.preferred_skills,
      minimum_experience_years: job.minimum_experience_years,
      vacancies: job.vacancies,
      salary_minimum: job.salary_minimum,
      salary_maximum: job.salary_maximum,
      application_deadline: job.application_deadline,
      required_programme_ids: job.required_programmes.map((programme) => programme.id),
    });
    setShowJobForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const lifecycle = async (job: Job, action: "publish" | "close") => {
    try { await (action === "publish" ? apiClient.publishJob(job.id) : apiClient.closeJob(job.id)); setMessage(`Job ${action === "publish" ? "published" : "closed"}.`); await load(); }
    catch (caught) { setError(errorMessage(caught, "Job status could not be updated.")); }
  };
  const findCandidates = async (event?: FormEvent) => {
    event?.preventDefault(); setCandidateLoading(true); setError(null);
    try { setCandidates(await apiClient.searchCandidates(candidateFilters)); }
    catch (caught) { setError(errorMessage(caught, "Candidate search failed.")); }
    finally { setCandidateLoading(false); }
  };
  const shortlist = async (candidate: Candidate) => {
    if (!candidateFilters.job_id) { setError("Select a job before shortlisting a candidate."); return; }
    try { await apiClient.shortlistCandidate(candidateFilters.job_id, candidate.trainee_id); setMessage(`${candidate.full_name} shortlisted.`); await findCandidates(); await load(); }
    catch (caught) { setError(errorMessage(caught, "Candidate could not be shortlisted.")); }
  };
  const updateApplication = async (application: JobApplication, status: Exclude<JobApplicationStatus, "applied" | "withdrawn">) => {
    const payload: Parameters<typeof apiClient.updateJobApplication>[1] = { status };
    if (status === "interview_scheduled") {
      const interviewAt = window.prompt("Interview date and time (YYYY-MM-DDTHH:mm)");
      const interviewMode = window.prompt("Interview mode (for example, video call)");
      if (!interviewAt || !interviewMode) return;
      payload.interview_at = new Date(interviewAt).toISOString(); payload.interview_mode = interviewMode;
    }
    try { await apiClient.updateJobApplication(application.id, payload); setMessage("Application status updated."); await load(); }
    catch (caught) { setError(errorMessage(caught, "Application status could not be updated.")); }
  };

  if (!workspace && !error) return <LoadingState label="Loading recruitment workspace" />;
  if (error && !workspace) return <ErrorState title="Recruitment workspace unavailable" description={error} onRetry={load} />;
  if (!workspace) return null;
  return (
    <>
      <PageHeading title="Recruitment workspace" description="Publish opportunities, find certificate-backed skills and manage each candidate through a clear hiring process." />
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Badge className={statusTone(workspace.profile.verification_status)}>{labelize(workspace.profile.verification_status)} employer</Badge>
        <span className="text-sm text-muted-foreground">{workspace.profile.company_name}</span>
      </div>
      {message ? <p className="mt-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}
      {error ? <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p> : null}
      <TabBar tabs={employerTabs} active={active} onChange={setActive} label="Recruitment workspace sections" />

      {active === "Jobs" ? (
        <section className="mt-6" aria-labelledby="jobs-heading">
          <div className="flex items-center justify-between gap-3"><h2 id="jobs-heading" className="text-lg font-semibold">Job postings</h2><Button onClick={() => { setEditingJob(null); setJobForm(blankJob); setShowJobForm(true); }}>Create job</Button></div>
          {showJobForm ? (
            <form className="mt-5 grid gap-4 rounded-md border bg-card p-5 sm:grid-cols-2" onSubmit={submitJob}>
              <Field label="Job title"><Input value={jobForm.title} onChange={(event) => setJobForm({ ...jobForm, title: event.target.value })} required /></Field>
              <Field label="Location"><Input value={jobForm.location} onChange={(event) => setJobForm({ ...jobForm, location: event.target.value })} required /></Field>
              <Field label="Employment type"><select className={fieldClass} value={jobForm.employment_type} onChange={(event) => setJobForm({ ...jobForm, employment_type: event.target.value as JobPayload["employment_type"] })}><option value="full_time">Full time</option><option value="part_time">Part time</option><option value="contract">Contract</option><option value="internship">Internship</option></select></Field>
              <Field label="Workplace"><select className={fieldClass} value={jobForm.workplace_mode} onChange={(event) => setJobForm({ ...jobForm, workplace_mode: event.target.value as JobPayload["workplace_mode"] })}><option value="on_site">On site</option><option value="hybrid">Hybrid</option><option value="remote">Remote</option></select></Field>
              <Field label="Required skills (comma separated)"><Input value={jobForm.required_skills.join(", ")} onChange={(event) => setJobForm({ ...jobForm, required_skills: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></Field>
              <Field label="Application deadline"><Input type="datetime-local" onChange={(event) => setJobForm({ ...jobForm, application_deadline: event.target.value ? new Date(event.target.value).toISOString() : null })} /></Field>
              <Field label="Vacancies"><Input type="number" min={1} value={jobForm.vacancies} onChange={(event) => setJobForm({ ...jobForm, vacancies: Number(event.target.value) })} required /></Field>
              <Field label="Minimum experience (years)"><Input type="number" min={0} value={jobForm.minimum_experience_years} onChange={(event) => setJobForm({ ...jobForm, minimum_experience_years: Number(event.target.value) })} required /></Field>
              <label className="text-sm font-medium sm:col-span-2">Description<textarea className={`${fieldClass} mt-2 min-h-28`} minLength={20} value={jobForm.description} onChange={(event) => setJobForm({ ...jobForm, description: event.target.value })} required /></label>
              <Field label="Minimum annual salary"><Input type="number" min={0} value={jobForm.salary_minimum ?? ""} onChange={(event) => setJobForm({ ...jobForm, salary_minimum: event.target.value ? Number(event.target.value) : null })} /></Field>
              <Field label="Maximum annual salary"><Input type="number" min={0} value={jobForm.salary_maximum ?? ""} onChange={(event) => setJobForm({ ...jobForm, salary_maximum: event.target.value ? Number(event.target.value) : null })} /></Field>
              <Field label="Required course IDs (comma separated)"><Input value={jobForm.required_programme_ids.join(", ")} onChange={(event) => setJobForm({ ...jobForm, required_programme_ids: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></Field>
              <Field label="Preferred skills (comma separated)"><Input value={jobForm.preferred_skills.join(", ")} onChange={(event) => setJobForm({ ...jobForm, preferred_skills: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></Field>
              <div className="flex gap-2 sm:col-span-2"><Button type="submit">{editingJob ? "Save changes" : "Save draft"}</Button><Button type="button" variant="outline" onClick={() => { setShowJobForm(false); setEditingJob(null); }}>Cancel</Button></div>
            </form>
          ) : null}
          <div className="mt-5 space-y-4">
            {workspace.jobs.map((job) => <div key={job.id}><JobCard job={job} /><div className="-mt-1 flex gap-2 rounded-b-md border border-t-0 bg-card px-5 pb-5">{job.status !== "closed" ? <Button size="sm" variant="outline" onClick={() => editJob(job)}>Edit</Button> : null}{job.status === "draft" ? <Button size="sm" onClick={() => void lifecycle(job, "publish")}>Publish</Button> : null}{job.status === "published" ? <Button size="sm" variant="outline" onClick={() => void lifecycle(job, "close")}>Close job</Button> : null}</div></div>)}
            {!workspace.jobs.length ? <EmptyState icon={BriefcaseBusiness} title="No jobs yet" description="Create a draft vacancy, review it and publish when ready." /> : null}
          </div>
        </section>
      ) : null}

      {active === "Candidates" ? (
        <section className="mt-6"><h2 className="text-lg font-semibold">Certified candidate search</h2><p className="mt-1 text-sm text-muted-foreground">Only trainees who opted into placement visibility and hold a valid certificate are listed.</p>
          <form className="mt-5 grid gap-3 rounded-md border bg-card p-4 sm:grid-cols-2 xl:grid-cols-6" onSubmit={(event) => void findCandidates(event)}>
            <select aria-label="Job for matching" className={fieldClass} value={candidateFilters.job_id} onChange={(event) => setCandidateFilters({ ...candidateFilters, job_id: event.target.value })}><option value="">No specific job</option>{workspace.jobs.filter((job) => job.status === "published").map((job) => <option value={job.id} key={job.id}>{job.title}</option>)}</select>
            <Input aria-label="Verified skill" placeholder="Verified skill" value={candidateFilters.skill} onChange={(event) => setCandidateFilters({ ...candidateFilters, skill: event.target.value })} />
            <Input aria-label="Candidate location" placeholder="Location" value={candidateFilters.location} onChange={(event) => setCandidateFilters({ ...candidateFilters, location: event.target.value })} />
            <select aria-label="Certified course" className={fieldClass} value={candidateFilters.course_id} onChange={(event) => setCandidateFilters({ ...candidateFilters, course_id: event.target.value })}><option value="">Any certified course</option>{Array.from(new Map(workspace.jobs.flatMap((job) => job.required_programmes).map((programme) => [programme.id, programme])).values()).map((programme) => <option value={programme.id} key={programme.id}>{programme.title}</option>)}</select>
            <Input aria-label="Certificate number" placeholder="Certificate number" value={candidateFilters.certificate_number} onChange={(event) => setCandidateFilters({ ...candidateFilters, certificate_number: event.target.value })} />
            <Button type="submit"><Search className="h-4 w-4" aria-hidden="true" />Search</Button>
          </form>
          <div className="mt-5 space-y-4">{candidateLoading ? <LoadingState label="Searching certified candidates" /> : candidates.map((candidate) => <CandidateCard key={candidate.trainee_id} candidate={candidate} onShortlist={() => void shortlist(candidate)} />)}{!candidateLoading && !candidates.length ? <EmptyState icon={UserRoundSearch} title="No candidates loaded" description="Choose filters and search the consented certified talent pool." /> : null}</div>
        </section>
      ) : null}

      {active === "Applications" ? <ApplicationsList applications={workspace.applications} employer onStatus={updateApplication} /> : null}
      {active === "Company" ? <CompanyProfile profile={workspace.profile} onSaved={load} /> : null}
      {active === "Verify certificate" ? (
        <section className="mt-6 max-w-2xl"><h2 className="text-lg font-semibold">Verify a certificate</h2><form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={async (event) => { event.preventDefault(); setError(null); try { setVerification(await apiClient.verifyCertificate(verificationToken.trim())); } catch (caught) { setVerification(null); setError(errorMessage(caught, "Certificate could not be verified.")); } }}><Input aria-label="Certificate verification token" value={verificationToken} onChange={(event) => setVerificationToken(event.target.value)} placeholder="Enter token from certificate QR link" required /><Button type="submit"><FileSearch className="h-4 w-4" aria-hidden="true" />Verify</Button></form>{verification ? <div className="mt-5 rounded-md border bg-card p-5"><Badge className={statusTone(verification.state)}>{labelize(verification.state)}</Badge><h3 className="mt-3 font-semibold">{verification.recipient_name}</h3><p className="mt-1 text-sm text-muted-foreground">{verification.title} · {verification.certificate_number}</p></div> : null}</section>
      ) : null}
    </>
  );
}

function CandidateCard({ candidate, onShortlist }: { candidate: Candidate; onShortlist: () => void }) {
  return <article className="rounded-md border bg-card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{candidate.full_name}</h3><p className="mt-1 text-sm text-muted-foreground">{candidate.headline || "Certified trainee"} · {candidate.location || "Location not listed"}</p></div>{candidate.match ? <span className="text-lg font-semibold text-primary">{candidate.match.score}/100</span> : null}</div><div className="mt-4 flex flex-wrap gap-2">{candidate.verified_skills.map((skill) => <Badge className="border bg-transparent" key={skill}><BadgeCheck className="mr-1 h-3 w-3" aria-hidden="true" />{skill}</Badge>)}</div>{candidate.match ? <div className="mt-4 text-sm text-muted-foreground">{candidate.match.reasons.map((reason) => <p className="mt-1" key={reason}>• {reason}</p>)}</div> : null}<div className="mt-4 rounded-md bg-muted p-3 text-sm">{candidate.contact ? <p>{candidate.contact.email}{candidate.contact.phone ? ` · ${candidate.contact.phone}` : ""}</p> : <p className="flex gap-2 text-muted-foreground"><LockKeyhole className="h-4 w-4 shrink-0" aria-hidden="true" />{candidate.contact_locked_reason}</p>}</div><div className="mt-4 flex flex-wrap gap-2"><Button size="sm" onClick={onShortlist} disabled={candidate.shortlisted}>{candidate.shortlisted ? "Shortlisted" : "Shortlist"}</Button>{candidate.resume_download_allowed ? <Button size="sm" variant="outline" onClick={async () => { const blob = await apiClient.candidateResume(candidate.trainee_id); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `${candidate.full_name}-resume`; link.click(); URL.revokeObjectURL(link.href); }}><Download className="h-4 w-4" aria-hidden="true" />Resume</Button> : null}</div></article>;
}

function ApplicationsList({ applications, employer = false, onStatus, onWithdraw }: { applications: JobApplication[]; employer?: boolean; onStatus?: (application: JobApplication, status: Exclude<JobApplicationStatus, "applied" | "withdrawn">) => void; onWithdraw?: (application: JobApplication) => void }) {
  return <section className="mt-6"><h2 className="text-lg font-semibold">Applications</h2><div className="mt-5 space-y-4">{applications.map((application) => <article className="rounded-md border bg-card p-5" key={application.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{application.job_title}</h3><p className="mt-1 text-sm text-muted-foreground">{employer ? application.trainee_name : application.company_name}</p></div><Badge className={statusTone(application.status)}>{labelize(application.status)}</Badge></div>{application.interview_at ? <p className="mt-4 flex items-center gap-2 text-sm"><CalendarClock className="h-4 w-4 text-primary" aria-hidden="true" />{formatDate(application.interview_at)} · {application.interview_mode}</p> : null}{application.contact ? <p className="mt-3 text-sm">{application.contact.email}{application.contact.phone ? ` · ${application.contact.phone}` : ""}</p> : null}<div className="mt-4 flex flex-wrap gap-2 border-t pt-4">{employer && onStatus && !["hired", "rejected", "withdrawn"].includes(application.status) ? <select aria-label={`Update status for ${application.trainee_name}`} className={`${fieldClass} max-w-64`} value="" onChange={(event) => { if (event.target.value) onStatus(application, event.target.value as Exclude<JobApplicationStatus, "applied" | "withdrawn">); }}><option value="">Update status</option><option value="shortlisted">Shortlisted</option><option value="interview_scheduled">Schedule interview</option><option value="interview_completed">Interview completed</option><option value="offered">Offer</option><option value="hired">Hired</option><option value="rejected">Reject</option></select> : null}{!employer && onWithdraw && !["hired", "rejected", "withdrawn"].includes(application.status) ? <Button size="sm" variant="outline" onClick={() => onWithdraw(application)}>Withdraw</Button> : null}</div></article>)}{!applications.length ? <EmptyState icon={BriefcaseBusiness} title="No applications" description={employer ? "Applications to your published jobs will appear here." : "Jobs you apply for will appear here."} /> : null}</div></section>;
}

function CompanyProfile({ profile, onSaved }: { profile: EmployerProfile; onSaved: () => Promise<void> }) {
  const [form, setForm] = useState({ industry: profile.industry, website: profile.website, company_size: profile.company_size, description: profile.description, headquarters: profile.headquarters, registration_number: profile.registration_number });
  const [message, setMessage] = useState<string | null>(null);
  return <section className="mt-6 max-w-3xl"><h2 className="text-lg font-semibold">Company profile</h2><form className="mt-5 grid gap-4 rounded-md border bg-card p-5 sm:grid-cols-2" onSubmit={async (event) => { event.preventDefault(); await apiClient.updateEmployerProfile(form); setMessage("Company profile saved."); await onSaved(); }}><Field label="Industry"><Input value={form.industry} onChange={(event) => setForm({ ...form, industry: event.target.value })} required /></Field><Field label="Headquarters"><Input value={form.headquarters} onChange={(event) => setForm({ ...form, headquarters: event.target.value })} required /></Field><Field label="Website"><Input type="url" value={form.website || ""} onChange={(event) => setForm({ ...form, website: event.target.value || null })} /></Field><Field label="Company size"><Input value={form.company_size || ""} onChange={(event) => setForm({ ...form, company_size: event.target.value || null })} /></Field><label className="text-sm font-medium sm:col-span-2">Description<textarea className={`${fieldClass} mt-2 min-h-28`} minLength={20} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} required /></label><div className="sm:col-span-2"><Button type="submit">Save company profile</Button>{message ? <span className="ml-3 text-sm text-emerald-700" role="status">{message}</span> : null}</div></form></section>;
}

const traineeTabs = ["Recommended", "Search jobs", "Saved", "Applications", "Employment profile"] as const;
type TraineeTab = (typeof traineeTabs)[number];

function TraineeEmployment() {
  const [searchParams] = useSearchParams();
  const linkedJobId = searchParams.get("job");
  const [workspace, setWorkspace] = useState<TraineeEmploymentWorkspace | null>(null);
  const [active, setActive] = useState<TraineeTab>(linkedJobId ? "Search jobs" : "Recommended");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filters, setFilters] = useState({ query: "", location: "", skill: "" });
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(async () => { setError(null); try { setWorkspace(await apiClient.traineeEmploymentWorkspace()); } catch (caught) { setError(errorMessage(caught, "Unable to load employment opportunities.")); } }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!linkedJobId) return;
    const loadLinkedJob = async () => {
      try {
        const publishedJobs = await apiClient.searchJobs({});
        setJobs(publishedJobs.filter((job) => job.id === linkedJobId));
        setActive("Search jobs");
        window.setTimeout(() => document.getElementById(`job-${linkedJobId}`)?.focus(), 0);
      } catch (caught) {
        setError(errorMessage(caught, "The linked job could not be loaded."));
      }
    };
    void loadLinkedJob();
  }, [linkedJobId]);
  const search = async (event: FormEvent) => { event.preventDefault(); try { setJobs(await apiClient.searchJobs(filters)); } catch (caught) { setError(errorMessage(caught, "Job search failed.")); } };
  const save = async (job: Job) => { try { if (job.saved) await apiClient.unsaveJob(job.id); else await apiClient.saveJob(job.id); await load(); if (active === "Search jobs") setJobs(await apiClient.searchJobs(filters)); } catch (caught) { setError(errorMessage(caught, "Saved jobs could not be updated.")); } };
  const apply = async (job: Job) => { const cover = window.prompt("Optional note to the employer") || undefined; try { await apiClient.applyForJob(job.id, cover); setMessage(`Application sent to ${job.company_name}.`); await load(); if (active === "Search jobs") setJobs(await apiClient.searchJobs(filters)); } catch (caught) { setError(errorMessage(caught, "Application could not be submitted.")); } };
  const withdraw = async (application: JobApplication) => { try { await apiClient.withdrawJobApplication(application.id); setMessage("Application withdrawn."); await load(); } catch (caught) { setError(errorMessage(caught, "Application could not be withdrawn.")); } };
  if (!workspace && !error) return <LoadingState label="Loading employment exchange" />;
  if (error && !workspace) return <ErrorState title="Employment exchange unavailable" description={error} onRetry={load} />;
  if (!workspace) return null;
  return <><PageHeading title="Jobs for certified trainees" description="Find verified employers and understand exactly how your certified skills, courses, interests and location contribute to every recommendation." />{message ? <p className="mt-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{message}</p> : null}{error ? <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p> : null}<TabBar tabs={traineeTabs} active={active} onChange={setActive} label="Employment sections" />
    {active === "Recommended" ? <section className="mt-6"><h2 className="text-lg font-semibold">Recommended for you</h2><div className="mt-5 grid gap-5 xl:grid-cols-2">{workspace.recommendations.map((job) => <JobCard key={job.id} job={job} onSave={(item) => void save(item)} onApply={(item) => void apply(item)} />)}{!workspace.recommendations.length ? <EmptyState icon={BriefcaseBusiness} title="No recommendations yet" description="Complete your employment profile and verified training to improve matches." /> : null}</div></section> : null}
    {active === "Search jobs" ? <section className="mt-6"><h2 className="text-lg font-semibold">Search jobs</h2><form className="mt-4 grid gap-3 rounded-md border bg-card p-4 sm:grid-cols-4" onSubmit={(event) => void search(event)}><Input aria-label="Job keywords" placeholder="Role or keyword" value={filters.query} onChange={(event) => setFilters({ ...filters, query: event.target.value })} /><Input aria-label="Job location" placeholder="Location" value={filters.location} onChange={(event) => setFilters({ ...filters, location: event.target.value })} /><Input aria-label="Job skill" placeholder="Skill" value={filters.skill} onChange={(event) => setFilters({ ...filters, skill: event.target.value })} /><Button type="submit"><Search className="h-4 w-4" aria-hidden="true" />Search</Button></form><div className="mt-5 grid gap-5 xl:grid-cols-2">{jobs.map((job) => <JobCard key={job.id} job={job} onSave={(item) => void save(item)} onApply={(item) => void apply(item)} />)}{!jobs.length ? <EmptyState icon={Search} title="Search published jobs" description="Use role, location or verified skill filters to narrow the list." /> : null}</div></section> : null}
    {active === "Saved" ? <section className="mt-6"><h2 className="text-lg font-semibold">Saved jobs</h2><div className="mt-5 grid gap-5 xl:grid-cols-2">{workspace.saved_jobs.map((job) => <JobCard key={job.id} job={job} onSave={(item) => void save(item)} onApply={(item) => void apply(item)} />)}{!workspace.saved_jobs.length ? <EmptyState icon={Heart} title="No saved jobs" description="Save an opportunity to return to it later." /> : null}</div></section> : null}
    {active === "Applications" ? <ApplicationsList applications={workspace.applications} onWithdraw={(application) => void withdraw(application)} /> : null}
    {active === "Employment profile" ? <TraineeProfileForm workspace={workspace} onSaved={load} /> : null}
  </>;
}

function TraineeProfileForm({ workspace, onSaved }: { workspace: TraineeEmploymentWorkspace; onSaved: () => Promise<void> }) {
  const profile = workspace.profile;
  const [form, setForm] = useState<EmploymentProfilePayload>({ headline: profile.headline, professional_summary: profile.professional_summary, preferred_roles: profile.preferred_roles, preferred_locations: profile.preferred_locations, open_to_work: profile.open_to_work });
  const [message, setMessage] = useState<string | null>(null);
  return <section className="mt-6 max-w-3xl"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-semibold">Employment profile</h2><p className="mt-1 text-sm text-muted-foreground">Verified skills come from valid NCCT certificates and cannot be edited here.</p></div><Badge className={profile.open_to_work ? "bg-emerald-100 text-emerald-800" : "bg-muted"}>{profile.open_to_work ? "Open to work" : "Not visible"}</Badge></div>{!profile.placement_visibility_consent ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">Enable placement visibility in My profile before employers can find you.</p> : null}<form className="mt-5 grid gap-4 rounded-md border bg-card p-5 sm:grid-cols-2" onSubmit={async (event) => { event.preventDefault(); await apiClient.updateEmploymentProfile(form); setMessage("Employment profile saved."); await onSaved(); }}><Field label="Professional headline"><Input value={form.headline || ""} onChange={(event) => setForm({ ...form, headline: event.target.value || null })} /></Field><Field label="Preferred roles (comma separated)"><Input value={form.preferred_roles.join(", ")} onChange={(event) => setForm({ ...form, preferred_roles: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></Field><Field label="Preferred locations (comma separated)"><Input value={form.preferred_locations.join(", ")} onChange={(event) => setForm({ ...form, preferred_locations: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></Field><label className="flex min-h-11 items-center gap-3 rounded-md border px-3 text-sm font-medium"><input type="checkbox" className="h-4 w-4 accent-primary" checked={form.open_to_work} onChange={(event) => setForm({ ...form, open_to_work: event.target.checked })} />Open to work</label><label className="text-sm font-medium sm:col-span-2">Professional summary<textarea className={`${fieldClass} mt-2 min-h-28`} value={form.professional_summary || ""} onChange={(event) => setForm({ ...form, professional_summary: event.target.value || null })} /></label><div className="sm:col-span-2"><p className="text-sm font-medium">Verified skills</p><div className="mt-2 flex flex-wrap gap-2">{profile.verified_skills.map((skill) => <Badge className="border bg-transparent" key={`${skill.certificate_id}-${skill.name}`}><BadgeCheck className="mr-1 h-3 w-3" aria-hidden="true" />{skill.name}</Badge>)}</div></div><div className="sm:col-span-2"><Button type="submit">Save profile</Button>{message ? <span className="ml-3 text-sm text-emerald-700" role="status">{message}</span> : null}</div></form><div className="mt-5 rounded-md border bg-card p-5"><h3 className="font-semibold">Resume</h3><p className="mt-1 text-sm text-muted-foreground">{profile.resume_filename || "No resume uploaded"}</p><label className="mt-4 inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-muted"><Upload className="h-4 w-4" aria-hidden="true" />Upload PDF, DOC or DOCX<input className="sr-only" type="file" accept=".pdf,.doc,.docx" onChange={async (event) => { const file = event.target.files?.[0]; if (!file) return; await apiClient.uploadEmploymentResume(file); setMessage("Resume uploaded."); await onSaved(); }} /></label></div></section>;
}

export function EmploymentPage() {
  const { user, logout, can } = useAuth();
  if (!user) return null;
  return <AppShell user={user} onLogout={logout}>{can("employment:verify") ? <AdminEmployment /> : can("employment:manage") ? <EmployerEmployment /> : <TraineeEmployment />}</AppShell>;
}
