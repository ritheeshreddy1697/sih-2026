import { Camera, CameraOff, ScanFace } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "../ui/button";

type FaceCaptureProps = {
  instruction: string;
  actionLabel: string;
  disabled?: boolean;
  isSubmitting?: boolean;
  onCapture: (frames: Blob[]) => Promise<void>;
};

function wait(milliseconds: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));
}

function captureFrame(video: HTMLVideoElement): Promise<Blob> {
  if (!video.videoWidth || !video.videoHeight) {
    return Promise.reject(new Error("Camera preview is not ready yet."));
  }
  const width = Math.min(video.videoWidth, 640);
  const height = Math.round((width / video.videoWidth) * video.videoHeight);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return Promise.reject(new Error("Camera capture is unavailable."));
  context.drawImage(video, 0, 0, width, height);
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Camera capture failed."))),
      "image/jpeg",
      0.82,
    );
  });
}

export function FaceCapture({
  instruction,
  actionLabel,
  disabled = false,
  isSubmitting = false,
  onCapture,
}: FaceCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [captureStep, setCaptureStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraActive(false);
    setCaptureStep(0);
  };

  useEffect(() => stopCamera, []);

  const startCamera = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActive(true);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Camera permission was denied or no camera is available.",
      );
    }
  };

  const captureSequence = async () => {
    if (!videoRef.current || !cameraActive) return;
    setError(null);
    try {
      const frames: Blob[] = [];
      for (let index = 0; index < 3; index += 1) {
        setCaptureStep(index + 1);
        if (index > 0) await wait(850);
        frames.push(await captureFrame(videoRef.current));
      }
      await onCapture(frames);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Face capture could not be completed.");
    } finally {
      setCaptureStep(0);
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative aspect-[4/3] min-h-56 overflow-hidden rounded-md border bg-black">
        <video
          ref={videoRef}
          className="h-full w-full object-cover [transform:scaleX(-1)]"
          muted
          playsInline
          aria-label="Live face-verification camera preview"
        />
        {!cameraActive ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-5 text-center text-slate-300">
            <ScanFace className="h-12 w-12" aria-hidden="true" />
            <p className="max-w-sm text-sm leading-6">Camera starts only after you choose it.</p>
          </div>
        ) : (
          <div className="pointer-events-none absolute inset-[12%] rounded-[45%] border-4 border-orange-400" />
        )}
      </div>
      <p className="text-sm font-medium leading-6">{instruction}</p>
      {captureStep ? (
        <p className="border-l-4 border-orange-500 bg-orange-50 px-3 py-2 text-sm text-orange-950" role="status">
          Capturing frame {captureStep} of 3. Keep following the movement instruction.
        </p>
      ) : null}
      {error ? (
        <p className="border-l-4 border-red-500 bg-red-50 px-3 py-2 text-sm text-red-950" role="alert">
          {error}
        </p>
      ) : null}
      <div className="grid gap-2 sm:grid-cols-2">
        {!cameraActive ? (
          <Button
            className="h-12"
            type="button"
            disabled={disabled || isSubmitting}
            onClick={() => void startCamera()}
          >
            <Camera className="h-5 w-5" aria-hidden="true" />
            Enable camera
          </Button>
        ) : (
          <Button
            className="h-12"
            type="button"
            disabled={disabled || isSubmitting || captureStep > 0}
            onClick={() => void captureSequence()}
          >
            <ScanFace className="h-5 w-5" aria-hidden="true" />
            {isSubmitting ? "Verifying" : actionLabel}
          </Button>
        )}
        <Button
          className="h-12"
          type="button"
          variant="outline"
          disabled={!cameraActive || isSubmitting}
          onClick={stopCamera}
        >
          <CameraOff className="h-5 w-5" aria-hidden="true" />
          Stop camera
        </Button>
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        Three temporary frames are sent over the encrypted connection and discarded after template
        extraction or verification. No photo gallery is created.
      </p>
    </div>
  );
}
