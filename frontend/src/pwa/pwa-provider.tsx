import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "../auth/auth-context-value";
import { useI18n } from "../i18n/i18n-provider";
import {
  apiClient,
  type LearningProgressEvent,
  type LearningProgressSyncResponse,
} from "../lib/api/client";
import {
  enqueueLearningProgress,
  learningProgressQueueCount,
  OFFLINE_DATA_CHANGED_EVENT,
  offlineDownloadCount,
  synchronizeLearningProgressQueue,
} from "../lib/pwa-db";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

type PwaContextValue = {
  isOnline: boolean;
  isReducedData: boolean;
  setReducedData: (enabled: boolean) => void;
  queueCount: number;
  downloadCount: number;
  isSyncing: boolean;
  installAvailable: boolean;
  updateAvailable: boolean;
  queueProgress: (
    event: Omit<LearningProgressEvent, "idempotency_key">,
  ) => Promise<LearningProgressSyncResponse | null>;
  syncProgress: () => Promise<LearningProgressSyncResponse | null>;
  install: () => Promise<void>;
  applyUpdate: () => void;
  refreshOfflineState: () => Promise<void>;
};

const defaultValue: PwaContextValue = {
  isOnline: true,
  isReducedData: false,
  setReducedData: () => undefined,
  queueCount: 0,
  downloadCount: 0,
  isSyncing: false,
  installAvailable: false,
  updateAvailable: false,
  queueProgress: async () => null,
  syncProgress: async () => null,
  install: async () => undefined,
  applyUpdate: () => undefined,
  refreshOfflineState: async () => undefined,
};

const PwaContext = createContext<PwaContextValue>(defaultValue);

function prefersReducedData() {
  const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
  return Boolean(connection?.saveData);
}

function initialReducedData() {
  const stored = window.localStorage?.getItem("ncct-reduced-data") ?? null;
  return stored === null ? prefersReducedData() : stored === "true";
}

export function PwaProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isReducedData, setReducedDataState] = useState(initialReducedData);
  const [queueCount, setQueueCount] = useState(0);
  const [downloadCount, setDownloadCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const syncPromiseRef = useRef<Promise<LearningProgressSyncResponse | null> | null>(null);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  const refreshOfflineState = useCallback(async () => {
    if (!user || typeof indexedDB === "undefined") {
      setQueueCount(0);
      setDownloadCount(0);
      return;
    }
    const [queued, downloaded] = await Promise.all([
      learningProgressQueueCount(user.id),
      offlineDownloadCount(user.id),
    ]);
    setQueueCount(queued);
    setDownloadCount(downloaded);
  }, [user]);

  const syncProgress = useCallback(async () => {
    if (!user || !navigator.onLine) return null;
    if (syncPromiseRef.current) return syncPromiseRef.current;
    const operation = (async () => {
      setIsSyncing(true);
      try {
        return await synchronizeLearningProgressQueue(user.id, (events) =>
          apiClient.syncLessonProgress(events),
        );
      } finally {
        setIsSyncing(false);
        await refreshOfflineState();
      }
    })();
    syncPromiseRef.current = operation;
    try {
      return await operation;
    } finally {
      if (syncPromiseRef.current === operation) syncPromiseRef.current = null;
    }
  }, [refreshOfflineState, user]);

  const queueProgress = useCallback(
    async (event: Omit<LearningProgressEvent, "idempotency_key">) => {
      if (!user) return null;
      const queued = await enqueueLearningProgress(user.id, event);
      if (!navigator.onLine) {
        await refreshOfflineState();
        return null;
      }
      let response = await syncProgress();
      if (!response?.items.some((item) => item.idempotency_key === queued.idempotency_key)) {
        response = await syncProgress();
      }
      return response;
    },
    [refreshOfflineState, syncProgress, user],
  );

  useEffect(() => {
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  useEffect(() => {
    const changed = () => void refreshOfflineState();
    window.addEventListener(OFFLINE_DATA_CHANGED_EVENT, changed);
    void refreshOfflineState();
    return () => window.removeEventListener(OFFLINE_DATA_CHANGED_EVENT, changed);
  }, [refreshOfflineState]);

  useEffect(() => {
    if (isOnline && queueCount) void syncProgress().catch(() => undefined);
  }, [isOnline, queueCount, syncProgress]);

  useEffect(() => {
    const beforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    const installed = () => setInstallPrompt(null);
    const updateReady = () => setUpdateAvailable(true);
    window.addEventListener("beforeinstallprompt", beforeInstall);
    window.addEventListener("appinstalled", installed);
    window.addEventListener("ncct:pwa-update-ready", updateReady);
    return () => {
      window.removeEventListener("beforeinstallprompt", beforeInstall);
      window.removeEventListener("appinstalled", installed);
      window.removeEventListener("ncct:pwa-update-ready", updateReady);
    };
  }, []);

  const setReducedData = useCallback((enabled: boolean) => {
    window.localStorage?.setItem("ncct-reduced-data", String(enabled));
    document.documentElement.dataset.reducedData = String(enabled);
    setReducedDataState(enabled);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.reducedData = String(isReducedData);
  }, [isReducedData]);

  const value = useMemo<PwaContextValue>(
    () => ({
      isOnline,
      isReducedData,
      setReducedData,
      queueCount,
      downloadCount,
      isSyncing,
      installAvailable: Boolean(installPrompt),
      updateAvailable,
      queueProgress,
      syncProgress,
      install: async () => {
        if (!installPrompt) return;
        await installPrompt.prompt();
        await installPrompt.userChoice;
        setInstallPrompt(null);
      },
      applyUpdate: () => {
        void navigator.serviceWorker?.getRegistration().then((registration) => {
          if (!registration?.waiting) return;
          navigator.serviceWorker.addEventListener(
            "controllerchange",
            () => window.location.reload(),
            { once: true },
          );
          registration.waiting.postMessage({ type: "SKIP_WAITING" });
        });
      },
      refreshOfflineState,
    }),
    [
      downloadCount,
      installPrompt,
      isOnline,
      isReducedData,
      isSyncing,
      queueCount,
      queueProgress,
      refreshOfflineState,
      setReducedData,
      syncProgress,
      updateAvailable,
    ],
  );

  return (
    <PwaContext.Provider value={value}>
      {!isOnline && !user ? (
        <div className="fixed inset-x-0 bottom-0 z-50 border-t border-amber-300 bg-amber-100 px-4 py-3 text-center text-sm font-medium text-amber-950" role="status" aria-live="polite">
          {t("pwa.offlineHint")}
        </div>
      ) : null}
      {children}
    </PwaContext.Provider>
  );
}

export function usePwa() {
  return useContext(PwaContext);
}
