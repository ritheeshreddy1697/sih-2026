import { fireEvent, render, screen } from "@testing-library/react";

import { App } from "../App";
import type { AuthResponse, Programme, User } from "../lib/api/client";

const trainee: User = {
  id: "trainee-1",
  email: "trainee@example.com",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["learning:access", "programmes:view", "applications:apply"],
  profile: { full_name: "Ananya Deshmukh", phone: null, designation: null },
  institution: null,
};

const programme: Programme = {
  id: "programme-1",
  institution: { id: "institution-1", name: "VAMNICOM", code: "VAMNICOM" },
  title: "Cooperative Governance and Leadership",
  code: "CGOV-01",
  summary: "Build practical skills for accountable cooperative governance.",
  description: "Detailed programme content for cooperative governance and leadership.",
  mode: "hybrid",
  status: "published",
  eligibility_criteria: "Open to cooperative-sector learners.",
  eligible_applicant_types: ["individual", "pacs"],
  capacity: 40,
  available_capacity: 21,
  location: "Pune",
  language: "English and Hindi",
  duration_days: 5,
  application_deadline: "2026-10-20T10:00:00Z",
  start_date: "2026-11-02",
  end_date: "2026-11-06",
  can_apply: true,
  has_applied: false,
  rejection_reason: null,
  batches: [],
  application_count: 0,
  nomination_count: 0,
  approved_count: 0,
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "access-token", token_type: "bearer", expires_in: 900, user };
}

describe("programme workflow pages", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows only the eligible published catalogue controls to a trainee", async () => {
    window.history.pushState({}, "", "/programmes");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(trainee));
        if (url.includes("/api/v1/programmes")) {
          return response({ items: [programme], total: 1 });
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Cooperative Governance and Leadership" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Create programme" })).not.toBeInTheDocument();
    expect(screen.getByText("21 of 40 seats available")).toBeInTheDocument();
  });

  it("submits a trainee application from programme details", async () => {
    window.history.pushState({}, "", "/programmes/programme-1");
    const fetcher = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(trainee));
      if (url.endsWith("/api/v1/programmes/programme-1/applications")) {
        expect(options?.method).toBe("POST");
        return response({ id: "application-1", status: "submitted" }, true, 201);
      }
      if (url.endsWith("/api/v1/programmes/programme-1")) return response(programme);
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Cooperative Governance and Leadership" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Why do you want to attend/), {
      target: { value: "I support a cooperative credit society." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit application" }));

    expect(await screen.findByText("Your application has been submitted.")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith(
      expect.stringContaining("/programmes/programme-1/applications"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
