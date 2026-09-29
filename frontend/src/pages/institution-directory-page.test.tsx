import { render, screen } from "@testing-library/react";

import { App } from "../App";
import type { AuthResponse, User } from "../lib/api/client";

const instituteAdministrator: User = {
  id: "institute-admin-1",
  email: "institute.admin@example.test",
  status: "active",
  roles: [{ code: "institute_admin", display_name: "Institute administrator" }],
  permissions: ["profiles:manage_institutions"],
  profile: { full_name: "Institute Administrator", phone: null, designation: null },
  institution: {
    id: "institution-1",
    name: "Demonstration ICM",
    code: "ICM-DEMO",
    institution_type: "icm",
  },
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "institution-token", token_type: "bearer", expires_in: 900, user };
}

describe("institution directory", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("does not offer institution creation to an institute administrator", async () => {
    window.history.pushState({}, "", "/directory/institutions");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) {
          return response(authResponse(instituteAdministrator));
        }
        if (url.includes("/api/v1/profiles/institutions")) {
          return response({ items: [], total: 0, page: 1, page_size: 12, pages: 0 });
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Institution hierarchy" })).toBeInTheDocument();
    expect(screen.queryByText("Add institution")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create institution" })).not.toBeInTheDocument();
  });
});
