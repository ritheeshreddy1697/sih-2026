import { fireEvent, render, screen } from "@testing-library/react";

import { App } from "../App";
import type {
  AssessmentAttempt,
  AuthResponse,
  CourseDetail,
  CourseListItem,
  User,
} from "../lib/api/client";

const trainee: User = {
  id: "trainee-learning-1",
  email: "trainee.learning@example.com",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["learning:access", "programmes:view", "applications:apply"],
  profile: { full_name: "Asha Learning Demo", phone: null, designation: null },
  institution: null,
};

const courseItem: CourseListItem = {
  id: "course-1",
  programme_id: "programme-1",
  programme_title: "Cooperative Governance",
  programme_code: "CGOV-DEMO",
  title: "Cooperative Governance Learning Journey",
  summary: "A demonstration course for member-led governance.",
  status: "published",
  languages: [
    { id: "language-en", code: "en", name: "English" },
    { id: "language-hi", code: "hi", name: "Hindi" },
  ],
  lesson_count: 4,
  completed_lesson_count: 1,
  progress_percent: 25,
  resume_lesson_id: "lesson-1",
  resume_position_seconds: 42,
  can_manage: false,
};

const courseDetail: CourseDetail = {
  ...courseItem,
  default_language_code: "en",
  sections: [
    {
      id: "section-1",
      title: "Foundation",
      position: 1,
      modules: [
        {
          id: "module-1",
          title: "Orientation",
          description: null,
          position: 1,
          lessons: [
            {
              id: "lesson-1",
              title: "Member ownership",
              lesson_type: "text",
              position: 1,
              duration_seconds: null,
              is_required: true,
              contents: [
                {
                  id: "content-1",
                  language_code: "en",
                  title: "Member ownership",
                  text_content: "A cooperative is owned and governed by its members.",
                  external_url: null,
                  filename: null,
                  content_type: null,
                  size_bytes: null,
                  has_asset: false,
                },
              ],
              progress: {
                status: "in_progress",
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
  assessments: [
    {
      id: "assessment-1",
      title: "Foundation quiz",
      instructions: "Choose the correct response.",
      assessment_type: "quiz",
      attempt_limit: 2,
      attempts_used: 0,
      attempts_remaining: 2,
      passing_score_percent: 60,
      best_score_percent: null,
      passed: false,
      is_published: true,
    },
  ],
};

const inProgressAttempt: AssessmentAttempt = {
  id: "attempt-1",
  assessment_id: "assessment-1",
  assessment_title: "Foundation quiz",
  attempt_number: 1,
  status: "in_progress",
  questions: [
    {
      id: "question-1",
      prompt: "Who owns a cooperative?",
      choices: ["Members", "One supplier"],
      points: 1,
      position: 1,
    },
  ],
  score_percent: null,
  points_earned: null,
  points_available: null,
  passed: null,
  grading_details: [],
  trainer_feedback: null,
  started_at: "2026-09-27T10:00:00Z",
  submitted_at: null,
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(): AuthResponse {
  return { access_token: "learning-access-token", token_type: "bearer", expires_in: 900, user: trainee };
}

describe("learning pages", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows course progress and links directly to the resume lesson", async () => {
    window.history.pushState({}, "", "/learning");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse());
        if (url.endsWith("/api/v1/learning/courses")) {
          return response({ items: [courseItem], total: 1 });
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Cooperative Governance Learning Journey" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: /learning journey progress/i })).toHaveAttribute(
      "aria-valuenow",
      "25",
    );
    expect(screen.getByRole("link", { name: /resume course/i })).toHaveAttribute(
      "href",
      "/learning/courses/course-1?lesson=lesson-1",
    );
  });

  it("submits answers only and displays the server-computed assessment result", async () => {
    window.history.pushState({}, "", "/learning/courses/course-1?lesson=lesson-1");
    let submittedBody: Record<string, unknown> | null = null;
    const fetcher = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse());
      if (url.endsWith("/api/v1/learning/courses/course-1")) return response(courseDetail);
      if (url.endsWith("/api/v1/learning/lessons/lesson-1/start")) {
        return response(courseDetail.sections[0].modules[0].lessons[0].progress);
      }
      if (url.endsWith("/api/v1/learning/assessments/assessment-1/attempts")) {
        return response(inProgressAttempt);
      }
      if (url.endsWith("/api/v1/learning/attempts/attempt-1/submit")) {
        submittedBody = JSON.parse(String(options?.body)) as Record<string, unknown>;
        return response({
          ...inProgressAttempt,
          status: "submitted",
          score_percent: 100,
          points_earned: 1,
          points_available: 1,
          passed: true,
          grading_details: [
            {
              question_id: "question-1",
              selected_option_index: 0,
              correct: true,
              points_earned: 1,
              explanation: "Members own the cooperative.",
            },
          ],
          submitted_at: "2026-09-27T10:05:00Z",
        });
      }
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<App />);

    expect(await screen.findByText("A cooperative is owned and governed by its members.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Begin" }));
    expect(await screen.findByText(/Who owns a cooperative\?/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Members"));
    fireEvent.click(screen.getByRole("button", { name: "Submit for grading" }));

    expect(await screen.findByText("100%")).toBeInTheDocument();
    expect(screen.getByText("1 of 1 points")).toBeInTheDocument();
    expect(submittedBody).toEqual({
      answers: [{ question_id: "question-1", option_index: 0 }],
    });
    expect(submittedBody).not.toHaveProperty("score_percent");
    expect(submittedBody).not.toHaveProperty("passed");
  });
});
