import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../App";
import type { AuthResponse, User } from "../lib/api/client";

const instituteAdmin: User = {
  id: "admin-1",
  email: "admin@example.test",
  status: "active",
  roles: [{ code: "institute_admin", display_name: "Institute administrator" }],
  permissions: [
    "notifications:send",
    "profiles:view_private",
    "profiles:view_trainee_directory",
  ],
  profile: { full_name: "Institute Administrator", phone: null, designation: null },
  institution: { id: "institution-1", name: "Demo ICM", code: "ICM-1", institution_type: "icm" },
};

const superAdmin: User = {
  ...instituteAdmin,
  id: "super-1",
  email: "super@example.test",
  roles: [{ code: "ncct_super_admin", display_name: "NCCT super administrator" }],
  permissions: ["platform:manage", "notifications:send", "profiles:manage_institutions"],
};

const traineeTarget = {
  user_id: "trainee-1",
  full_name: "Asha Trainee",
  email: "asha@example.test",
  phone: null,
  institution: { id: "institution-1", name: "Demo ICM", code: "ICM-1", institution_type: "icm" },
  account_status: "active",
  preferred_language: null,
  preferred_location: null,
  state: null,
  skills: [],
  completion_percent: 20,
  pending_documents: 0,
  is_demo: true,
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "notification-token", token_type: "bearer", expires_in: 900, user };
}

describe("notification composer", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("allows an institute administrator to notify a selected trainee", async () => {
    window.history.pushState({}, "", "/notifications");
    const fetcher = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(instituteAdmin));
      if (url.includes("/api/v1/profiles/trainees")) {
        return response({ items: [traineeTarget], total: 1, page: 1, page_size: 100, pages: 1 });
      }
      if (url.endsWith("/api/v1/notifications") && options?.method === "POST") {
        return response({ id: "notification-1", sent_count: 1 }, true, 201);
      }
      if (url.endsWith("/api/v1/notifications")) {
        return response({ items: [], unread_count: 0 });
      }
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Send notification" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("checkbox", { name: /Asha Trainee/ }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Schedule update" } });
    fireEvent.change(screen.getByLabelText("Notification message"), { target: { value: "The session begins at ten." } });
    fireEvent.click(screen.getByRole("button", { name: "Send to 1" }));

    expect(await screen.findByText("Notification sent to 1 recipient.")).toBeInTheDocument();
    const sendCall = fetcher.mock.calls.find(
      ([url, options]) => String(url).endsWith("/api/v1/notifications") && (options as RequestInit | undefined)?.method === "POST",
    );
    expect(JSON.parse(String((sendCall?.[1] as RequestInit).body))).toEqual({
      target_type: "trainees",
      target_ids: ["trainee-1"],
      title: "Schedule update",
      description: "The session begins at ten.",
    });
  });

  it("allows a super administrator to notify a selected institution", async () => {
    window.history.pushState({}, "", "/notifications");
    const fetcher = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(superAdmin));
      if (url.includes("/api/v1/profiles/institutions")) {
        return response({
          items: [{
            id: "institution-2",
            name: "Demo RICM",
            code: "RICM-2",
            institution_type: "ricm",
            parent_id: null,
            state: null,
            district: null,
            address: null,
            contact_email: null,
            contact_phone: null,
            website: null,
            registration_number: null,
            profile_summary: null,
            is_demo: true,
            is_active: true,
            parent: null,
            children: [],
            child_count: 0,
          }],
          total: 1,
          page: 1,
          page_size: 100,
          pages: 1,
        });
      }
      if (url.endsWith("/api/v1/notifications") && options?.method === "POST") {
        return response({ id: "notification-2", sent_count: 2 }, true, 201);
      }
      if (url.endsWith("/api/v1/notifications")) return response({ items: [], unread_count: 0 });
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<App />);

    expect(await screen.findByText(/active administrators of selected institutions/)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("checkbox", { name: /Demo RICM/ }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Reporting deadline" } });
    fireEvent.change(screen.getByLabelText("Notification message"), { target: { value: "Submit the report by Friday." } });
    fireEvent.click(screen.getByRole("button", { name: "Send to 1" }));

    await waitFor(() => {
      const call = fetcher.mock.calls.find(
        ([url, options]) => String(url).endsWith("/api/v1/notifications") && (options as RequestInit | undefined)?.method === "POST",
      );
      expect(JSON.parse(String((call?.[1] as RequestInit).body)).target_type).toBe("institutions");
    });
  });
});
