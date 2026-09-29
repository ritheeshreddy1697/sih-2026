import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../App";
import type { AuthResponse, TraineeProfile, User } from "../lib/api/client";

const trainee: User = {
  id: "trainee-profile-1",
  email: "asha@example.test",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["learning:access", "profiles:self"],
  profile: { full_name: "Asha Demonstration", phone: "9000000001", designation: null },
  institution: null,
};

const administrator: User = {
  id: "admin-profile-1",
  email: "admin@example.test",
  status: "active",
  roles: [{ code: "institute_admin", display_name: "Institute administrator" }],
  permissions: [
    "institution:manage",
    "profiles:view_trainee_directory",
    "profiles:view_private",
    "profiles:manage_institutions",
    "profiles:validate_documents",
  ],
  profile: { full_name: "Demonstration Administrator", phone: null, designation: null },
  institution: {
    id: "institution-1",
    name: "Demonstration ICM",
    code: "ICM-DEMO",
    institution_type: "icm",
  },
};

const trainer: User = {
  id: "trainer-profile-1",
  email: "trainer@example.test",
  status: "active",
  roles: [{ code: "trainer", display_name: "Trainer" }],
  permissions: ["profiles:view_trainee_directory"],
  profile: { full_name: "Demonstration Trainer", phone: null, designation: "Trainer" },
  institution: {
    id: "institution-1",
    name: "Demonstration ICM",
    code: "ICM-DEMO",
    institution_type: "icm",
  },
};

const profile: TraineeProfile = {
  user_id: trainee.id,
  full_name: "Asha Demonstration",
  email: trainee.email,
  phone: "9000000001",
  institution: {
    id: "pacs-1",
    name: "PACS Demonstration Society",
    code: "PACS-DEMO",
    institution_type: "pacs",
  },
  account_status: "active",
  preferred_language: "Marathi",
  preferred_location: "Pune",
  state: "Maharashtra",
  skills: ["Bookkeeping"],
  completion_percent: 80,
  pending_documents: 1,
  is_demo: true,
  designation: "Member services assistant",
  date_of_birth: "1996-08-12",
  gender: "Woman",
  alternate_email: null,
  address_line: "Demonstration address",
  city: "Pune",
  postal_code: "411001",
  career_interests: "Cooperative governance",
  completion: {
    percent: 80,
    completed_sections: ["Personal information"],
    missing_sections: ["Documents"],
  },
  education: [],
  employment: [],
  memberships: [],
  documents: [
    {
      id: "document-1",
      document_type: "identity",
      filename: "demonstration-identity.pdf",
      content_type: "application/pdf",
      size_bytes: 1024,
      validation_status: "pending",
      validation_notes: null,
      validated_by_name: null,
      validated_at: null,
      uploaded_at: "2026-09-27T10:00:00Z",
    },
  ],
  enrollments: [],
  consent_preferences: {
    placement_visibility_consent: true,
    communication_consent: true,
    data_sharing_consent: false,
  },
  audit_history: [],
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "profile-token", token_type: "bearer", expires_in: 900, user };
}

describe("profile management pages", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders completion and saves trainee personal information", async () => {
    window.history.pushState({}, "", "/profile");
    const fetcher = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(trainee));
      if (url.endsWith("/api/v1/profiles/me") && options?.method === "PATCH") {
        return response({ ...profile, phone: "9111111111" });
      }
      if (url.endsWith("/api/v1/profiles/me")) return response(profile);
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "My profile" })).toBeInTheDocument();
    expect(await screen.findByText("80%")).toBeInTheDocument();
    expect(await screen.findByText("demonstration-identity.pdf")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Phone"), { target: { value: "9111111111" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByText("Personal details saved.")).toBeInTheDocument();
    const patchCall = fetcher.mock.calls.find(
      ([url, options]) =>
        String(url).endsWith("/api/v1/profiles/me") &&
        (options as RequestInit | undefined)?.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    expect(JSON.parse(String((patchCall?.[1] as RequestInit).body))).toMatchObject({
      phone: "9111111111",
      skills: ["Bookkeeping"],
    });
  });

  it("renders an administrator-scoped paginated trainee directory", async () => {
    window.history.pushState({}, "", "/directory/trainees");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(administrator));
        if (url.includes("/api/v1/profiles/trainers")) {
          return response({
            items: [{
              user_id: "trainer-1",
              full_name: "Meera Trainer",
              email: "meera.trainer@example.test",
              phone: "9000000002",
              designation: "Senior trainer",
              institution: profile.institution,
              account_status: "active",
            }],
            total: 1,
            page: 1,
            page_size: 12,
            pages: 1,
          });
        }
        if (url.includes("/api/v1/profiles/trainees")) {
          return response({ items: [profile], total: 13, page: 1, page_size: 12, pages: 2 });
        }
        if (url.includes("/api/v1/profiles/institutions")) {
          return response({ items: [], total: 0, page: 1, page_size: 100, pages: 0 });
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "People directory" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Asha Demonstration" })).toBeInTheDocument();
    expect(screen.getByText(`ID: ${profile.user_id}`)).toBeInTheDocument();
    expect(screen.getByText("Demonstration data")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open private profile/ })).toHaveAttribute(
      "href",
      `/directory/trainees/${profile.user_id}`,
    );
    expect(screen.getByRole("navigation", { name: "Trainee pages" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("13 trainee profiles")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("tab", { name: "Trainers" }));
    expect(await screen.findByRole("heading", { name: "Meera Trainer" })).toBeInTheDocument();
    expect(screen.getByText("ID: trainer-1")).toBeInTheDocument();
  });

  it("shows a trainer only the assigned-trainee directory", async () => {
    window.history.pushState({}, "", "/directory/trainees");
    const fetcher = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(trainer));
      if (url.includes("/api/v1/profiles/trainees")) {
        return response({ items: [profile], total: 1, page: 1, page_size: 12, pages: 1 });
      }
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "People directory" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Asha Demonstration" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Trainees" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Trainers" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Open private profile/ })).not.toBeInTheDocument();
    expect(screen.getByText(/enrolled in your assigned batches/)).toBeInTheDocument();
    expect(fetcher.mock.calls.some(([url]) => String(url).includes("/profiles/institutions"))).toBe(false);
  });
});
