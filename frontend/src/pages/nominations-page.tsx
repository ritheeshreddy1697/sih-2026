import { useCallback, useEffect, useState } from "react";
import { Download, FileUp, Mail } from "lucide-react";
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
  type ProgrammeNomination,
} from "../lib/api/client";

export function NominationsPage() {
  const { user, logout, can } = useAuth();
  const [searchParams] = useSearchParams();
  const programmeId = searchParams.get("programme_id") ?? undefined;
  const [nominations, setNominations] = useState<ProgrammeNomination[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setNominations(await apiClient.nominations(programmeId));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load nominations.");
    } finally {
      setIsLoading(false);
    }
  }, [programmeId]);

  useEffect(() => { void load(); }, [load]);
  if (!user) return null;

  const review = async (id: string, status: ApplicationStatus) => {
    try {
      await apiClient.reviewNomination(id, status);
      setNotice(`Nomination marked ${status.replace("_", " ")}.`);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to update this nomination.");
    }
  };

  const upload = async (id: string, type: DocumentType, file: File) => {
    try {
      await apiClient.uploadNominationDocument(id, type, file);
      setNotice("Nomination document uploaded.");
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
      <p className="text-sm font-semibold text-primary">Candidate pipeline</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Nominations</h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">Track PACS, SHG and cooperative-institution nominees through the review process.</p>
      {programmeId ? <div className="mt-5"><Button asChild variant="outline" size="sm"><Link to={`/programmes/${programmeId}`}>Back to programme</Link></Button></div> : null}
      {notice ? <p className="mt-5 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p> : null}
      <div className="mt-6" aria-live="polite">
        {isLoading ? <LoadingState label="Loading nominations" /> : null}
        {error ? <ErrorState title="Nominations could not be loaded" description={error} onRetry={load} /> : null}
        {!isLoading && !error && nominations.length === 0 ? <EmptyState title="No nominations yet" description="Eligible nominations submitted individually or by CSV will appear here." /> : null}
        {!isLoading && !error && nominations.length ? (
          <div className="overflow-x-auto rounded-lg border bg-card">
            <table className="min-w-[760px] w-full text-left text-sm">
              <thead className="border-b bg-muted/60 text-xs text-muted-foreground"><tr><th className="px-4 py-3 font-medium">Candidate</th><th className="px-4 py-3 font-medium">Programme</th><th className="px-4 py-3 font-medium">Type</th><th className="px-4 py-3 font-medium">Source</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Actions</th></tr></thead>
              <tbody className="divide-y">
                {nominations.map((nomination) => (
                  <tr key={nomination.id} className="align-top">
                    <td className="px-4 py-4"><p className="font-medium">{nomination.candidate_full_name}</p><p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"><Mail className="h-3.5 w-3.5" aria-hidden="true" />{nomination.candidate_email}</p>{nomination.documents.map((item) => <Button key={item.id} type="button" variant="ghost" size="sm" className="mt-2 -ml-3" onClick={() => void download(item.id, item.filename)}><Download className="h-4 w-4" aria-hidden="true" />{item.filename}</Button>)}</td>
                    <td className="px-4 py-4"><p>{nomination.programme_title}</p><p className="mt-1 text-xs text-muted-foreground">{nomination.programme_code}</p></td>
                    <td className="px-4 py-4 capitalize">{nomination.nomination_type.replace("_", " ")}</td>
                    <td className="px-4 py-4">{nomination.source === "bulk_csv" ? "CSV upload" : "Individual"}</td>
                    <td className="px-4 py-4"><StatusBadge status={nomination.status} /></td>
                    <td className="px-4 py-4">
                      {can("applications:review") ? <div className="flex flex-wrap gap-1"><Button size="sm" variant="outline" onClick={() => void review(nomination.id, "approved")}>Approve</Button><Button size="sm" variant="outline" onClick={() => void review(nomination.id, "waitlisted")}>Wait-list</Button><Button size="sm" variant="ghost" className="text-destructive" onClick={() => void review(nomination.id, "rejected")}>Reject</Button></div> : <NominationDocumentUpload nominationId={nomination.id} onUpload={upload} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}

function NominationDocumentUpload({ nominationId, onUpload }: { nominationId: string; onUpload: (id: string, type: DocumentType, file: File) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  return <div className="flex min-w-64 gap-2"><Input type="file" aria-label="Nomination letter" accept="application/pdf,image/jpeg,image/png" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><Button size="icon" variant="outline" disabled={!file} aria-label="Upload nomination letter" onClick={() => { if (file) void onUpload(nominationId, "nomination_letter", file); }}><FileUp className="h-4 w-4" aria-hidden="true" /></Button></div>;
}
