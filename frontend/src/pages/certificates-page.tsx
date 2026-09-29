import {
  Award,
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  FileBadge,
  Send,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

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
  type CertificateCandidate,
  type CertificatePolicy,
  type CertificateState,
  type DigitalCertificate,
  type Programme,
  type SkillWallet,
} from "../lib/api/client";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function errorMessage(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

function formatDate(value: string | null) {
  if (!value) return "No expiry";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value));
}

function stateStyle(state: CertificateState) {
  if (state === "valid") return "bg-emerald-100 text-emerald-800";
  if (state === "revoked") return "bg-red-100 text-red-800";
  return "bg-amber-100 text-amber-900";
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{Math.round(value)}%</p>
    </div>
  );
}

async function saveCertificate(certificate: DigitalCertificate) {
  const blob = await apiClient.downloadCertificate(certificate.id);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${certificate.certificate_number}.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function WalletView() {
  const [wallet, setWallet] = useState<SkillWallet | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setWallet(await apiClient.skillWallet());
    } catch (caught) {
      setError(errorMessage(caught, "Your skill wallet is unavailable."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => void load(), [load]);

  const share = async (certificate: DigitalCertificate) => {
    setMessage(null);
    const shareData = {
      title: certificate.title,
      text: `${certificate.recipient_name} - ${certificate.programme_title}`,
      url: certificate.verification_url,
    };
    try {
      if (navigator.share) await navigator.share(shareData);
      else {
        await navigator.clipboard.writeText(certificate.verification_url);
        setMessage("Verification link copied.");
      }
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      setMessage("The verification link could not be shared.");
    }
  };

  const download = async (certificate: DigitalCertificate) => {
    setMessage(null);
    try {
      await saveCertificate(certificate);
    } catch (caught) {
      setMessage(errorMessage(caught, "The certificate PDF could not be downloaded."));
    }
  };

  if (isLoading) return <LoadingState label="Loading your skill wallet" />;
  if (error) {
    return <ErrorState title="Skill wallet unavailable" description={error} onRetry={load} />;
  }
  if (!wallet?.certificates.length) {
    return (
      <EmptyState
        icon={Award}
        title="No certificates issued yet"
        description="Eligible certificates will appear here after an administrator issues them."
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="border-l-4 border-l-primary bg-card px-5 py-4 shadow-sm">
          <p className="text-sm text-muted-foreground">Certificates</p>
          <p className="mt-1 text-2xl font-semibold">{wallet.total}</p>
        </div>
        <div className="border-l-4 border-l-emerald-600 bg-card px-5 py-4 shadow-sm">
          <p className="text-sm text-muted-foreground">Currently valid</p>
          <p className="mt-1 text-2xl font-semibold">{wallet.valid_count}</p>
        </div>
      </div>
      {message ? (
        <p className="border-l-4 border-l-sky-500 bg-sky-50 p-3 text-sm text-sky-950" role="status">
          {message}
        </p>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {wallet.certificates.map((certificate) => (
          <article key={certificate.id} className="rounded-lg border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">
                <FileBadge className="h-6 w-6" aria-hidden="true" />
              </span>
              <Badge className={stateStyle(certificate.state)}>{certificate.state}</Badge>
            </div>
            <h2 className="mt-4 text-lg font-semibold">{certificate.title}</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {certificate.programme_title} · {certificate.institution_name}
            </p>
            <p className="mt-3 font-mono text-xs text-muted-foreground">
              {certificate.certificate_number}
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-3 border-y py-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Issued</dt>
                <dd className="mt-1 font-medium">{formatDate(certificate.issued_at)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Valid until</dt>
                <dd className="mt-1 font-medium">{formatDate(certificate.expires_at)}</dd>
              </div>
            </dl>
            {certificate.revocation_reason ? (
              <p className="mt-4 rounded-md bg-red-50 p-3 text-sm leading-6 text-red-900">
                {certificate.revocation_reason}
              </p>
            ) : null}
            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void download(certificate)}>
                <Download className="h-4 w-4" aria-hidden="true" />
                Download PDF
              </Button>
              <Button variant="outline" onClick={() => void share(certificate)}>
                <Send className="h-4 w-4" aria-hidden="true" />
                Share
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Copy verification link for ${certificate.title}`}
                title="Copy verification link"
                onClick={() => {
                  void navigator.clipboard.writeText(certificate.verification_url).then(() => {
                    setMessage("Verification link copied.");
                  });
                }}
              >
                <Copy className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button asChild variant="ghost" size="icon">
                <a
                  href={certificate.verification_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Open public verification for ${certificate.title}`}
                  title="Open public verification"
                >
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                </a>
              </Button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdministrationView() {
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [programmeId, setProgrammeId] = useState("");
  const [policy, setPolicy] = useState<CertificatePolicy | null>(null);
  const [candidates, setCandidates] = useState<CertificateCandidate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isProgrammeLoading, setIsProgrammeLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const programmeRequestId = useRef(0);

  useEffect(() => {
    let active = true;
    void apiClient
      .programmes()
      .then(({ items }) => {
        if (!active) return;
        setProgrammes(items);
        setProgrammeId((current) => current || items[0]?.id || "");
      })
      .catch((caught) => {
        if (active) setError(errorMessage(caught, "Programmes could not be loaded."));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const loadProgramme = useCallback(async () => {
    if (!programmeId) return;
    const requestId = ++programmeRequestId.current;
    setIsProgrammeLoading(true);
    setError(null);
    try {
      const policyItem = await apiClient.certificatePolicy(programmeId);
      if (requestId !== programmeRequestId.current) return;
      setPolicy(policyItem);
      const candidateItems = policyItem ? await apiClient.certificateCandidates(programmeId) : [];
      if (requestId !== programmeRequestId.current) return;
      setCandidates(candidateItems);
    } catch (caught) {
      if (requestId === programmeRequestId.current) {
        setError(errorMessage(caught, "Certificate information could not be loaded."));
      }
    } finally {
      if (requestId === programmeRequestId.current) setIsProgrammeLoading(false);
    }
  }, [programmeId]);

  useEffect(() => void loadProgramme(), [loadProgramme]);

  const configurePolicy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setMessage(null);
    try {
      await apiClient.configureCertificatePolicy(programmeId, {
        certificate_title: String(form.get("certificate_title")),
        minimum_course_completion_percent: Number(form.get("course_completion")),
        minimum_attendance_percent: Number(form.get("attendance")),
        minimum_assessment_score_percent: Number(form.get("assessment")),
        validity_days: form.get("validity_days") ? Number(form.get("validity_days")) : null,
        is_active: form.get("is_active") === "on",
      });
      await loadProgramme();
      setMessage("Certificate policy saved.");
    } catch (caught) {
      setMessage(errorMessage(caught, "Certificate policy could not be saved."));
    }
  };

  const issue = async (enrollmentId: string) => {
    setMessage(null);
    try {
      await apiClient.issueCertificate(enrollmentId);
      await loadProgramme();
      setMessage("Certificate issued and added to the trainee's wallet.");
    } catch (caught) {
      setMessage(errorMessage(caught, "Certificate could not be issued."));
    }
  };

  const download = async (certificate: DigitalCertificate) => {
    setMessage(null);
    try {
      await saveCertificate(certificate);
    } catch (caught) {
      setMessage(errorMessage(caught, "The certificate PDF could not be downloaded."));
    }
  };

  const revoke = async (event: FormEvent<HTMLFormElement>, certificateId: string) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await apiClient.revokeCertificate(certificateId, String(form.get("reason")));
      setRevokingId(null);
      await loadProgramme();
      setMessage("Certificate revoked. Public verification now shows it as invalid.");
    } catch (caught) {
      setMessage(errorMessage(caught, "Certificate could not be revoked."));
    }
  };

  const selectedProgramme = useMemo(
    () => programmes.find((programme) => programme.id === programmeId),
    [programmeId, programmes],
  );

  if (isLoading) return <LoadingState label="Loading certificate administration" />;
  if (error && !programmes.length) {
    return <ErrorState title="Certificates unavailable" description={error} />;
  }
  if (!programmes.length) {
    return (
      <EmptyState
        icon={Award}
        title="No programmes available"
        description="A programme is required before a certificate policy can be configured."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="max-w-xl">
        <label className="text-sm font-medium" htmlFor="certificate-programme">
          Programme
        </label>
        <select
          id="certificate-programme"
          className={`${fieldClass} mt-2`}
          value={programmeId}
          onChange={(event) => setProgrammeId(event.target.value)}
        >
          {programmes.map((programme) => (
            <option value={programme.id} key={programme.id}>
              {programme.title} ({programme.code})
            </option>
          ))}
        </select>
      </div>

      {message ? (
        <p className="border-l-4 border-l-sky-500 bg-sky-50 p-3 text-sm text-sky-950" role="status">
          {message}
        </p>
      ) : null}
      {error ? <ErrorState title="Unable to load programme" description={error} onRetry={loadProgramme} /> : null}
      {isProgrammeLoading ? <LoadingState label="Checking certificate eligibility" /> : null}

      {!isProgrammeLoading ? (
        <section className="border-t pt-6" aria-labelledby="policy-heading">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 id="policy-heading" className="text-lg font-semibold">Eligibility policy</h2>
              <p className="mt-1 text-sm text-muted-foreground">{selectedProgramme?.institution.name}</p>
            </div>
            {policy ? (
              <Badge className={policy.is_active ? "bg-emerald-100 text-emerald-800" : "bg-muted"}>
                {policy.is_active ? "Active" : "Paused"}
              </Badge>
            ) : null}
          </div>
          <form
            key={policy?.id ?? programmeId}
            className="grid gap-4 md:grid-cols-2 xl:grid-cols-5"
            onSubmit={configurePolicy}
          >
            <label className="text-sm font-medium md:col-span-2 xl:col-span-1">
              Certificate title
              <Input
                className="mt-2"
                name="certificate_title"
                defaultValue={policy?.certificate_title ?? "Certificate of Completion"}
                minLength={3}
                required
              />
            </label>
            <label className="text-sm font-medium">
              Course completion (%)
              <Input className="mt-2" name="course_completion" type="number" min="0" max="100" defaultValue={policy?.minimum_course_completion_percent ?? 100} required />
            </label>
            <label className="text-sm font-medium">
              Attendance (%)
              <Input className="mt-2" name="attendance" type="number" min="0" max="100" defaultValue={policy?.minimum_attendance_percent ?? 75} required />
            </label>
            <label className="text-sm font-medium">
              Assessment score (%)
              <Input className="mt-2" name="assessment" type="number" min="0" max="100" defaultValue={policy?.minimum_assessment_score_percent ?? 60} required />
            </label>
            <label className="text-sm font-medium">
              Validity (days)
              <Input className="mt-2" name="validity_days" type="number" min="1" max="36500" defaultValue={policy?.validity_days ?? ""} placeholder="No expiry" />
            </label>
            <label className="flex min-h-11 items-center gap-3 text-sm font-medium md:col-span-2">
              <input name="is_active" type="checkbox" defaultChecked={policy?.is_active ?? true} className="h-5 w-5 accent-primary" />
              Allow certificate issuance
            </label>
            <div className="md:col-span-2 xl:col-span-3 xl:text-right">
              <Button type="submit">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                Save policy
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {!isProgrammeLoading && policy ? (
        <section className="border-t pt-6" aria-labelledby="candidate-heading">
          <div className="mb-4">
            <h2 id="candidate-heading" className="text-lg font-semibold">Trainee eligibility</h2>
            <p className="mt-1 text-sm text-muted-foreground">{candidates.length} enrolled trainee{candidates.length === 1 ? "" : "s"}</p>
          </div>
          {!candidates.length ? (
            <EmptyState title="No enrolled trainees" description="No certificate candidates are available for this programme." />
          ) : (
            <div className="space-y-3">
              {candidates.map((candidate) => (
                <article key={candidate.enrollment_id} className="rounded-lg border bg-card p-4 shadow-sm">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold">{candidate.trainee_name}</h3>
                        <Badge className={candidate.eligible ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}>
                          {candidate.eligible ? "Eligible" : "Not eligible"}
                        </Badge>
                        {candidate.certificate ? <Badge className={stateStyle(candidate.certificate.state)}>{candidate.certificate.state}</Badge> : null}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{candidate.trainee_email}</p>
                      <div className="mt-4 grid grid-cols-3 gap-4">
                        <Metric label="Course" value={candidate.metrics.course_completion_percent} />
                        <Metric label="Attendance" value={candidate.metrics.attendance_percent} />
                        <Metric label="Assessment" value={candidate.metrics.assessment_score_percent} />
                      </div>
                      {candidate.reasons.length ? (
                        <ul className="mt-4 space-y-1 text-sm text-amber-900">
                          {candidate.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                        </ul>
                      ) : null}
                    </div>
                    <div className="flex min-w-[220px] flex-wrap gap-2 xl:justify-end">
                      {!candidate.certificate ? (
                        <Button disabled={!candidate.eligible} onClick={() => void issue(candidate.enrollment_id)}>
                          <Award className="h-4 w-4" aria-hidden="true" />
                          Issue certificate
                        </Button>
                      ) : (
                        <>
                          <Button variant="outline" onClick={() => void download(candidate.certificate!)}>
                            <Download className="h-4 w-4" aria-hidden="true" />
                            PDF
                          </Button>
                          {candidate.certificate.state !== "revoked" ? (
                            <Button variant="destructive" onClick={() => setRevokingId(candidate.certificate!.id)}>
                              <ShieldX className="h-4 w-4" aria-hidden="true" />
                              Revoke
                            </Button>
                          ) : null}
                        </>
                      )}
                    </div>
                  </div>
                  {candidate.certificate && revokingId === candidate.certificate.id ? (
                    <form className="mt-4 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-end" onSubmit={(event) => void revoke(event, candidate.certificate!.id)}>
                      <label className="flex-1 text-sm font-medium">
                        Revocation reason
                        <Input className="mt-2" name="reason" minLength={5} maxLength={1000} required />
                      </label>
                      <Button type="submit" variant="destructive">Confirm revocation</Button>
                      <Button type="button" variant="ghost" onClick={() => setRevokingId(null)}>Cancel</Button>
                    </form>
                  ) : null}
                  {candidate.certificate?.audit_history.length ? (
                    <p className="mt-4 border-t pt-3 text-xs text-muted-foreground">
                      Last event: {candidate.certificate.audit_history[0].event_type.replace("certificate.", "")} by {candidate.certificate.audit_history[0].actor_name ?? "System"} on {formatDate(candidate.certificate.audit_history[0].created_at)}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

export function CertificatesPage() {
  const { user, logout, can } = useAuth();
  if (!user) return null;
  const isAdministrator = can("certificates:manage");

  return (
    <AppShell user={user} onLogout={logout}>
      <div className="space-y-6">
        <header className="flex flex-col gap-3 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Badge className={isAdministrator ? "bg-sky-100 text-sky-800" : "bg-emerald-100 text-emerald-800"}>
              {isAdministrator ? "Administrator workspace" : "Trainee wallet"}
            </Badge>
            <h1 className="mt-3 text-2xl font-semibold sm:text-3xl">
              {isAdministrator ? "Certificate administration" : "Digital skill wallet"}
            </h1>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {isAdministrator ? <ShieldAlert className="h-5 w-5" aria-hidden="true" /> : <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />}
            {isAdministrator ? "Controlled issuance" : "Verified achievements"}
          </div>
        </header>
        {isAdministrator ? <AdministrationView /> : <WalletView />}
      </div>
    </AppShell>
  );
}
