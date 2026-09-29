import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  Award,
  BookOpenCheck,
  BriefcaseBusiness,
  Download,
  FileCheck2,
  FileUp,
  GraduationCap,
  History,
  Save,
  ShieldCheck,
  Trash2,
  UsersRound,
} from "lucide-react";

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
  type EducationRecord,
  type EmploymentRecord,
  type MembershipRecord,
  type AccountDeletionRequest,
  type ProfileDocumentType,
  type TraineeProfile,
} from "../lib/api/client";

const fieldClass =
  "h-11 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary";
const textareaClass =
  "min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary";

function formatDate(value: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function labelForEvent(value: string) {
  return value.replace("profile.", "").replace(/_/g, " ");
}

export function ProfilePage() {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState<TraineeProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deletionRequest, setDeletionRequest] = useState<AccountDeletionRequest | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [profileResult, deletionResult] = await Promise.all([
        apiClient.myProfile(),
        apiClient.accountDeletionRequest().catch(() => null),
      ]);
      setProfile(profileResult);
      setDeletionRequest(deletionResult);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load your profile.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user) return null;

  const runUpdate = async (action: () => Promise<TraineeProfile>, message: string) => {
    setIsSaving(true);
    setError(null);
    try {
      setProfile(await action());
      setNotice(message);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to update your profile.");
    } finally {
      setIsSaving(false);
    }
  };

  const savePersonal = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const optional = (name: string) => String(data.get(name) ?? "").trim() || null;
    void runUpdate(
      () =>
        apiClient.updateMyProfile({
          full_name: optional("full_name"),
          phone: optional("phone"),
          designation: optional("designation"),
          date_of_birth: optional("date_of_birth"),
          gender: optional("gender"),
          alternate_email: optional("alternate_email"),
          address_line: optional("address_line"),
          city: optional("city"),
          state: optional("state"),
          postal_code: optional("postal_code"),
          preferred_language: optional("preferred_language"),
          preferred_location: optional("preferred_location"),
          career_interests: optional("career_interests"),
          skills: String(data.get("skills") ?? "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      "Personal details saved.",
    );
  };

  const addEducation = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const year = String(data.get("completion_year") ?? "");
    const payload: Omit<EducationRecord, "id"> = {
      qualification: String(data.get("qualification")),
      field_of_study: String(data.get("field_of_study") ?? "") || null,
      institution_name: String(data.get("institution_name")),
      completion_year: year ? Number(year) : null,
      grade: String(data.get("grade") ?? "") || null,
      is_highest_qualification: data.get("is_highest_qualification") === "on",
    };
    void runUpdate(() => apiClient.addEducation(payload), "Education record added.").then(() =>
      form.reset(),
    );
  };

  const addEmployment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const isCurrent = data.get("is_current") === "on";
    const payload: Omit<EmploymentRecord, "id"> = {
      employer_name: String(data.get("employer_name")),
      job_title: String(data.get("job_title")),
      start_date: String(data.get("start_date")),
      end_date: isCurrent ? null : String(data.get("end_date") ?? "") || null,
      is_current: isCurrent,
      responsibilities: String(data.get("responsibilities") ?? "") || null,
    };
    void runUpdate(() => apiClient.addEmployment(payload), "Employment record added.").then(() =>
      form.reset(),
    );
  };

  const addMembership = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload: Omit<MembershipRecord, "id"> = {
      institution_name: String(data.get("institution_name")),
      membership_type: String(data.get("membership_type")),
      member_number: String(data.get("member_number") ?? "") || null,
      joined_on: String(data.get("joined_on") ?? "") || null,
      is_active: true,
    };
    void runUpdate(() => apiClient.addMembership(payload), "Membership added.").then(() =>
      form.reset(),
    );
  };

  const uploadDocument = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get("document");
    if (!(file instanceof File) || file.size === 0) return;
    void runUpdate(
      () =>
        apiClient.uploadProfileDocument(
          String(data.get("document_type")) as ProfileDocumentType,
          file,
        ),
      "Document uploaded for validation.",
    ).then(() => form.reset());
  };

  const download = async (id: string, filename: string) => {
    try {
      const blob = await apiClient.downloadProfileDocument(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to download this document.");
    }
  };

  const requestDeletion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setIsSaving(true);
    setError(null);
    try {
      const result = await apiClient.requestAccountDeletion({
        current_password: String(data.get("current_password")),
        reason: String(data.get("reason") ?? "").trim() || undefined,
        acknowledge_retention: data.get("acknowledge_retention") === "on",
      });
      setDeletionRequest(result);
      setNotice("Account deletion request submitted.");
      form.reset();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to request account deletion.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-primary">Private trainee record</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">My profile</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Keep your training, cooperative experience and consent choices current.
          </p>
        </div>
        {profile ? (
          <div className="w-full max-w-xs rounded-md border bg-card p-4" aria-label="Profile completion">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Profile completion</span>
              <span className="font-semibold text-primary">{profile.completion.percent}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-primary"
                style={{ width: `${profile.completion.percent}%` }}
              />
            </div>
            {profile.completion.missing_sections.length ? (
              <p className="mt-2 text-xs text-muted-foreground">
                Next: {profile.completion.missing_sections[0]}
              </p>
            ) : (
              <p className="mt-2 text-xs text-emerald-700">All profile sections are complete.</p>
            )}
          </div>
        ) : null}
      </div>

      {notice ? (
        <p className="mt-5 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">
          {notice}
        </p>
      ) : null}
      <div className="mt-6" aria-live="polite">
        {isLoading ? <LoadingState label="Loading your private profile" /> : null}
        {error ? <ErrorState title="Profile action could not be completed" description={error} onRetry={load} /> : null}
      </div>

      {!isLoading && profile ? (
        <div className="mt-7 space-y-10">
          <section aria-labelledby="personal-heading">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
              <div>
                <h2 id="personal-heading" className="text-lg font-semibold">Personal and contact information</h2>
                <p className="text-sm text-muted-foreground">Visible only to you and authorised administrators.</p>
              </div>
            </div>
            <form key={profile.user_id} className="mt-4 grid gap-4 rounded-md border bg-card p-5 sm:grid-cols-2 lg:grid-cols-3" onSubmit={savePersonal}>
              <Field label="Full name"><Input name="full_name" required defaultValue={profile.full_name} /></Field>
              <Field label="Phone"><Input name="phone" inputMode="tel" defaultValue={profile.phone ?? ""} /></Field>
              <Field label="Date of birth"><Input name="date_of_birth" type="date" defaultValue={profile.date_of_birth ?? ""} /></Field>
              <Field label="Gender"><Input name="gender" defaultValue={profile.gender ?? ""} /></Field>
              <Field label="Alternate email"><Input name="alternate_email" type="email" defaultValue={profile.alternate_email ?? ""} /></Field>
              <Field label="Current role"><Input name="designation" defaultValue={profile.designation ?? ""} /></Field>
              <Field label="Address" className="sm:col-span-2"><Input name="address_line" defaultValue={profile.address_line ?? ""} /></Field>
              <Field label="City"><Input name="city" defaultValue={profile.city ?? ""} /></Field>
              <Field label="State"><Input name="state" defaultValue={profile.state ?? ""} /></Field>
              <Field label="Postal code"><Input name="postal_code" defaultValue={profile.postal_code ?? ""} /></Field>
              <Field label="Preferred language"><Input name="preferred_language" defaultValue={profile.preferred_language ?? ""} /></Field>
              <Field label="Preferred location"><Input name="preferred_location" defaultValue={profile.preferred_location ?? ""} /></Field>
              <Field label="Skills (comma separated)" className="sm:col-span-2"><Input name="skills" defaultValue={profile.skills.join(", ")} /></Field>
              <Field label="Career interests" className="sm:col-span-2 lg:col-span-3"><textarea className={textareaClass} name="career_interests" defaultValue={profile.career_interests ?? ""} /></Field>
              <div className="sm:col-span-2 lg:col-span-3"><Button type="submit" disabled={isSaving}><Save className="h-4 w-4" aria-hidden="true" />Save profile</Button></div>
            </form>
          </section>

          <section aria-labelledby="experience-heading">
            <div className="flex items-center gap-3">
              <BriefcaseBusiness className="h-5 w-5 text-primary" aria-hidden="true" />
              <h2 id="experience-heading" className="text-lg font-semibold">Education, work and membership</h2>
            </div>
            <div className="mt-4 grid gap-5 xl:grid-cols-3">
              <RecordGroup title="Education" icon={GraduationCap} items={profile.education.map((item) => ({ id: item.id, title: item.qualification, meta: `${item.institution_name}${item.completion_year ? ` · ${item.completion_year}` : ""}` }))} onDelete={(id) => runUpdate(() => apiClient.deleteEducation(id), "Education record removed.")}>
                <form className="grid gap-3" onSubmit={addEducation}>
                  <Input name="qualification" required placeholder="Qualification" aria-label="Qualification" />
                  <Input name="field_of_study" placeholder="Field of study" aria-label="Field of study" />
                  <Input name="institution_name" required placeholder="Institution" aria-label="Education institution" />
                  <div className="grid grid-cols-2 gap-3"><Input name="completion_year" type="number" min="1900" max="2100" placeholder="Year" aria-label="Completion year" /><Input name="grade" placeholder="Grade" aria-label="Grade" /></div>
                  <label className="flex min-h-11 items-center gap-3 text-sm"><input name="is_highest_qualification" type="checkbox" className="h-5 w-5 accent-primary" />Highest qualification</label>
                  <Button type="submit" variant="outline" disabled={isSaving}>Add education</Button>
                </form>
              </RecordGroup>
              <RecordGroup title="Employment" icon={BriefcaseBusiness} items={profile.employment.map((item) => ({ id: item.id, title: item.job_title, meta: `${item.employer_name} · ${formatDate(item.start_date)}` }))} onDelete={(id) => runUpdate(() => apiClient.deleteEmployment(id), "Employment record removed.")}>
                <form className="grid gap-3" onSubmit={addEmployment}>
                  <Input name="employer_name" required placeholder="Employer" aria-label="Employer" />
                  <Input name="job_title" required placeholder="Role or title" aria-label="Job title" />
                  <div className="grid grid-cols-2 gap-3"><Field label="Start date"><Input name="start_date" required type="date" /></Field><Field label="End date"><Input name="end_date" type="date" /></Field></div>
                  <label className="flex min-h-11 items-center gap-3 text-sm"><input name="is_current" type="checkbox" className="h-5 w-5 accent-primary" />Current employment</label>
                  <textarea className={textareaClass} name="responsibilities" placeholder="Responsibilities" aria-label="Responsibilities" />
                  <Button type="submit" variant="outline" disabled={isSaving}>Add employment</Button>
                </form>
              </RecordGroup>
              <RecordGroup title="Cooperative membership" icon={UsersRound} items={profile.memberships.map((item) => ({ id: item.id, title: item.institution_name, meta: `${item.membership_type}${item.member_number ? ` · ${item.member_number}` : ""}` }))} onDelete={(id) => runUpdate(() => apiClient.deleteMembership(id), "Membership removed.")}>
                <form className="grid gap-3" onSubmit={addMembership}>
                  <Input name="institution_name" required placeholder="Cooperative institution" aria-label="Cooperative institution" />
                  <Input name="membership_type" required placeholder="Membership type" aria-label="Membership type" />
                  <Input name="member_number" placeholder="Member number" aria-label="Member number" />
                  <Field label="Joined on"><Input name="joined_on" type="date" /></Field>
                  <Button type="submit" variant="outline" disabled={isSaving}>Add membership</Button>
                </form>
              </RecordGroup>
            </div>
          </section>

          <section aria-labelledby="documents-heading">
            <div className="flex items-center gap-3"><FileCheck2 className="h-5 w-5 text-primary" aria-hidden="true" /><h2 id="documents-heading" className="text-lg font-semibold">Documents</h2></div>
            <form className="mt-4 grid gap-3 rounded-md border bg-card p-5 sm:grid-cols-[200px_1fr_auto]" onSubmit={uploadDocument}>
              <select name="document_type" className={fieldClass} aria-label="Profile document type" defaultValue="identity"><option value="identity">Identity</option><option value="education">Education</option><option value="employment">Employment</option><option value="membership">Membership</option><option value="resume">Resume</option><option value="other">Other</option></select>
              <Input name="document" type="file" required accept="application/pdf,image/jpeg,image/png" aria-label="Choose profile document" />
              <Button type="submit" variant="outline" disabled={isSaving}><FileUp className="h-4 w-4" aria-hidden="true" />Upload</Button>
            </form>
            {profile.documents.length ? (
              <ul className="mt-3 divide-y rounded-md border bg-card">
                {profile.documents.map((document) => (
                  <li key={document.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0"><p className="truncate text-sm font-medium">{document.filename}</p><p className="mt-1 text-xs text-muted-foreground capitalize">{document.document_type} · {Math.ceil(document.size_bytes / 1024)} KB</p>{document.validation_notes ? <p className="mt-1 text-xs text-muted-foreground">{document.validation_notes}</p> : null}</div>
                    <div className="flex items-center gap-2"><StatusBadge value={document.validation_status} /><Button type="button" size="icon" variant="ghost" aria-label={`Download ${document.filename}`} onClick={() => void download(document.id, document.filename)}><Download className="h-4 w-4" aria-hidden="true" /></Button></div>
                  </li>
                ))}
              </ul>
            ) : <div className="mt-3"><EmptyState title="No documents uploaded" description="Upload a PDF, JPEG or PNG when evidence is required." /></div>}
          </section>

          <section aria-labelledby="consent-heading">
            <div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" /><h2 id="consent-heading" className="text-lg font-semibold">Consent preferences</h2></div>
            <form className="mt-4 space-y-2 rounded-md border bg-card p-5" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); void runUpdate(() => apiClient.updateProfileConsents({ placement_visibility_consent: data.get("placement") === "on", communication_consent: data.get("communication") === "on", data_sharing_consent: data.get("data_sharing") === "on" }), "Consent preferences saved."); }}>
              <ConsentToggle name="placement" label="Allow authorised employers to see my placement profile" defaultChecked={profile.consent_preferences.placement_visibility_consent} />
              <ConsentToggle name="communication" label="Receive programme and training communications" defaultChecked={profile.consent_preferences.communication_consent} />
              <ConsentToggle name="data_sharing" label="Allow approved institutional data sharing" defaultChecked={profile.consent_preferences.data_sharing_consent} />
              <Button className="mt-3" type="submit" disabled={isSaving}><Save className="h-4 w-4" aria-hidden="true" />Save preferences</Button>
            </form>
          </section>

          <section aria-labelledby="learning-heading">
            <div className="flex items-center gap-3"><BookOpenCheck className="h-5 w-5 text-primary" aria-hidden="true" /><h2 id="learning-heading" className="text-lg font-semibold">Programme history</h2></div>
            {profile.enrollments.length ? <div className="mt-4 space-y-4">{profile.enrollments.map((enrollment) => <article key={enrollment.id} className="rounded-md border bg-card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium text-muted-foreground">{enrollment.programme_code}{enrollment.batch_name ? ` · ${enrollment.batch_name}` : ""}</p><h3 className="mt-1 font-semibold">{enrollment.programme_title}</h3></div><StatusBadge value={enrollment.status} /></div><div className="mt-4 grid gap-4 text-sm md:grid-cols-3"><HistoryStat icon={History} label="Attendance" value={enrollment.attendance.length ? `${enrollment.attendance.filter((item) => item.status === "present").length} of ${enrollment.attendance.length} present` : "Not recorded"} /><HistoryStat icon={Award} label="Assessments" value={enrollment.assessments.length ? enrollment.assessments.map((item) => `${item.title}: ${item.result}`).join(", ") : "Not recorded"} /><HistoryStat icon={FileCheck2} label="Certificates" value={enrollment.certificates.length ? enrollment.certificates.map((item) => item.certificate_number).join(", ") : "Not issued"} /></div></article>)}</div> : <div className="mt-4"><EmptyState title="No programme history" description="Approved enrolments and completed learning will appear here." /></div>}
          </section>

          <section aria-labelledby="audit-heading">
            <div className="flex items-center gap-3"><History className="h-5 w-5 text-primary" aria-hidden="true" /><h2 id="audit-heading" className="text-lg font-semibold">Audit history</h2></div>
            {profile.audit_history.length ? <ol className="mt-4 divide-y rounded-md border bg-card">{profile.audit_history.map((event) => <li key={event.id} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-medium capitalize">{labelForEvent(event.event_type)}</p><p className="text-xs text-muted-foreground">By {event.actor_name}</p></div><time className="text-xs text-muted-foreground" dateTime={event.created_at}>{formatDate(event.created_at)}</time></li>)}</ol> : <div className="mt-4"><EmptyState title="No profile activity yet" description="Profile changes and administrative reviews will be recorded here." /></div>}
          </section>

          <section className="border-t pt-8" aria-labelledby="data-rights-heading">
            <div className="flex items-center gap-3"><Trash2 className="h-5 w-5 text-destructive" aria-hidden="true" /><h2 id="data-rights-heading" className="text-lg font-semibold">Account and data deletion</h2></div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              A request starts a cooling period. Private profile data is erased after NCCT review;
              statutory training, certificate and audit records may be retained in de-identified form.
            </p>
            {deletionRequest?.status === "pending" ? (
              <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-5 text-amber-950">
                <p className="font-semibold">Deletion scheduled for {formatDate(deletionRequest.scheduled_for)}</p>
                <p className="mt-1 text-sm">You can cancel this request before an NCCT administrator completes it.</p>
                <Button className="mt-4" type="button" variant="outline" disabled={isSaving} onClick={() => void apiClient.cancelAccountDeletion(deletionRequest.id).then((result) => { setDeletionRequest(result); setNotice("Account deletion request cancelled."); }).catch((caught) => setError(caught instanceof ApiError ? caught.message : "Unable to cancel the request."))}>Cancel deletion request</Button>
              </div>
            ) : (
              <details className="mt-4 rounded-md border bg-card p-5">
                <summary className="cursor-pointer font-medium text-destructive">Request account deletion</summary>
                <form className="mt-5 max-w-xl space-y-4" onSubmit={requestDeletion}>
                  <Field label="Current password"><Input name="current_password" type="password" autoComplete="current-password" required /></Field>
                  <Field label="Reason, optional"><textarea className={textareaClass} name="reason" maxLength={1000} /></Field>
                  <label className="flex min-h-12 items-start gap-3 rounded-md border p-3 text-sm leading-5"><input className="mt-0.5 h-5 w-5 shrink-0 accent-primary" name="acknowledge_retention" type="checkbox" required />I understand that legally required training, certificate and security audit records may be retained after personal details are removed.</label>
                  <Button type="submit" variant="destructive" disabled={isSaving}><Trash2 className="h-4 w-4" aria-hidden="true" />Submit deletion request</Button>
                </form>
              </details>
            )}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}

function Field({ label, className, children }: { label: string; className?: string; children: React.ReactNode }) {
  return <label className={className}><span className="mb-1.5 block text-sm font-medium">{label}</span>{children}</label>;
}

function RecordGroup({ title, icon: Icon, items, onDelete, children }: { title: string; icon: typeof GraduationCap; items: Array<{ id: string; title: string; meta: string }>; onDelete: (id: string) => Promise<unknown>; children: React.ReactNode }) {
  return <div className="rounded-md border bg-card p-5"><div className="flex items-center gap-2"><Icon className="h-5 w-5 text-primary" aria-hidden="true" /><h3 className="font-semibold">{title}</h3></div>{items.length ? <ul className="my-4 divide-y border-y">{items.map((item) => <li key={item.id} className="flex items-center justify-between gap-3 py-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{item.title}</p><p className="truncate text-xs text-muted-foreground">{item.meta}</p></div><Button type="button" size="icon" variant="ghost" aria-label={`Delete ${item.title}`} onClick={() => void onDelete(item.id)}><Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" /></Button></li>)}</ul> : <p className="my-4 text-sm text-muted-foreground">No records added.</p>}<details><summary className="cursor-pointer py-2 text-sm font-medium text-primary">Add {title.toLowerCase()}</summary><div className="mt-3">{children}</div></details></div>;
}

function ConsentToggle({ name, label, defaultChecked }: { name: string; label: string; defaultChecked: boolean }) {
  return <label className="flex min-h-12 items-center gap-3 rounded-md px-2 text-sm hover:bg-muted"><input name={name} type="checkbox" defaultChecked={defaultChecked} className="h-5 w-5 shrink-0 accent-primary" />{label}</label>;
}

function StatusBadge({ value }: { value: string }) {
  const tone = value === "verified" || value === "completed" ? "bg-emerald-100 text-emerald-800" : value === "rejected" || value === "withdrawn" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-900";
  return <Badge className={`${tone} capitalize`}>{value.replace(/_/g, " ")}</Badge>;
}

function HistoryStat({ icon: Icon, label, value }: { icon: typeof History; label: string; value: string }) {
  return <div className="flex gap-3"><Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" /><div><p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-1 capitalize">{value}</p></div></div>;
}
