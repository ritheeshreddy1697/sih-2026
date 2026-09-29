import type {
  AttendanceSyncResponse,
  KioskSession,
  OfflineAttendanceEvent,
} from "./api/client";

const DATABASE_NAME = "ncct-attendance-kiosk";
const DATABASE_VERSION = 1;
const SETTINGS_STORE = "settings";
const QUEUE_STORE = "attendance-queue";

export type QueuedAttendanceEvent = OfflineAttendanceEvent & {
  attempts: number;
  last_error: string | null;
};

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed"));
  });
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(SETTINGS_STORE)) {
        database.createObjectStore(SETTINGS_STORE);
      }
      if (!database.objectStoreNames.contains(QUEUE_STORE)) {
        database.createObjectStore(QUEUE_STORE, { keyPath: "idempotency_key" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Unable to open kiosk storage"));
  });
}

async function setting<T>(key: string): Promise<T | null> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(SETTINGS_STORE, "readonly");
    const result = await requestResult(transaction.objectStore(SETTINGS_STORE).get(key));
    return (result as T | undefined) ?? null;
  } finally {
    database.close();
  }
}

async function putSetting<T>(key: string, value: T): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(SETTINGS_STORE, "readwrite");
    await requestResult(transaction.objectStore(SETTINGS_STORE).put(value, key));
  } finally {
    database.close();
  }
}

export function getDeviceToken(): Promise<string | null> {
  return setting<string>("device-token");
}

export function setDeviceToken(token: string): Promise<void> {
  return putSetting("device-token", token);
}

export function getPairedSession(): Promise<KioskSession | null> {
  return setting<KioskSession>("paired-session");
}

export function setPairedSession(session: KioskSession): Promise<void> {
  return putSetting("paired-session", session);
}

export function clearPairedSession(): Promise<void> {
  return putSetting("paired-session", null);
}

export async function enqueueAttendance(event: OfflineAttendanceEvent): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(QUEUE_STORE, "readwrite");
    await requestResult(
      transaction.objectStore(QUEUE_STORE).put({
        ...event,
        attempts: 0,
        last_error: null,
      } satisfies QueuedAttendanceEvent),
    );
  } finally {
    database.close();
  }
}

export async function queuedAttendance(): Promise<QueuedAttendanceEvent[]> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(QUEUE_STORE, "readonly");
    return await requestResult<QueuedAttendanceEvent[]>(
      transaction.objectStore(QUEUE_STORE).getAll(),
    );
  } finally {
    database.close();
  }
}

async function removeQueuedAttendance(idempotencyKey: string): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(QUEUE_STORE, "readwrite");
    await requestResult(transaction.objectStore(QUEUE_STORE).delete(idempotencyKey));
  } finally {
    database.close();
  }
}

async function markRejected(event: QueuedAttendanceEvent, detail: string): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(QUEUE_STORE, "readwrite");
    await requestResult(
      transaction.objectStore(QUEUE_STORE).put({
        ...event,
        attempts: event.attempts + 1,
        last_error: detail,
      } satisfies QueuedAttendanceEvent),
    );
  } finally {
    database.close();
  }
}

export async function synchronizeAttendanceQueue(
  synchronize: (items: OfflineAttendanceEvent[]) => Promise<AttendanceSyncResponse>,
): Promise<AttendanceSyncResponse | null> {
  const queued = await queuedAttendance();
  if (queued.length === 0) return null;

  const response = await synchronize(
    queued.map((event) => ({
      idempotency_key: event.idempotency_key,
      session_id: event.session_id,
      trainee_qr: event.trainee_qr,
      captured_at: event.captured_at,
    })),
  );
  const queuedById = new Map(queued.map((event) => [event.idempotency_key, event]));
  await Promise.all(
    response.items.map((result) => {
      const event = queuedById.get(result.idempotency_key);
      if (!event) return Promise.resolve();
      if (result.result === "rejected") return markRejected(event, result.detail);
      return removeQueuedAttendance(result.idempotency_key);
    }),
  );
  return response;
}

export async function clearKioskData(): Promise<void> {
  const database = await openDatabase();
  database.close();
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DATABASE_NAME);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error ?? new Error("Unable to clear kiosk storage"));
    request.onblocked = () => reject(new Error("Kiosk storage is still in use"));
  });
}
