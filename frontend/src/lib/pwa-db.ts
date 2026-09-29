import type {
  CourseDetail,
  LearningProgressEvent,
  LearningProgressSyncResponse,
} from "./api/client";

const DATABASE_NAME = "ncct-private-offline-learning";
const DATABASE_VERSION = 1;
const ASSET_STORE = "lesson-assets";
const COURSE_STORE = "offline-courses";
const PROGRESS_STORE = "progress-queue";

export const OFFLINE_DATA_CHANGED_EVENT = "ncct:offline-data-changed";

export type DownloadedLessonAsset = {
  key: string;
  user_id: string;
  course_id: string;
  lesson_id: string;
  content_id: string;
  language_code: string;
  title: string;
  filename: string | null;
  content_type: string | null;
  size_bytes: number;
  blob: Blob;
  downloaded_at: string;
};

export type OfflineCoursePackage = {
  key: string;
  user_id: string;
  course_id: string;
  lesson_ids: string[];
  course: CourseDetail;
  updated_at: string;
};

export type QueuedLearningProgress = LearningProgressEvent & {
  user_id: string;
  attempts: number;
  last_error: string | null;
};

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Offline storage request failed"));
  });
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(ASSET_STORE)) {
        const store = database.createObjectStore(ASSET_STORE, { keyPath: "key" });
        store.createIndex("user_id", "user_id");
      }
      if (!database.objectStoreNames.contains(COURSE_STORE)) {
        const store = database.createObjectStore(COURSE_STORE, { keyPath: "key" });
        store.createIndex("user_id", "user_id");
      }
      if (!database.objectStoreNames.contains(PROGRESS_STORE)) {
        const store = database.createObjectStore(PROGRESS_STORE, {
          keyPath: "idempotency_key",
        });
        store.createIndex("user_id", "user_id");
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Unable to open offline storage"));
  });
}

function notifyChanged() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(OFFLINE_DATA_CHANGED_EVENT));
}

function assetKey(userId: string, contentId: string) {
  return `${userId}:${contentId}`;
}

function courseKey(userId: string, courseId: string) {
  return `${userId}:${courseId}`;
}

async function put<Value>(storeName: string, value: Value): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(storeName, "readwrite");
    await requestResult(transaction.objectStore(storeName).put(value));
  } finally {
    database.close();
  }
}

async function get<Value>(storeName: string, key: string): Promise<Value | null> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(storeName, "readonly");
    const result = await requestResult(transaction.objectStore(storeName).get(key));
    return (result as Value | undefined) ?? null;
  } finally {
    database.close();
  }
}

async function remove(storeName: string, key: string): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(storeName, "readwrite");
    await requestResult(transaction.objectStore(storeName).delete(key));
  } finally {
    database.close();
  }
}

async function recordsForUser<Value>(storeName: string, userId: string): Promise<Value[]> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(storeName, "readonly");
    return await requestResult<Value[]>(
      transaction.objectStore(storeName).index("user_id").getAll(userId),
    );
  } finally {
    database.close();
  }
}

export async function saveDownloadedLessonAsset(
  asset: Omit<DownloadedLessonAsset, "key" | "downloaded_at">,
): Promise<DownloadedLessonAsset> {
  const stored: DownloadedLessonAsset = {
    ...asset,
    key: assetKey(asset.user_id, asset.content_id),
    downloaded_at: new Date().toISOString(),
  };
  await put(ASSET_STORE, stored);
  notifyChanged();
  return stored;
}

export function downloadedLessonAsset(
  userId: string,
  contentId: string,
): Promise<DownloadedLessonAsset | null> {
  return get(ASSET_STORE, assetKey(userId, contentId));
}

