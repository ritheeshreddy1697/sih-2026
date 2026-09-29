import { useCallback, useEffect, useState } from "react";
import { Download, FileUp, Mail, UserRound } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

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
  type ApplicationStatus,
  type DocumentType,
  type ProgrammeApplication,
} from "../lib/api/client";

export function ApplicationsPage() {
  const { user, logout, can } = useAuth();
  const [searchParams] = useSearchParams();
  const programmeId = searchParams.get("programme_id") ?? undefined;
  const [applications, setApplications] = useState<ProgrammeApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setApplications(await apiClient.applications(programmeId));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load applications.");
    } finally {
      setIsLoading(false);
    }
  }, [programmeId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user) return null;

  const review = async (applicationId: string, status: ApplicationStatus) => {
    try {
      await apiClient.reviewApplication(applicationId, status);
      setNotice(`Application marked ${status.replace("_", " ")}.`);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to update this application.");
    }
  };

  const upload = async (applicationId: string, type: DocumentType, file: File) => {
    try {
      await apiClient.uploadApplicationDocument(applicationId, type, file);
      setNotice("Document uploaded successfully.");
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to upload the document.");
    }
  };

  const download = async (documentId: string, filename: string) => {
    try {
      const blob = await apiClient.downloadDocument(documentId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to download the document.");
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      <div>
        <p className="text-sm font-semibold text-primary">
          {can("applications:review") ? "Submission review" : "Status tracking"}
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Applications</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {can("applications:review")
            ? "Review trainee eligibility and make a clear admissions decision."
            : "Track decisions and keep supporting documents with each application."}
        </p>
      </div>
      {programmeId ? (
        <div className="mt-5"><Button asChild variant="outline" size="sm"><Link to={`/programmes/${programmeId}`}>Back to programme</Link></Button></div>
      ) : null}
      {notice ? <p className="mt-5 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p> : null}
      <div className="mt-6" aria-live="polite">
        {isLoading ? <LoadingState label="Loading applications" /> : null}
        {error ? <ErrorState title="Applications could not be loaded" description={error} onRetry={load} /> : null}
        {!isLoading && !error && applications.length === 0 ? <EmptyState title="No applications yet" description="Applications will appear here after an eligible trainee submits one." /> : null}
        {!isLoading && !error && applications.length ? (
          <div className="space-y-4">
            {applications.map((application) => (
              <article key={application.id} className="rounded-lg border bg-card p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">{application.programme_code}</p>
                    <h2 className="mt-1 text-base font-semibold">{application.programme_title}</h2>
                    {can("applications:review") ? (
                      <div className="mt-3 space-y-1 text-sm text-muted-foreground">
                        <p className="flex items-center gap-2"><UserRound className="h-4 w-4" aria-hidden="true" />{application.trainee_name}</p>
                        <p className="flex items-center gap-2"><Mail className="h-4 w-4" aria-hidden="true" />{application.trainee_email}</p>
                      </div>
                    ) : null}
                  </div>
                  <StatusBadge status={application.status} />
                </div>
                {application.statement ? <p className="mt-4 border-l-2 pl-4 text-sm leading-6 text-muted-foreground">{application.statement}</p> : null}
                {application.review_notes ? <p className="mt-4 rounded-md bg-muted p-3 text-sm"><span className="font-medium">Review note:</span> {application.review_notes}</p> : null}
                <div className="mt-4 border-t pt-4">
                  <p className="text-xs font-medium text-muted-foreground">Documents</p>
                  {application.documents.length ? <ul className="mt-2 space-y-1 text-sm">{application.documents.map((item) => <li key={item.id} className="flex items-center justify-between gap-3"><span>{item.filename} · {Math.ceil(item.size_bytes / 1024)} KB</span><Button type="button" size="icon" variant="ghost" aria-label={`Download ${item.filename}`} onClick={() => void download(item.id, item.filename)}><Download className="h-4 w-4" aria-hidden="true" /></Button></li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">No documents uploaded.</p>}
                  {!can("applications:review") ? <DocumentUpload applicationId={application.id} onUpload={upload} /> : null}
                </div>
                {can("applications:review") ? (
                  <div className="mt-4 flex flex-wrap gap-2 border-t pt-4" aria-label={`Review ${application.trainee_name}`}>
                    <Button size="sm" variant="outline" onClick={() => void review(application.id, "under_review")}>Start review</Button>
                    <Button size="sm" onClick={() => void review(application.id, "approved")}>Approve</Button>
                    <Button size="sm" variant="outline" onClick={() => void review(application.id, "waitlisted")}>Wait-list</Button>
                    <Button size="sm" variant="outline" className="text-destructive" onClick={() => void review(application.id, "rejected")}>Reject</Button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}

function DocumentUpload({ applicationId, onUpload }: { applicationId: string; onUpload: (applicationId: string, type: DocumentType, file: File) => Promise<void> }) {
  const [type, setType] = useState<DocumentType>("eligibility");
  const [file, setFile] = useState<File | null>(null);
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-[160px_1fr_auto]">
      <select className="h-11 rounded-md border bg-card px-3 text-sm" aria-label="Document type" value={type} onChange={(event) => setType(event.target.value as DocumentType)}><option value="eligibility">Eligibility proof</option><option value="identity">Identity document</option><option value="other">Other</option></select>
      <Input type="file" aria-label="Application document" accept="application/pdf,image/jpeg,image/png" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      <Button type="button" variant="outline" disabled={!file} onClick={() => { if (file) void onUpload(applicationId, type, file); }}><FileUp className="h-4 w-4" aria-hidden="true" />Upload</Button>
    </div>
  );
}
