import { BrowserQRCodeReader, type IScannerControls } from "@zxing/browser";
import {
  Camera,
  CheckCircle2,
  Expand,
  Laptop,
  RefreshCw,
  RotateCcw,
  ScanLine,
  ScanFace,
  ShieldCheck,
  Wifi,
  WifiOff,
  XCircle,
} from "lucide-react";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { FaceCapture } from "../components/attendance/face-capture";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type AttendanceSyncItem,
  type BiometricChallenge,
  type KioskSession,
} from "../lib/api/client";
import {
  clearKioskData,
  clearPairedSession,
  enqueueAttendance,
  getDeviceToken,
  getPairedSession,
  queuedAttendance,
  setDeviceToken,
  setPairedSession,
  synchronizeAttendanceQueue,
} from "../lib/kiosk-db";
import { cn } from "../lib/utils";

type Feedback = {
  tone: "success" | "error" | "offline" | "info";
  title: string;
  detail: string;
};

const feedbackStyle = {
  success: "border-emerald-500 bg-emerald-50 text-emerald-950",
  error: "border-red-500 bg-red-50 text-red-950",
  offline: "border-amber-500 bg-amber-50 text-amber-950",
  info: "border-sky-500 bg-sky-50 text-sky-950",
};

function errorMessage(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

function feedbackFromResult(result: AttendanceSyncItem): Feedback {
  if (result.result === "created") {
    return {
      tone: "success",
      title: `Welcome, ${result.trainee_name ?? "trainee"}`,
      detail: "Attendance recorded successfully.",
    };
  }
  if (result.result === "duplicate" || result.result === "already_checked_in") {
    return {
      tone: "info",
      title: "Already checked in",
      detail: result.detail,
    };
  }
  return { tone: "error", title: "Attendance not recorded", detail: result.detail };
}

export function AttendanceKioskPage() {
  const [deviceToken, setStoredDeviceToken] = useState<string | null>(null);
  const [session, setSession] = useState<KioskSession | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>({
    tone: "info",
    title: "Kiosk ready",
    detail: "Activate this device, then pair it to an attendance session.",
  });
  const [manualCode, setManualCode] = useState("");
  const [identityCode, setIdentityCode] = useState("");
  const [faceChallenge, setFaceChallenge] = useState<BiometricChallenge | null>(null);
  const [isFaceProcessing, setIsFaceProcessing] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsRef = useRef<IScannerControls | null>(null);
  const processingRef = useRef(false);
  const lastScanRef = useRef<{ value: string; at: number } | null>(null);

  const refreshPendingCount = useCallback(async () => {
    setPendingCount((await queuedAttendance()).length);
  }, []);

  const synchronize = useCallback(async () => {
    if (!deviceToken || !navigator.onLine) return null;
    try {
      const response = await synchronizeAttendanceQueue((items) =>
        apiClient.syncKioskAttendance(deviceToken, items),
      );
      await refreshPendingCount();
      if (response?.items.length) {
        setFeedback(feedbackFromResult(response.items[response.items.length - 1]));
      }
      return response;
    } catch (caught) {
      setFeedback({
        tone: "offline",
        title: "Saved on this device",
        detail: errorMessage(caught, "Synchronization will retry when the connection returns."),
      });
      return null;
    }
  }, [deviceToken, refreshPendingCount]);

  useEffect(() => {
    void Promise.all([getDeviceToken(), getPairedSession(), queuedAttendance()]).then(
      ([storedToken, storedSession, queued]) => {
        setStoredDeviceToken(storedToken);
        setSession(storedSession);
        setPendingCount(queued.length);
      },
    );
  }, []);

  useEffect(() => {
    const online = () => {
      setIsOnline(true);
      void synchronize();
    };
    const offline = () => setIsOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, [synchronize]);

  useEffect(() => {
    if (deviceToken && navigator.onLine) void synchronize();
  }, [deviceToken, synchronize]);

  useEffect(
    () => () => {
      controlsRef.current?.stop();
    },
    [],
  );

  const processCode = useCallback(
    async (rawValue: string) => {
      const value = rawValue.trim();
      if (!value || processingRef.current) return;
      const previous = lastScanRef.current;
      if (previous?.value === value && Date.now() - previous.at < 3000) return;
      lastScanRef.current = { value, at: Date.now() };
      processingRef.current = true;
      setIsProcessing(true);
      try {
        if (!deviceToken) {
          setFeedback({
            tone: "error",
            title: "Device not activated",
            detail: "Enter the one-time kiosk token before scanning.",
          });
          return;
        }
        if (!session) {
          if (!navigator.onLine) {
            setFeedback({
              tone: "error",
              title: "Connection required",
              detail: "A new session must be paired while online.",
            });
            return;
          }
          const paired = await apiClient.pairKiosk(deviceToken, value);
          await setPairedSession(paired);
          setSession(paired);
          setFeedback({
            tone: "success",
            title: "Session paired",
            detail: `${paired.programme_code}: ${paired.title}`,
          });
          return;
        }
        if (!value.startsWith("NCCT-TRAINEE:")) {
          setFeedback({
            tone: "error",
            title: "Wrong QR code",
            detail: "Scan the trainee identity QR shown in the trainee portal.",
          });
          return;
        }
        if (Date.now() > new Date(session.offline_until).getTime()) {
          setFeedback({
            tone: "error",
            title: "Session window ended",
            detail: "Pair the kiosk to a current attendance session.",
          });
          return;
        }
        const idempotencyKey = crypto.randomUUID();
        await enqueueAttendance({
          idempotency_key: idempotencyKey,
          session_id: session.session_id,
          trainee_qr: value,
          captured_at: new Date().toISOString(),
        });
        await refreshPendingCount();
        setFeedback({
          tone: navigator.onLine ? "info" : "offline",
          title: navigator.onLine ? "Checking attendance" : "Saved offline",
          detail: navigator.onLine
            ? "Validating the trainee and enrolment."
            : "This scan will synchronize automatically when the connection returns.",
        });
        if (navigator.onLine) await synchronize();
      } catch (caught) {
        setFeedback({
          tone: "error",
          title: session ? "Scan could not be saved" : "Session could not be paired",
          detail: errorMessage(caught, "Please check the QR code and try again."),
        });
      } finally {
        processingRef.current = false;
        setIsProcessing(false);
      }
    }, [deviceToken, refreshPendingCount, session, synchronize],
  );

  const startCamera = async () => {
    if (!videoRef.current) return;
    try {
      controlsRef.current?.stop();
      const reader = new BrowserQRCodeReader(undefined, { delayBetweenScanAttempts: 200 });
      controlsRef.current = await reader.decodeFromVideoDevice(
        undefined,
        videoRef.current,
        (result) => {
          if (result) void processCode(result.getText());
        },
      );
      setIsCameraActive(true);
      setFeedback({
        tone: "info",
        title: session ? "Ready for trainee QR" : "Ready for session QR",
        detail: "Hold the QR code steady inside the camera area.",
      });
    } catch (caught) {
      setFeedback({
        tone: "error",
        title: "Camera unavailable",
        detail:
          caught instanceof Error
            ? caught.message
            : "Allow camera access in Chromium and try again.",
      });
    }
  };

  const stopCamera = () => {
    controlsRef.current?.stop();
    controlsRef.current = null;
    setIsCameraActive(false);
  };

  const activateDevice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const token = String(form.get("device_token") ?? "").trim();
    if (!token) return;
    await setDeviceToken(token);
    setStoredDeviceToken(token);
    setFeedback({
      tone: "success",
      title: "Device activated",
      detail: "Scan the rotating session QR from the trainer dashboard.",
    });
  };

  const submitManualCode = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void processCode(manualCode).then(() => setManualCode(""));
  };

  const resetSession = async () => {
    await clearPairedSession();
    setSession(null);
    setFaceChallenge(null);
    setFeedback({
      tone: "info",
      title: "Ready for a session",
      detail: "Scan the trainer's rotating attendance-session QR.",
    });
  };

  const resetDevice = async () => {
    if (pendingCount > 0) {
      setFeedback({
        tone: "error",
        title: "Pending scans remain",
        detail: "Reconnect and synchronize all saved attendance before changing device.",
      });
      return;
    }
    stopCamera();
    await clearKioskData();
    setStoredDeviceToken(null);
    setSession(null);
    setFaceChallenge(null);
  };

  const startFaceChallenge = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!deviceToken || !session || !navigator.onLine) return;
    stopCamera();
    setIsFaceProcessing(true);
    try {
      const challenge = await apiClient.createKioskBiometricChallenge(
        deviceToken,
        session.session_id,
        identityCode.trim().toUpperCase(),
      );
      setFaceChallenge(challenge);
      setFeedback({
        tone: "info",
        title: `Verify ${challenge.trainee_name}`,
        detail: challenge.instruction,
      });
    } catch (caught) {
      setFaceChallenge(null);
      setFeedback({
        tone: "error",
        title: "Face verification unavailable",
        detail: errorMessage(caught, "Use QR attendance or ask a staff member for help."),
      });
    } finally {
      setIsFaceProcessing(false);
    }
  };

  const verifyFace = async (frames: Blob[]) => {
    if (!deviceToken || !faceChallenge) return;
    setIsFaceProcessing(true);
    try {
      const result = await apiClient.verifyKioskBiometric(
        deviceToken,
        faceChallenge.id,
        frames,
      );
      if (result.status === "verified" && result.attendance_recorded) {
        setFeedback({
          tone: "success",
          title: `Welcome, ${result.trainee_name}`,
          detail: result.detail,
        });
      } else if (result.status === "manual_review") {
        setFeedback({
          tone: "offline",
          title: "Manual review required",
          detail: `${result.detail} You have not been marked present yet.`,
        });
      } else {
        setFeedback({
          tone: "error",
          title: "Face not verified",
          detail: result.detail,
        });
      }
      setFaceChallenge(null);
      setIdentityCode("");
    } catch (caught) {
      setFaceChallenge(null);
      setFeedback({
        tone: "error",
        title: "Face verification failed",
        detail: errorMessage(caught, "Attendance was not recorded. Use the QR fallback."),
      });
    } finally {
      setIsFaceProcessing(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white" aria-live="polite">
      <header className="border-b border-white/15 bg-slate-900 px-4 py-4 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-md bg-orange-500 text-slate-950">
              <ScanLine className="h-7 w-7" aria-hidden="true" />
            </span>
            <div>
              <p className="text-lg font-semibold">NCCT Attendance Kiosk</p>
              <p className="text-sm text-slate-300">
                {session ? `${session.programme_code} · ${session.batch_name}` : "Waiting for session"}
              </p>
            </div>
          </div>
          <div className="flex w-full flex-wrap items-center gap-3 text-sm font-medium sm:w-auto">
            <span
              className={cn(
                "flex min-h-11 items-center gap-2 rounded-md border px-3",
                isOnline
                  ? "border-emerald-500/60 bg-emerald-950 text-emerald-200"
                  : "border-amber-500/60 bg-amber-950 text-amber-100",
              )}
            >
              {isOnline ? <Wifi className="h-5 w-5" /> : <WifiOff className="h-5 w-5" />}
              {isOnline ? "Online" : "Offline"}
            </span>
            <span className="flex min-h-11 items-center gap-2 rounded-md border border-white/20 px-3">
              <RefreshCw className="h-5 w-5" aria-hidden="true" />
              {pendingCount} pending
            </span>
            <Button
              variant="outline"
              className="border-white/30 bg-transparent text-white hover:bg-white/10"
              onClick={() => void document.documentElement.requestFullscreen?.()}
            >
              <Expand className="h-5 w-5" aria-hidden="true" />
              Full screen
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section>
          <div className="relative aspect-[4/3] max-h-[68vh] min-h-[240px] overflow-hidden rounded-md border border-white/20 bg-black">
            <video
              ref={videoRef}
              className="h-full w-full object-cover"
              muted
              playsInline
              aria-label="Live QR camera preview"
            />
            {!isCameraActive ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center">
                <Camera className="h-16 w-16 text-slate-400" aria-hidden="true" />
                <p className="max-w-md text-lg text-slate-300">
                  {deviceToken
                    ? session
                      ? "Start the camera to scan trainee identity QR codes."
                      : "Start the camera to scan the trainer's session QR."
                    : "Activate this kiosk before starting the camera."}
                </p>
              </div>
            ) : null}
            {isCameraActive ? (
              <div className="pointer-events-none absolute inset-[15%] rounded-md border-4 border-orange-400" />
            ) : null}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Button
              className="h-16 text-base"
              disabled={!deviceToken || isCameraActive || Boolean(faceChallenge)}
              onClick={() => void startCamera()}
            >
              <Camera className="h-6 w-6" aria-hidden="true" />
              Start camera
            </Button>
            <Button
              className="h-16 border-white/30 bg-transparent text-base text-white hover:bg-white/10"
              variant="outline"
              disabled={!isCameraActive}
              onClick={stopCamera}
            >
              <XCircle className="h-6 w-6" aria-hidden="true" />
              Stop camera
            </Button>
          </div>

          <div
            className={cn("mt-4 border-l-8 p-5", feedbackStyle[feedback.tone])}
            role={feedback.tone === "error" ? "alert" : "status"}
          >
            <div className="flex items-start gap-3">
              {feedback.tone === "success" ? (
                <CheckCircle2 className="mt-0.5 h-8 w-8 shrink-0" aria-hidden="true" />
              ) : feedback.tone === "error" ? (
                <XCircle className="mt-0.5 h-8 w-8 shrink-0" aria-hidden="true" />
              ) : feedback.tone === "offline" ? (
                <WifiOff className="mt-0.5 h-8 w-8 shrink-0" aria-hidden="true" />
              ) : (
                <ShieldCheck className="mt-0.5 h-8 w-8 shrink-0" aria-hidden="true" />
              )}
              <div>
                <p className="text-xl font-semibold">{feedback.title}</p>
                <p className="mt-1 text-base leading-6">{feedback.detail}</p>
              </div>
            </div>
          </div>
        </section>

        <aside className="space-y-6">
          <section className="rounded-md border border-sky-400/40 bg-sky-950 p-4 text-sm leading-6 text-sky-100">
            <p className="font-semibold">Camera privacy</p>
            <p className="mt-1">
              QR mode processes frames only on this device. Optional face mode starts only after an
              enrolled trainee claims their identity; it sends three temporary frames for a
              one-to-one check and never searches for unknown people.
            </p>
          </section>
          {!deviceToken ? (
            <form className="rounded-md border border-white/20 bg-slate-900 p-5" onSubmit={activateDevice}>
              <Laptop className="h-8 w-8 text-orange-400" aria-hidden="true" />
              <h1 className="mt-3 text-xl font-semibold">Activate this kiosk</h1>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Enter the token shown once when an administrator registers this device.
              </p>
              <label className="mt-5 block text-sm font-medium" htmlFor="kiosk-device-token">
                Device token
              </label>
              <Input
                id="kiosk-device-token"
                name="device_token"
                type="password"
                className="mt-2 h-14 border-white/30 bg-slate-950 text-base text-white"
                autoComplete="off"
                required
              />
              <Button className="mt-4 h-14 w-full text-base" type="submit">
                <ShieldCheck className="h-5 w-5" aria-hidden="true" />
                Activate device
              </Button>
            </form>
          ) : (
            <section className="rounded-md border border-white/20 bg-slate-900 p-5">
              <p className="text-sm font-medium text-orange-300">Current session</p>
              <h1 className="mt-2 text-xl font-semibold">
                {session?.title ?? "Not paired"}
              </h1>
              {session ? (
                <div className="mt-3 space-y-1 text-sm text-slate-300">
                  <p>{session.programme_title}</p>
                  <p>{session.batch_name}</p>
                  <p>Ends {new Date(session.ends_at).toLocaleString("en-IN")}</p>
                </div>
              ) : (
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Scan or enter the trainer&apos;s rotating session QR while online.
                </p>
              )}
              {session ? (
                <Button
                  className="mt-4 w-full border-white/30 bg-transparent text-white hover:bg-white/10"
                  variant="outline"
                  onClick={() => void resetSession()}
                >
                  <RotateCcw className="h-5 w-5" aria-hidden="true" />
                  Change session
                </Button>
              ) : null}
            </section>
          )}

          {deviceToken ? (
            <form className="rounded-md border border-white/20 bg-slate-900 p-5" onSubmit={submitManualCode}>
              <label className="text-sm font-medium" htmlFor="manual-qr-code">
                QR text fallback
              </label>
              <p className="mt-1 text-xs leading-5 text-slate-400">
                Use with a USB QR reader or when camera access is unavailable.
              </p>
              <textarea
                id="manual-qr-code"
                className="mt-3 min-h-28 w-full rounded-md border border-white/30 bg-slate-950 p-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-orange-400"
                value={manualCode}
                onChange={(event) => setManualCode(event.target.value)}
              />
              <Button
                className="mt-3 h-14 w-full text-base"
                disabled={!manualCode.trim() || isProcessing}
                type="submit"
              >
                <ScanLine className="h-5 w-5" aria-hidden="true" />
                {isProcessing ? "Processing" : "Process code"}
              </Button>
            </form>
          ) : null}

          {deviceToken && session ? (
            <section className="rounded-md border border-amber-400/50 bg-slate-900 p-5">
              <div className="flex items-center gap-2">
                <ScanFace className="h-6 w-6 text-amber-300" aria-hidden="true" />
                <h2 className="text-lg font-semibold">Optional face verification</h2>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                <strong className="text-amber-200">Demo mode:</strong> not production-grade face
                recognition. It works only for a consenting enrolled trainee who enters their own
                identity code. QR attendance remains the recommended fallback.
              </p>
              {!faceChallenge ? (
                <form className="mt-4" onSubmit={(event) => void startFaceChallenge(event)}>
                  <label className="text-sm font-medium" htmlFor="face-identity-code">
                    Trainee identity code
                  </label>
                  <Input
                    id="face-identity-code"
                    className="mt-2 h-14 border-white/30 bg-slate-950 text-base uppercase text-white"
                    value={identityCode}
                    onChange={(event) => setIdentityCode(event.target.value)}
                    placeholder="NCCT-1234ABCD"
                    autoComplete="off"
                    minLength={8}
                    maxLength={32}
                    required
                  />
                  <Button
                    className="mt-3 h-14 w-full text-base"
                    type="submit"
                    disabled={!isOnline || !identityCode.trim() || isFaceProcessing}
                  >
                    <ScanFace className="h-5 w-5" aria-hidden="true" />
                    {isOnline ? "Start face challenge" : "Face check needs internet"}
                  </Button>
                </form>
              ) : (
                <div className="mt-4">
                  <div className="rounded-md bg-white p-3 text-slate-950">
                    <FaceCapture
                      instruction={faceChallenge.instruction}
                      actionLabel="Capture and verify"
                      isSubmitting={isFaceProcessing}
                      onCapture={verifyFace}
                    />
                  </div>
                  <Button
                    className="mt-3 w-full border-white/30 bg-transparent text-white hover:bg-white/10"
                    type="button"
                    variant="outline"
                    disabled={isFaceProcessing}
                    onClick={() => setFaceChallenge(null)}
                  >
                    Cancel face verification
                  </Button>
                </div>
              )}
            </section>
          ) : null}

          {deviceToken ? (
            <div className="flex flex-col gap-3">
              <Button
                className="h-12 border-white/30 bg-transparent text-white hover:bg-white/10"
                variant="outline"
                disabled={!isOnline || pendingCount === 0}
                onClick={() => void synchronize()}
              >
                <RefreshCw className="h-5 w-5" aria-hidden="true" />
                Synchronize now
              </Button>
              <Button
                className="h-12 text-slate-300 hover:bg-white/10 hover:text-white"
                variant="ghost"
                onClick={() => void resetDevice()}
              >
                Change registered device
              </Button>
            </div>
          ) : null}
        </aside>
      </div>
    </main>
  );
}
