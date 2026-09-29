import {
  Check,
  Clock3,
  ExternalLink,
  Laptop,
  Plus,
  QrCode,
  ScanFace,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import QRCode from "qrcode";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { FaceCapture } from "../components/attendance/face-capture";
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
  type AttendanceCorrection,
  type AttendanceReport,
  type AttendanceSession,
  type AttendanceStatus,
  type BiometricChallenge,
  type BiometricEnrollment,
  type BiometricVerification,
  type KioskDevice,
  type Programme,
  type RegisteredKioskDevice,
  type TraineeAttendanceIdentity,
} from "../lib/api/client";
import { setDeviceToken } from "../lib/kiosk-db";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function errorMessage(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

function localInputValue(date: Date) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusTone(status: string) {
  if (status === "open" || status === "present" || status === "approved") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (status === "pending" || status === "excused") return "bg-amber-100 text-amber-900";
  if (status === "cancelled" || status === "rejected") return "bg-red-100 text-red-800";
  return "bg-muted text-foreground";
}

function TraineeIdentityView() {
  const [identity, setIdentity] = useState<TraineeAttendanceIdentity | null>(null);
  const [biometric, setBiometric] = useState<BiometricEnrollment | null>(null);
  const [challenge, setChallenge] = useState<BiometricChallenge | null>(null);
  const [qrImage, setQrImage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [consentGranted, setConsentGranted] = useState(false);
  const [isBiometricBusy, setIsBiometricBusy] = useState(false);

  useEffect(() => {
    void apiClient
      .attendanceIdentity()
      .then(async (item) => {
        setIdentity(item);
        setQrImage(
          await QRCode.toDataURL(item.qr_payload, {
            width: 360,
            margin: 2,
            errorCorrectionLevel: "M",
            color: { dark: "#0f172a", light: "#ffffff" },
          }),
        );
      })
      .catch((caught) => setError(errorMessage(caught, "Unable to load your attendance QR.")));
    void apiClient
      .biometricEnrollment()
      .then(setBiometric)
      .catch((caught) =>
        setNotice(errorMessage(caught, "Optional face verification is currently unavailable.")),
      );
  }, []);

  const beginBiometricEnrollment = async () => {
    if (!consentGranted) {
      setNotice("Read the notice and explicitly agree before starting face enrolment.");
      return;
    }
    setIsBiometricBusy(true);
    setNotice(null);
    try {
      setChallenge(await apiClient.createBiometricEnrollmentChallenge());
    } catch (caught) {
      setNotice(errorMessage(caught, "Face enrolment could not be started."));
    } finally {
      setIsBiometricBusy(false);
    }
  };

  const completeBiometricEnrollment = async (frames: Blob[]) => {
    if (!challenge) return;
    setIsBiometricBusy(true);
    setNotice(null);
    try {
      setBiometric(await apiClient.enrollBiometric(challenge.id, frames));
      setChallenge(null);
      setConsentGranted(false);
      setNotice("Face template enrolled. QR attendance is still available at every kiosk.");
    } catch (caught) {
      setChallenge(null);
      setNotice(errorMessage(caught, "Face enrolment was rejected. Request a new challenge."));
    } finally {
      setIsBiometricBusy(false);
    }
  };

  const deleteBiometricEnrollment = async () => {
    if (!window.confirm("Delete your protected face template and withdraw biometric consent?")) {
      return;
    }
    setIsBiometricBusy(true);
    try {
      const result = await apiClient.deleteMyBiometricEnrollment();
      setBiometric((current) =>
        current ? { ...current, enrolled: false, enrolled_at: null } : current,
      );
      setChallenge(null);
      setNotice(result.message);
    } catch (caught) {
      setNotice(errorMessage(caught, "Biometric data could not be deleted."));
    } finally {
      setIsBiometricBusy(false);
    }
  };

  if (error) return <ErrorState title="Attendance QR unavailable" description={error} />;
  if (!identity || !qrImage) return <LoadingState label="Preparing your attendance QR" />;
  return (
    <div className="mx-auto max-w-xl text-center">
      <p className="text-sm font-semibold text-primary">Trainee identity</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">My attendance QR</h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Show this QR at your training venue. It identifies you but does not mark attendance until an
        authorised kiosk validates your enrolment and the active session.
      </p>
      <div className="mx-auto mt-7 w-fit rounded-md border bg-white p-4 shadow-sm">
        <img className="h-auto w-[min(72vw,360px)]" src={qrImage} alt="Your unique trainee attendance QR code" />
      </div>
      <p className="mt-5 text-lg font-semibold">{identity.full_name}</p>
      <p className="mt-1 font-mono text-sm text-muted-foreground">{identity.identity_code}</p>
      <div className="mt-6 border-l-4 border-sky-500 bg-sky-50 p-4 text-left text-sm leading-6 text-sky-950">
        Keep this code private. Report a lost or shared code to your institute administrator.
      </div>

      {biometric ? (
        <section className="mt-8 border-t pt-7 text-left" aria-labelledby="face-enrolment-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-primary">Optional attendance method</p>
              <h2 id="face-enrolment-heading" className="mt-1 text-xl font-semibold">
                Face verification
              </h2>
            </div>
            <Badge className={biometric.enrolled ? statusTone("approved") : statusTone("pending")}>
              {biometric.enrolled ? "Enrolled" : "Not enrolled"}
            </Badge>
          </div>
          {biometric.is_demo ? (
            <div className="mt-4 border-l-4 border-amber-500 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
              <strong>Demonstration mode:</strong> this local visual-template comparison is not
              production-grade face recognition or presentation-attack detection. Use QR for any
              real attendance decision.
            </div>
          ) : null}
          <p className="mt-4 text-sm leading-6 text-muted-foreground">{biometric.privacy_notice}</p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            Identity code: {identity.identity_code}
          </p>

          {notice ? (
            <p className="mt-4 border-l-4 border-primary bg-muted px-4 py-3 text-sm" role="status">
              {notice}
            </p>
          ) : null}

          {!biometric.enrolled && biometric.provider_mode !== "disabled" ? (
            <div className="mt-5 space-y-4">
              <label className="flex min-h-12 items-start gap-3 rounded-md border p-3 text-sm leading-6">
                <input
                  className="mt-1 h-5 w-5 shrink-0 accent-primary"
                  type="checkbox"
                  checked={consentGranted}
                  onChange={(event) => setConsentGranted(event.target.checked)}
                />
                <span>
                  I voluntarily consent to face-template processing only for NCCT attendance. I
                  understand QR is available without biometric enrolment and I can delete my
                  template later.
                </span>
              </label>
              {!challenge ? (
                <Button
                  className="h-12 w-full sm:w-auto"
                  disabled={!consentGranted || isBiometricBusy}
                  onClick={() => void beginBiometricEnrollment()}
                >
                  <ScanFace className="h-5 w-5" aria-hidden="true" />
                  Begin face enrolment
                </Button>
              ) : (
                <FaceCapture
                  instruction={challenge.instruction}
                  actionLabel="Capture and enrol"
                  isSubmitting={isBiometricBusy}
                  onCapture={completeBiometricEnrollment}
                />
              )}
            </div>
          ) : null}

          {biometric.enrolled ? (
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
              <p className="text-sm text-muted-foreground">
                Enrolled {biometric.enrolled_at ? formatDateTime(biometric.enrolled_at) : "recently"}
              </p>
              <Button
                variant="outline"
                className="min-h-11 text-red-700"
                disabled={isBiometricBusy}
                onClick={() => void deleteBiometricEnrollment()}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete face data
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

export function AttendancePage() {
  const { user, logout, can } = useAuth();
  const canApproveAttendance = can("attendance:approve");
  const [sessions, setSessions] = useState<AttendanceSession[]>([]);
  const [devices, setDevices] = useState<KioskDevice[]>([]);
  const [corrections, setCorrections] = useState<AttendanceCorrection[]>([]);
  const [biometricReviews, setBiometricReviews] = useState<BiometricVerification[]>([]);
  const [biometricReviewNotes, setBiometricReviewNotes] = useState<Record<string, string>>({});
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedProgrammeId, setSelectedProgrammeId] = useState("");
  const [qrSessionId, setQrSessionId] = useState<string | null>(null);
  const [qrImage, setQrImage] = useState("");
  const [qrExpiresAt, setQrExpiresAt] = useState("");
  const [report, setReport] = useState<AttendanceReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [newDevice, setNewDevice] = useState<RegisteredKioskDevice | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [correctionTarget, setCorrectionTarget] = useState<{
    sessionId: string;
    enrollmentId: string;
    traineeName: string;
    currentStatus: AttendanceStatus;
  } | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sessionItems, deviceItems, correctionItems, programmeItems, reviewItems] = await Promise.all([
        apiClient.attendanceSessions(),
        apiClient.kioskDevices(),
        apiClient.attendanceCorrections(),
        apiClient.programmes(),
        canApproveAttendance ? apiClient.biometricReviews() : Promise.resolve([]),
      ]);
      setSessions(sessionItems);
      setDevices(deviceItems);
      setCorrections(correctionItems);
      setBiometricReviews(reviewItems);
      setProgrammes(programmeItems.items);
    } catch (caught) {
      setError(errorMessage(caught, "Unable to load attendance management."));
    } finally {
      setIsLoading(false);
    }
  }, [canApproveAttendance]);

  useEffect(() => {
    if (can("attendance:manage")) void load();
  }, [can, load]);

  const selectedProgramme = useMemo(
    () => programmes.find((programme) => programme.id === selectedProgrammeId),
    [programmes, selectedProgrammeId],
  );

  const refreshSessionQr = useCallback(async (sessionId: string) => {
    try {
      const qr = await apiClient.attendanceSessionQr(sessionId);
      setQrImage(
        await QRCode.toDataURL(qr.payload, {
          width: 320,
          margin: 1,
          errorCorrectionLevel: "M",
          color: { dark: "#0f172a", light: "#ffffff" },
        }),
      );
      setQrExpiresAt(qr.expires_at);
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to issue the session QR."));
      setQrSessionId(null);
    }
  }, []);

  useEffect(() => {
    if (!qrSessionId) return;
    void refreshSessionQr(qrSessionId);
    const timer = window.setInterval(() => void refreshSessionQr(qrSessionId), 30_000);
    return () => window.clearInterval(timer);
  }, [qrSessionId, refreshSessionQr]);

  if (!user) return null;

  const createSession = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setMessage(null);
    try {
      await apiClient.createAttendanceSession({
        programme_id: String(form.get("programme_id")),
        batch_id: String(form.get("batch_id")),
        title: String(form.get("title")),
        starts_at: new Date(String(form.get("starts_at"))).toISOString(),
        ends_at: new Date(String(form.get("ends_at"))).toISOString(),
      });
      setShowCreate(false);
      setSelectedProgrammeId("");
      await load();
      setMessage("Attendance session created.");
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to create attendance session."));
    }
  };

  const registerDevice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const device = await apiClient.registerKioskDevice({ name: String(form.get("name")) });
      setNewDevice(device);
      setDevices((current) => [device, ...current]);
      event.currentTarget.reset();
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to register this kiosk."));
    }
  };

  const openReport = async (sessionId: string) => {
    setReportLoading(true);
    setMessage(null);
    try {
      setReport(await apiClient.attendanceReport(sessionId));
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to load the attendance report."));
    } finally {
      setReportLoading(false);
    }
  };

  const requestCorrection = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!correctionTarget) return;
    const form = new FormData(event.currentTarget);
    try {
      await apiClient.requestAttendanceCorrection(correctionTarget.sessionId, {
        enrollment_id: correctionTarget.enrollmentId,
        requested_status: String(form.get("requested_status")) as AttendanceStatus,
        reason: String(form.get("reason")),
      });
      setCorrectionTarget(null);
      await load();
      setMessage("Correction sent for approval.");
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to request the correction."));
    }
  };

  const reviewCorrection = async (id: string, decision: "approved" | "rejected") => {
    try {
      await apiClient.reviewAttendanceCorrection(id, decision);
      await load();
      if (report) await openReport(report.session.id);
      setMessage(`Correction ${decision}.`);
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to review the correction."));
    }
  };

  const reviewBiometric = async (id: string, decision: "approved" | "rejected") => {
    const notes = biometricReviewNotes[id]?.trim() ?? "";
    if (notes.length < 5) {
      setMessage("Add a review note of at least five characters before deciding.");
      return;
    }
    try {
      await apiClient.reviewBiometric(id, decision, notes);
      setBiometricReviewNotes((current) => ({ ...current, [id]: "" }));
      await load();
      if (report) await openReport(report.session.id);
      setMessage(`Biometric review ${decision}.`);
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to complete the biometric review."));
    }
  };

  const deleteTraineeBiometric = async (traineeId: string, traineeName: string) => {
    if (!window.confirm(`Delete the protected face template for ${traineeName}?`)) return;
    try {
      const result = await apiClient.deleteTraineeBiometricEnrollment(traineeId);
      if (report) await openReport(report.session.id);
      setMessage(result.message);
    } catch (caught) {
      setMessage(errorMessage(caught, "Unable to delete the biometric template."));
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      {!can("attendance:manage") ? (
        <TraineeIdentityView />
      ) : (
        <>
          <header className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-primary">Training delivery</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Attendance</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                Open attendance sessions, pair trusted camera kiosks and review validated records.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link to="/kiosk/attendance" target="_blank">
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  Open kiosk
                </Link>
              </Button>
              <Button onClick={() => setShowCreate((current) => !current)}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                New session
              </Button>
            </div>
          </header>

          {message ? (
            <p className="mt-4 border-l-4 border-primary bg-muted px-4 py-3 text-sm" role="status">
              {message}
            </p>
          ) : null}

          {showCreate ? (
            <form className="mt-6 border-b pb-6" onSubmit={(event) => void createSession(event)}>
              <h2 className="text-base font-semibold">Create attendance session</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium">
                  Programme
                  <select
                    className={`${fieldClass} mt-2`}
                    name="programme_id"
                    value={selectedProgrammeId}
                    onChange={(event) => setSelectedProgrammeId(event.target.value)}
                    required
                  >
                    <option value="">Select programme</option>
                    {programmes.map((programme) => (
                      <option key={programme.id} value={programme.id}>
                        {programme.code} · {programme.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium">
                  Batch
                  <select className={`${fieldClass} mt-2`} name="batch_id" required>
                    <option value="">Select batch</option>
                    {selectedProgramme?.batches?.map((batch) => (
                      <option key={batch.id} value={batch.id}>
                        {batch.code} · {batch.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium md:col-span-2">
                  Session title
                  <Input className="mt-2" name="title" minLength={3} required />
                </label>
                <label className="text-sm font-medium">
                  Starts at
                  <Input
                    className="mt-2"
                    name="starts_at"
                    type="datetime-local"
                    defaultValue={localInputValue(new Date(Date.now() - 5 * 60_000))}
                    required
                  />
                </label>
                <label className="text-sm font-medium">
                  Ends at
                  <Input
                    className="mt-2"
                    name="ends_at"
                    type="datetime-local"
                    defaultValue={localInputValue(new Date(Date.now() + 2 * 60 * 60_000))}
                    required
                  />
                </label>
              </div>
              <div className="mt-4 flex gap-2">
                <Button type="submit">Create session</Button>
                <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          ) : null}

          {isLoading ? <LoadingState label="Loading attendance" /> : null}
          {error ? (
            <ErrorState title="Attendance could not be loaded" description={error} onRetry={load} />
          ) : null}
          {!isLoading && !error ? (
            <div className="mt-7 grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div className="min-w-0 space-y-8">
                <section aria-labelledby="attendance-sessions-heading">
                  <div className="flex items-center justify-between gap-3">
                    <h2 id="attendance-sessions-heading" className="text-lg font-semibold">
                      Attendance sessions
                    </h2>
                    <span className="text-sm text-muted-foreground">{sessions.length} sessions</span>
                  </div>
                  {sessions.length === 0 ? (
                    <EmptyState
                      title="No attendance sessions"
                      description="Create a session for an assigned programme batch."
                    />
                  ) : (
                    <div className="mt-3 overflow-x-auto rounded-md border">
                      <table className="w-full min-w-[720px] text-left text-sm">
                        <thead className="bg-muted text-xs uppercase text-muted-foreground">
                          <tr>
                            <th className="px-4 py-3">Session</th>
                            <th className="px-4 py-3">Time</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3">Check-ins</th>
                            <th className="px-4 py-3 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {sessions.map((item) => (
                            <tr key={item.id}>
                              <td className="px-4 py-4">
                                <p className="font-medium">{item.title}</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {item.programme_code} · {item.batch_name}
                                </p>
                              </td>
                              <td className="px-4 py-4 text-muted-foreground">
                                {formatDateTime(item.starts_at)}
                              </td>
                              <td className="px-4 py-4">
                                <Badge className={statusTone(item.status)}>{item.status}</Badge>
                              </td>
                              <td className="px-4 py-4 font-semibold">{item.check_in_count}</td>
                              <td className="px-4 py-4">
                                <div className="flex justify-end gap-2">
                                  {item.status === "open" ? (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => setQrSessionId(item.id)}
                                    >
                                      <QrCode className="h-4 w-4" aria-hidden="true" />
                                      Session QR
                                    </Button>
                                  ) : null}
                                  <Button size="sm" onClick={() => void openReport(item.id)}>
                                    Report
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                {qrSessionId ? (
                  <section className="border-y bg-slate-950 px-4 py-6 text-center text-white" aria-label="Rotating attendance session QR">
                    <div className="mx-auto flex max-w-xl flex-col items-center">
                      <p className="text-sm font-medium text-orange-300">Rotating session QR</p>
                      <h2 className="mt-1 text-xl font-semibold">
                        {sessions.find((item) => item.id === qrSessionId)?.title}
                      </h2>
                      {qrImage ? (
                        <img className="mt-5 w-[min(72vw,320px)] bg-white p-3" src={qrImage} alt="Time-limited attendance session QR" />
                      ) : (
                        <div className="mt-5 h-80 w-80 animate-pulse bg-slate-800" />
                      )}
                      <p className="mt-3 flex items-center gap-2 text-sm text-slate-300">
                        <Clock3 className="h-4 w-4" aria-hidden="true" />
                        Refreshes automatically · current code expires {qrExpiresAt ? new Date(qrExpiresAt).toLocaleTimeString("en-IN") : "soon"}
                      </p>
                      <Button className="mt-4 border-white/30 bg-transparent text-white hover:bg-white/10" variant="outline" onClick={() => setQrSessionId(null)}>
                        Close QR
                      </Button>
                    </div>
                  </section>
                ) : null}

                {reportLoading ? <LoadingState label="Loading attendance report" /> : null}
                {report ? (
                  <section aria-labelledby="attendance-report-heading">
                    <div className="flex flex-wrap items-end justify-between gap-3">
                      <div>
                        <h2 id="attendance-report-heading" className="text-lg font-semibold">
                          {report.session.title} report
                        </h2>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {report.session.programme_code} · {report.session.batch_name}
                        </p>
                      </div>
                      <Button variant="ghost" size="icon" aria-label="Close report" onClick={() => setReport(null)}>
                        <X className="h-5 w-5" aria-hidden="true" />
                      </Button>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border bg-border sm:grid-cols-4">
                      {[
                        ["Attendance", `${report.attendance_percent}%`],
                        ["Present", report.present_count],
                        ["Absent", report.absent_count],
                        ["Excused", report.excused_count],
                      ].map(([label, value]) => (
                        <div className="bg-card p-4" key={label}>
                          <p className="text-xs text-muted-foreground">{label}</p>
                          <p className="mt-1 text-2xl font-semibold">{value}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 overflow-x-auto rounded-md border">
                      <table className="w-full min-w-[680px] text-left text-sm">
                        <thead className="bg-muted text-xs uppercase text-muted-foreground">
                          <tr><th className="px-4 py-3">Trainee</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Captured</th><th className="px-4 py-3">Device</th><th className="px-4 py-3" /></tr>
                        </thead>
                        <tbody className="divide-y">
                          {report.rows.map((row) => (
                            <tr key={row.enrollment_id}>
                              <td className="px-4 py-3"><p className="font-medium">{row.trainee_name}</p><p className="text-xs text-muted-foreground">{row.trainee_email}</p></td>
                              <td className="px-4 py-3"><Badge className={statusTone(row.status)}>{row.status}</Badge></td>
                              <td className="px-4 py-3 text-muted-foreground">{row.captured_at ? formatDateTime(row.captured_at) : "Not recorded"}</td>
                              <td className="px-4 py-3 font-mono text-xs">{row.device_code ?? row.source ?? "-"}</td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex justify-end gap-1">
                                  {row.biometric_enrolled && canApproveAttendance ? (
                                    <Button size="sm" variant="ghost" className="text-red-700" onClick={() => void deleteTraineeBiometric(row.trainee_id, row.trainee_name)}>
                                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                                      Delete face data
                                    </Button>
                                  ) : null}
                                  <Button size="sm" variant="ghost" onClick={() => setCorrectionTarget({ sessionId: report.session.id, enrollmentId: row.enrollment_id, traineeName: row.trainee_name, currentStatus: row.status })}>Correct</Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                ) : null}

                {correctionTarget ? (
                  <form className="border-l-4 border-amber-500 bg-amber-50 p-5" onSubmit={(event) => void requestCorrection(event)}>
                    <h2 className="font-semibold text-amber-950">Request correction for {correctionTarget.traineeName}</h2>
                    <p className="mt-1 text-sm text-amber-900">Current status: {correctionTarget.currentStatus}. An institute administrator must approve this change.</p>
                    <div className="mt-4 grid gap-4 sm:grid-cols-[180px_1fr]">
                      <label className="text-sm font-medium text-amber-950">New status<select className={`${fieldClass} mt-2`} name="requested_status" required><option value="present">Present</option><option value="absent">Absent</option><option value="excused">Excused</option></select></label>
                      <label className="text-sm font-medium text-amber-950">Reason<textarea className={`${fieldClass} mt-2 min-h-24`} name="reason" minLength={5} required /></label>
                    </div>
                    <div className="mt-4 flex gap-2"><Button type="submit">Send for approval</Button><Button type="button" variant="ghost" onClick={() => setCorrectionTarget(null)}>Cancel</Button></div>
                  </form>
                ) : null}

                <section aria-labelledby="corrections-heading">
                  <h2 id="corrections-heading" className="text-lg font-semibold">Manual corrections</h2>
                  {corrections.length === 0 ? <p className="mt-3 text-sm text-muted-foreground">No correction requests.</p> : (
                    <div className="mt-3 divide-y rounded-md border">
                      {corrections.map((item) => (
                        <article className="p-4" key={item.id}>
                          <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{item.trainee_name}</p><p className="mt-1 text-sm text-muted-foreground">{item.previous_status ?? "absent"} to {item.requested_status} · {item.session_title}</p></div><Badge className={statusTone(item.approval_status)}>{item.approval_status}</Badge></div>
                          <p className="mt-3 text-sm">{item.reason}</p>
                          <p className="mt-2 text-xs text-muted-foreground">Requested by {item.requested_by_name}</p>
                          {item.approval_status === "pending" && can("attendance:approve") ? <div className="mt-3 flex gap-2"><Button size="sm" onClick={() => void reviewCorrection(item.id, "approved")}><Check className="h-4 w-4" aria-hidden="true" />Approve</Button><Button size="sm" variant="destructive" onClick={() => void reviewCorrection(item.id, "rejected")}><X className="h-4 w-4" aria-hidden="true" />Reject</Button></div> : null}
                        </article>
                      ))}
                    </div>
                  )}
                </section>

                {canApproveAttendance ? (
                  <section aria-labelledby="biometric-reviews-heading">
                    <div className="flex items-center gap-2">
                      <ScanFace className="h-5 w-5 text-primary" aria-hidden="true" />
                      <h2 id="biometric-reviews-heading" className="text-lg font-semibold">
                        Face-verification reviews
                      </h2>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      Uncertain matches never create attendance automatically. Approve only after
                      checking the trainee in person; camera images are not retained.
                    </p>
                    {biometricReviews.length === 0 ? (
                      <p className="mt-3 text-sm text-muted-foreground">No face verifications require review.</p>
                    ) : (
                      <div className="mt-3 divide-y rounded-md border">
                        {biometricReviews.map((item) => (
                          <article className="p-4" key={item.id}>
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className="font-medium">{item.trainee_name}</p>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  {item.session_title} · confidence {Math.round(item.confidence * 100)}%
                                  · automatic threshold {Math.round(item.threshold * 100)}%
                                </p>
                              </div>
                              <Badge className={statusTone(item.review_status ?? item.status)}>
                                {item.review_status ?? item.status.replace("_", " ")}
                              </Badge>
                            </div>
                            <p className="mt-3 text-sm">{item.detail}</p>
                            {item.review_status === "pending" ? (
                              <div className="mt-4 space-y-3">
                                <label className="block text-sm font-medium" htmlFor={`biometric-review-${item.id}`}>
                                  In-person review note
                                </label>
                                <textarea
                                  id={`biometric-review-${item.id}`}
                                  className={`${fieldClass} min-h-24`}
                                  value={biometricReviewNotes[item.id] ?? ""}
                                  onChange={(event) => setBiometricReviewNotes((current) => ({ ...current, [item.id]: event.target.value }))}
                                  minLength={5}
                                  maxLength={1000}
                                />
                                <div className="flex flex-wrap gap-2">
                                  <Button size="sm" onClick={() => void reviewBiometric(item.id, "approved")}>
                                    <Check className="h-4 w-4" aria-hidden="true" />Approve attendance
                                  </Button>
                                  <Button size="sm" variant="destructive" onClick={() => void reviewBiometric(item.id, "rejected")}>
                                    <X className="h-4 w-4" aria-hidden="true" />Reject match
                                  </Button>
                                </div>
                              </div>
                            ) : null}
                          </article>
                        ))}
                      </div>
                    )}
                  </section>
                ) : null}
              </div>

              <aside className="min-w-0">
                <section className="rounded-md border bg-card p-5 shadow-sm" aria-labelledby="kiosk-devices-heading">
                  <Laptop className="h-7 w-7 text-primary" aria-hidden="true" />
                  <h2 id="kiosk-devices-heading" className="mt-3 text-lg font-semibold">Kiosk devices</h2>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">Register each laptop, Raspberry Pi or Android browser before it can submit attendance.</p>
                  <form className="mt-4 flex gap-2" onSubmit={(event) => void registerDevice(event)}><Input name="name" placeholder="Reception laptop" minLength={2} required /><Button size="icon" aria-label="Register kiosk"><Plus className="h-5 w-5" aria-hidden="true" /></Button></form>
                  {newDevice ? (
                    <div className="mt-4 border-l-4 border-emerald-500 bg-emerald-50 p-4 text-emerald-950">
                      <p className="font-semibold">Save this token now</p><p className="mt-1 text-xs leading-5">It is shown once and stored only on the kiosk.</p><code className="mt-3 block break-all rounded bg-white p-2 text-xs">{newDevice.device_token}</code>
                      <Button className="mt-3 w-full" size="sm" onClick={() => void setDeviceToken(newDevice.device_token).then(() => setMessage("This browser is activated as the new kiosk."))}><ShieldCheck className="h-4 w-4" aria-hidden="true" />Activate this browser</Button>
                    </div>
                  ) : null}
                  <div className="mt-5 space-y-3">
                    {devices.map((device) => (
                      <div className="border-t pt-3 first:border-t-0 first:pt-0" key={device.id}><div className="flex items-start justify-between gap-2"><div><p className="text-sm font-medium">{device.name}</p><p className="mt-1 font-mono text-xs text-muted-foreground">{device.device_code}</p></div><Badge className={statusTone(device.status)}>{device.status}</Badge></div>{device.status === "active" ? <Button className="mt-2 px-0 text-destructive" size="sm" variant="ghost" onClick={() => void apiClient.revokeKioskDevice(device.id).then(load)}>Revoke device</Button> : null}</div>
                    ))}
                  </div>
                </section>
              </aside>
            </div>
          ) : null}
        </>
      )}
    </AppShell>
  );
}
