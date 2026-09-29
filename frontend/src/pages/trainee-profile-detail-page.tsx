import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Award, Download, FileCheck2, History, ShieldAlert } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ApiError, apiClient, type TraineeProfile } from "../lib/api/client";

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value)) : "Not recorded";
}

export function TraineeProfileDetailPage() {
  const { traineeId } = useParams();
  const { user, logout, can } = useAuth();
  const [profile, setProfile] = useState<TraineeProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!traineeId) return;
    setIsLoading(true);
    setError(null);
    try { setProfile(await apiClient.traineeProfile(traineeId)); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to load this profile."); }
    finally { setIsLoading(false); }
  }, [traineeId]);

  useEffect(() => { void load(); }, [load]);
  if (!user) return null;

  const validate = async (documentId: string, decision: "verified" | "rejected") => {
    const notes = decision === "rejected" ? window.prompt("Reason for rejection") : "Verified by authorised administrator.";
    if (decision === "rejected" && !notes) return;
    try { await apiClient.validateProfileDocument(documentId, decision, notes ?? undefined); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to validate the document."); }
  };

  const download = async (id: string, filename: string) => {
    try { const blob = await apiClient.downloadProfileDocument(id); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to download the document."); }
  };

  return <AppShell user={user} onLogout={logout}>
    <Button asChild variant="ghost" size="sm"><Link to="/directory/trainees"><ArrowLeft className="h-4 w-4" aria-hidden="true" />Back to trainees</Link></Button>
    <div className="mt-5 flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-amber-950"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" /><div><p className="text-sm font-semibold">Private trainee information</p><p className="mt-1 text-xs leading-5">Access is institution-scoped and recorded in the profile audit history.</p></div></div>
    <div className="mt-6" aria-live="polite">{isLoading ? <LoadingState label="Loading private trainee profile" /> : null}{error ? <ErrorState title="Profile could not be loaded" description={error} onRetry={load} /> : null}</div>
    {!isLoading && profile ? <div className="mt-6 space-y-9">
      <header className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold sm:text-3xl">{profile.full_name}</h1>{profile.is_demo ? <Badge className="bg-sky-100 text-sky-800">Demonstration data</Badge> : null}</div><p className="mt-2 text-sm text-muted-foreground">{profile.email} · {profile.phone ?? "No phone"}</p><p className="mt-1 text-sm text-muted-foreground">{profile.institution?.name ?? "No institution"}</p></div><div className="w-full max-w-xs"><div className="flex justify-between text-sm"><span>Profile completion</span><strong>{profile.completion.percent}%</strong></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary" style={{ width: `${profile.completion.percent}%` }} /></div></div></header>
      <section><h2 className="text-lg font-semibold">Personal, contact and preferences</h2><dl className="mt-4 grid gap-4 rounded-md border bg-card p-5 sm:grid-cols-2 lg:grid-cols-4"><Info label="Date of birth" value={formatDate(profile.date_of_birth)} /><Info label="Location" value={[profile.city, profile.state, profile.postal_code].filter(Boolean).join(", ") || "Not recorded"} /><Info label="Preferred language" value={profile.preferred_language ?? "Not recorded"} /><Info label="Preferred location" value={profile.preferred_location ?? "Not recorded"} /><Info label="Designation" value={profile.designation ?? "Not recorded"} /><Info label="Alternate email" value={profile.alternate_email ?? "Not recorded"} /><Info label="Career interests" value={profile.career_interests ?? "Not recorded"} className="sm:col-span-2" /></dl><div className="mt-3 flex flex-wrap gap-2">{profile.skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div></section>
      <section><h2 className="text-lg font-semibold">Education, work and cooperative membership</h2><div className="mt-4 grid gap-4 lg:grid-cols-3"><SimpleList title="Education" items={profile.education.map((item) => ({ title: item.qualification, detail: `${item.institution_name}${item.completion_year ? ` · ${item.completion_year}` : ""}` }))} /><SimpleList title="Employment" items={profile.employment.map((item) => ({ title: item.job_title, detail: `${item.employer_name} · ${formatDate(item.start_date)}` }))} /><SimpleList title="Memberships" items={profile.memberships.map((item) => ({ title: item.institution_name, detail: `${item.membership_type}${item.member_number ? ` · ${item.member_number}` : ""}` }))} /></div></section>
      <section><h2 className="text-lg font-semibold">Documents and validation</h2>{profile.documents.length ? <ul className="mt-4 divide-y rounded-md border bg-card">{profile.documents.map((document) => <li key={document.id} className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between"><div><p className="text-sm font-medium">{document.filename}</p><p className="mt-1 text-xs text-muted-foreground capitalize">{document.document_type} · {document.validation_status}{document.validated_by_name ? ` by ${document.validated_by_name}` : ""}</p>{document.validation_notes ? <p className="mt-1 text-xs text-muted-foreground">{document.validation_notes}</p> : null}</div><div className="flex flex-wrap gap-2"><Button type="button" size="icon" variant="ghost" aria-label={`Download ${document.filename}`} onClick={() => void download(document.id, document.filename)}><Download className="h-4 w-4" aria-hidden="true" /></Button>{can("profiles:validate_documents") && document.validation_status === "pending" ? <><Button type="button" size="sm" onClick={() => void validate(document.id, "verified")}>Verify</Button><Button type="button" size="sm" variant="outline" className="text-destructive" onClick={() => void validate(document.id, "rejected")}>Reject</Button></> : <Badge className="capitalize">{document.validation_status}</Badge>}</div></li>)}</ul> : <div className="mt-4"><EmptyState title="No documents" description="This trainee has not uploaded profile documents." /></div>}</section>
      <section><h2 className="text-lg font-semibold">Learning history</h2>{profile.enrollments.length ? <div className="mt-4 space-y-3">{profile.enrollments.map((item) => <article key={item.id} className="rounded-md border bg-card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs text-muted-foreground">{item.programme_code}</p><h3 className="mt-1 font-semibold">{item.programme_title}</h3></div><Badge className="capitalize">{item.status}</Badge></div><div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground"><span>{item.attendance.length} attendance records</span><span>{item.assessments.length} assessments</span><span>{item.certificates.length} certificates</span></div>{item.certificates.map((certificate) => <p key={certificate.id} className="mt-3 flex items-center gap-2 text-sm"><Award className="h-4 w-4 text-primary" aria-hidden="true" />{certificate.title} · {certificate.certificate_number}</p>)}</article>)}</div> : <div className="mt-4"><EmptyState title="No learning history" description="Approved enrolments will appear here." /></div>}</section>
      <section><h2 className="flex items-center gap-2 text-lg font-semibold"><History className="h-5 w-5 text-primary" aria-hidden="true" />Audit history</h2>{profile.audit_history.length ? <ol className="mt-4 divide-y rounded-md border bg-card">{profile.audit_history.map((event) => <li key={event.id} className="flex flex-col gap-1 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-medium capitalize">{event.event_type.replace("profile.", "").replace(/_/g, " ")}</p><p className="text-xs text-muted-foreground">{event.actor_name}</p></div><time className="text-xs text-muted-foreground">{formatDate(event.created_at)}</time></li>)}</ol> : <div className="mt-4"><EmptyState icon={FileCheck2} title="No audit events" description="Profile activity will be recorded here." /></div>}</section>
    </div> : null}
  </AppShell>;
}

function Info({ label, value, className }: { label: string; value: string; className?: string }) { return <div className={className}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 text-sm">{value}</dd></div>; }
function SimpleList({ title, items }: { title: string; items: Array<{ title: string; detail: string }> }) { return <div className="rounded-md border bg-card p-5"><h3 className="font-semibold">{title}</h3>{items.length ? <ul className="mt-3 divide-y">{items.map((item, index) => <li key={`${item.title}-${index}`} className="py-3"><p className="text-sm font-medium">{item.title}</p><p className="mt-1 text-xs text-muted-foreground">{item.detail}</p></li>)}</ul> : <p className="mt-3 text-sm text-muted-foreground">No records.</p>}</div>; }
