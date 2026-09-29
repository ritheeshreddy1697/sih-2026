import { Award, CalendarDays, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { ApiError, apiClient, type CertificateVerification } from "../lib/api/client";
import { cn } from "../lib/utils";

function formatDate(value: string | null) {
  if (!value) return "No expiry";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "long" }).format(new Date(value));
}

const statePresentation = {
  valid: {
    title: "Valid certificate",
    description: "This certificate is currently valid in the NCCT training records.",
    icon: ShieldCheck,
    panel: "border-emerald-300 bg-emerald-50 text-emerald-950",
    badge: "bg-emerald-700 text-white",
  },
  revoked: {
    title: "Revoked certificate",
    description: "This certificate is no longer valid.",
    icon: ShieldX,
    panel: "border-red-300 bg-red-50 text-red-950",
    badge: "bg-red-700 text-white",
  },
  expired: {
    title: "Expired certificate",
    description: "This certificate has passed its validity date.",
    icon: ShieldAlert,
    panel: "border-amber-300 bg-amber-50 text-amber-950",
    badge: "bg-amber-700 text-white",
  },
};

export function CertificateVerificationPage() {
  const { token = "" } = useParams();
  const [certificate, setCertificate] = useState<CertificateVerification | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    void apiClient
      .verifyCertificate(token)
      .then(setCertificate)
      .catch((caught) => {
        setError(
          caught instanceof ApiError && caught.status === 404
            ? "No certificate matches this verification link."
            : "Certificate verification is temporarily unavailable.",
        );
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  const presentation = certificate ? statePresentation[certificate.state] : null;
  const StatusIcon = presentation?.icon ?? ShieldAlert;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex min-h-16 max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-3 font-semibold">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Award className="h-5 w-5" aria-hidden="true" />
            </span>
            NCCT Certificate Verification
          </Link>
          <Badge className="hidden sm:inline-flex">Public record</Badge>
        </div>
      </header>
      <main className="py-10 sm:py-16">
        <div className="mx-4 sm:mx-6 lg:mx-auto lg:max-w-3xl">
          {isLoading ? <LoadingState label="Verifying certificate" /> : null}
          {error ? (
            <ErrorState title="Certificate not verified" description={error} />
          ) : null}
          {certificate && presentation ? (
            <article className="overflow-hidden rounded-lg border bg-card shadow-sm">
            <div className={cn("border-b p-6 sm:p-8", presentation.panel)}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-4">
                  <StatusIcon className="h-10 w-10 shrink-0" aria-hidden="true" />
                  <div>
                    <h1 className="text-2xl font-semibold">{presentation.title}</h1>
                    <p className="mt-1 text-sm leading-6">{presentation.description}</p>
                  </div>
                </div>
                <Badge className={presentation.badge}>{certificate.state}</Badge>
              </div>
            </div>
            <div className="p-6 sm:p-8">
              <p className="text-sm text-muted-foreground">Certificate awarded to</p>
              <h2 className="mt-2 text-2xl font-semibold">{certificate.recipient_name}</h2>
              <p className="mt-5 text-sm text-muted-foreground">Programme</p>
              <p className="mt-1 text-lg font-medium">{certificate.programme_title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{certificate.institution_name}</p>
              <dl className="mt-7 grid gap-5 border-t pt-6 sm:grid-cols-3">
                <div>
                  <dt className="text-xs text-muted-foreground">Certificate number</dt>
                  <dd className="mt-2 break-all font-mono text-sm font-medium">{certificate.certificate_number}</dd>
                </div>
                <div>
                  <dt className="flex items-center gap-1.5 text-xs text-muted-foreground"><CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />Issued</dt>
                  <dd className="mt-2 text-sm font-medium">{formatDate(certificate.issued_at)}</dd>
                </div>
                <div>
                  <dt className="flex items-center gap-1.5 text-xs text-muted-foreground"><CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />Valid until</dt>
                  <dd className="mt-2 text-sm font-medium">{formatDate(certificate.expires_at)}</dd>
                </div>
              </dl>
            </div>
            </article>
          ) : null}
        </div>
      </main>
    </div>
  );
}
