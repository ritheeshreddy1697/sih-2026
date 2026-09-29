import { render, screen, waitFor } from "@testing-library/react";

import { App } from "./App";
import type { AuthResponse, DashboardResponse, User } from "./lib/api/client";

const trainee: User = {
  id: "trainee-1",
  email: "trainee@example.com",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["learning:access"],
  profile: { full_name: "Ananya Deshmukh", phone: null, designation: null },
  institution: null,
};

const authResponse: AuthResponse = {
  access_token: "access-token",
  token_type: "bearer",
  expires_in: 900,
  user: trainee,
};

const dashboardResponse: DashboardResponse = {
  dashboard_key: "trainee",
  title: "My learning",
  description: "Continue your program and meet upcoming deadlines.",
  metrics: [
    { label: "Program progress", value: "68%", change: "4 of 6 modules", tone: "accent" },
  ],
  quick_actions: [
    {
      label: "Continue learning",
      description: "Resume your next module.",
      href: "/workspace/learning",
      permission: "learning:access",
    },
  ],
  schedule_title: "Coming up",
  schedule: [
    {
      date_label: "Tomorrow",
      title: "Financial management",
      meta: "10:30 · Online",
      status: "confirmed",
    },
  ],
  activity: [
    { title: "Module completed", description: "Quiz score: 86%", time_label: "Yesterday" },
  ],
  notifications: [],
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

describe("App routes", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the public landing page", async () => {
    window.history.pushState({}, "", "/");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(response({ detail: "Refresh token is missing" }, false, 401)),
    );

    render(<App />);

    expect(
      screen.getByRole("heading", { name: "NCCT Cooperative Training Platform" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in to continue" })).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/refresh"), expect.anything()));
  });

  it("redirects an unauthenticated dashboard visit to sign in", async () => {
    window.history.pushState({}, "", "/dashboard");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(response({ detail: "Refresh token is missing" }, false, 401)),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Sign in to your workspace" }),
    ).toBeInTheDocument();
  });

  it("renders the server-selected dashboard for an authenticated user", async () => {
    window.history.pushState({}, "", "/dashboard");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse);
        if (url.endsWith("/api/v1/dashboard")) return response(dashboardResponse);
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "My learning" })).toBeInTheDocument();
    expect(screen.getByText("Program progress")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Continue learning/ })).toBeInTheDocument();
  });

  it("shows permission denied when a user lacks the route permission", async () => {
    window.history.pushState({}, "", "/admin");
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(response(authResponse)));

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Access not permitted" }),
    ).toBeInTheDocument();
  });
});
