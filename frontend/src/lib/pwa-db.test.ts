import "fake-indexeddb/auto";

import type { CourseDetail } from "./api/client";
import {
  clearPrivateLearningData,
  downloadedLessonAsset,
  enqueueLearningProgress,
  learningProgressQueueCount,
  offlineCoursePackage,
  queuedLearningProgress,
  saveDownloadedLessonAsset,
  saveOfflineCourseLesson,
  synchronizeLearningProgressQueue,
} from "./pwa-db";

const course: CourseDetail = {
  id: "course-offline",
  programme_id: "programme-1",
  programme_title: "Cooperative Governance",
  programme_code: "COOP-1",
  title: "Offline learning course",
  summary: "A course used to verify private offline lesson storage.",
  status: "published",
  languages: [{ id: "language-1", code: "en", name: "English" }],
  lesson_count: 1,
  completed_lesson_count: 0,
  progress_percent: 0,
  resume_lesson_id: "lesson-1",
  resume_position_seconds: 0,
  can_manage: false,
  default_language_code: "en",
  sections: [
    {
      id: "section-1",
      title: "Foundation",
      position: 1,
      modules: [
        {
          id: "module-1",
          title: "Basics",
          description: null,
          position: 1,
          lessons: [
            {
              id: "lesson-1",
              title: "Member ownership",
              lesson_type: "pdf",
              position: 1,
              duration_seconds: null,
              is_required: true,
              contents: [
                {
                  id: "content-1",
                  language_code: "en",
                  title: "Member ownership",
                  text_content: null,
                  external_url: null,
                  filename: "ownership.pdf",
                  content_type: "application/pdf",
                  size_bytes: 8,
                  has_asset: true,
                },
              ],
              progress: {
                status: "not_started",
                last_position_seconds: 0,
                viewed_seconds: 0,
                completed_at: null,
              },
            },
          ],
        },
      ],
    },
  ],
  assignments: [],
  assessments: [],
};

describe("private PWA storage", () => {
  beforeEach(async () => {
    await clearPrivateLearningData();
  });

  afterEach(async () => {
    await clearPrivateLearningData();
  });

  it("keeps downloaded lessons scoped to the authenticated user", async () => {
    await saveDownloadedLessonAsset({
      user_id: "user-a",
      course_id: course.id,
      lesson_id: "lesson-1",
      content_id: "content-1",
      language_code: "en",
      title: "Member ownership",
      filename: "ownership.pdf",
      content_type: "application/pdf",
      size_bytes: 8,
      blob: new Blob(["%PDF-1.4"], { type: "application/pdf" }),
    });
    await saveOfflineCourseLesson("user-a", course, "lesson-1");

    expect(await downloadedLessonAsset("user-a", "content-1")).not.toBeNull();
    expect(await downloadedLessonAsset("user-b", "content-1")).toBeNull();
    expect((await offlineCoursePackage("user-a", course.id))?.lesson_ids).toEqual(["lesson-1"]);
    expect(await offlineCoursePackage("user-b", course.id)).toBeNull();
  });

  it("synchronizes a queued event exactly once after connectivity returns", async () => {
    const idempotencyKey = "295091bf-7ef3-4c62-bb3c-abfa1d27212d";
    await enqueueLearningProgress("user-a", {
      idempotency_key: idempotencyKey,
      lesson_id: "lesson-1",
      action: "complete",
      captured_at: "2026-09-28T10:00:00.000Z",
    });
    const synchronize = vi.fn().mockResolvedValue({
      items: [
        {
          idempotency_key: idempotencyKey,
          lesson_id: "lesson-1",
          result: "applied",
          detail: "Progress synchronized",
          progress: {
            status: "completed",
            last_position_seconds: 0,
            viewed_seconds: 0,
            completed_at: "2026-09-28T10:01:00.000Z",
          },
        },
      ],
      applied: 1,
      duplicates: 0,
      rejected: 0,
    });

    await synchronizeLearningProgressQueue("user-a", synchronize);
    await synchronizeLearningProgressQueue("user-a", synchronize);

    expect(synchronize).toHaveBeenCalledOnce();
    expect(await learningProgressQueueCount("user-a")).toBe(0);
  });

  it("retains rejected events with the server reason for a safe retry", async () => {
    const idempotencyKey = "45164d0f-9208-4b47-a454-f0ee605a62e2";
    await enqueueLearningProgress("user-a", {
      idempotency_key: idempotencyKey,
      lesson_id: "lesson-1",
      action: "heartbeat",
      captured_at: "2026-09-28T10:00:30.000Z",
      position_seconds: 30,
      elapsed_seconds: 30,
    });

    await synchronizeLearningProgressQueue("user-a", async () => ({
      items: [
        {
          idempotency_key: idempotencyKey,
          lesson_id: "lesson-1",
          result: "rejected",
          detail: "Active enrolment required",
          progress: null,
        },
      ],
      applied: 0,
      duplicates: 0,
      rejected: 1,
    }));

    expect(await queuedLearningProgress("user-a")).toEqual([
      expect.objectContaining({ attempts: 1, last_error: "Active enrolment required" }),
    ]);
  });
});