function offlineCourse(course: CourseDetail, lessonIds: string[]): CourseDetail {
  const selected = new Set(lessonIds);
  const sections = course.sections
    .map((section) => ({
      ...section,
      modules: section.modules
        .map((module) => ({
          ...module,
          lessons: module.lessons.filter((lesson) => selected.has(lesson.id)),
        }))
        .filter((module) => module.lessons.length > 0),
    }))
    .filter((section) => section.modules.length > 0);
  const lessons = sections.flatMap((section) =>
    section.modules.flatMap((module) => module.lessons),
  );
  return {
    ...course,
    sections,
    assignments: [],
    assessments: [],
    lesson_count: lessons.length,
    completed_lesson_count: lessons.filter((lesson) => lesson.progress.status === "completed")
      .length,
    resume_lesson_id:
      lessons.find((lesson) => lesson.progress.status !== "completed")?.id ?? lessons[0]?.id ?? null,
  };
}

export async function saveOfflineCourseLesson(
  userId: string,
  course: CourseDetail,
  lessonId: string,
): Promise<OfflineCoursePackage> {
  const existing = await offlineCoursePackage(userId, course.id);
  const lessonIds = [...new Set([...(existing?.lesson_ids ?? []), lessonId])];
  const stored: OfflineCoursePackage = {
    key: courseKey(userId, course.id),
    user_id: userId,
    course_id: course.id,
    lesson_ids: lessonIds,
    course: offlineCourse(course, lessonIds),
    updated_at: new Date().toISOString(),
  };
  await put(COURSE_STORE, stored);
  notifyChanged();
  return stored;
}

export function offlineCoursePackage(
  userId: string,
  courseId: string,
): Promise<OfflineCoursePackage | null> {
  return get(COURSE_STORE, courseKey(userId, courseId));
}

export function offlineCoursePackages(userId: string): Promise<OfflineCoursePackage[]> {
  return recordsForUser(COURSE_STORE, userId);
}

export async function enqueueLearningProgress(
  userId: string,
  event: Omit<LearningProgressEvent, "idempotency_key"> & { idempotency_key?: string },
): Promise<QueuedLearningProgress> {
  const queued: QueuedLearningProgress = {
    ...event,
    idempotency_key: event.idempotency_key ?? crypto.randomUUID(),
    user_id: userId,
    attempts: 0,
    last_error: null,
  };
  await put(PROGRESS_STORE, queued);
  notifyChanged();
  return queued;
}

export async function queuedLearningProgress(userId: string): Promise<QueuedLearningProgress[]> {
  const items = await recordsForUser<QueuedLearningProgress>(PROGRESS_STORE, userId);
  return items.sort((left, right) => left.captured_at.localeCompare(right.captured_at));
}

export async function learningProgressQueueCount(userId: string): Promise<number> {
  return (await queuedLearningProgress(userId)).length;
}

async function markRejected(event: QueuedLearningProgress, detail: string): Promise<void> {
  await put(PROGRESS_STORE, {
    ...event,
    attempts: event.attempts + 1,
    last_error: detail,
  } satisfies QueuedLearningProgress);
}

export async function synchronizeLearningProgressQueue(
  userId: string,
  synchronize: (items: LearningProgressEvent[]) => Promise<LearningProgressSyncResponse>,
): Promise<LearningProgressSyncResponse | null> {
  const queued = await queuedLearningProgress(userId);
  if (!queued.length) return null;
  const response = await synchronize(
    queued.map((event) => ({
      idempotency_key: event.idempotency_key,
      lesson_id: event.lesson_id,
      action: event.action,
      captured_at: event.captured_at,
      position_seconds: event.position_seconds,
      elapsed_seconds: event.elapsed_seconds,
    })),
  );
  const queuedById = new Map(queued.map((event) => [event.idempotency_key, event]));
  await Promise.all(
    response.items.map((result) => {
      const event = queuedById.get(result.idempotency_key);
      if (!event) return Promise.resolve();
      if (result.result === "rejected") return markRejected(event, result.detail);
      return remove(PROGRESS_STORE, result.idempotency_key);
    }),
  );
  notifyChanged();
  return response;
}

export async function offlineDownloadCount(userId: string): Promise<number> {
  return (await recordsForUser<DownloadedLessonAsset>(ASSET_STORE, userId)).length;
}

export async function clearPrivateLearningData(): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DATABASE_NAME);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error ?? new Error("Unable to clear offline learning"));
    request.onblocked = () => reject(new Error("Offline learning storage is still in use"));
  });
  notifyChanged();
}
