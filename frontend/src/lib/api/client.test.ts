import { ApiClient, ApiError, type AuthResponse } from "./client";

const authResponse: AuthResponse = {
  access_token: "access-token",
  token_type: "bearer",
  expires_in: 900,
  user: {
    id: "user-id",
    email: "admin@example.com",
    status: "active",
    roles: [{ code: "ncct_super_admin", display_name: "NCCT super administrator" }],
    permissions: [
      "platform:manage",
      "institution:manage",
      "training:deliver",
      "learning:access",
      "nominations:manage",
      "recruitment:access",
      "programmes:view",
      "programmes:manage",
      "programmes:approve",
      "applications:apply",
      "applications:review",
      "nominations:create",
      "profiles:self",
      "profiles:view_private",
      "profiles:manage_institutions",
      "profiles:validate_documents",
    ],
    profile: { full_name: "Demo Admin", phone: null, designation: null },
    institution: null,
  },
};

describe("ApiClient", () => {
  it("fetches health status", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok", service: "test-api" }),
    });
    const client = new ApiClient({ baseUrl: "http://api.test", fetcher });

    await expect(client.health()).resolves.toEqual({ status: "ok", service: "test-api" });
    expect(fetcher).toHaveBeenCalledWith("http://api.test/api/v1/health", {
      method: "GET",
      body: undefined,
      credentials: "include",
      headers: { Accept: "application/json" },
    });
  });

  it("uses the current browser fetch with the correct global receiver", async () => {
    const originalFetch = globalThis.fetch;
    const browserFetch = vi.fn(function (this: typeof globalThis) {
      if (this !== globalThis) throw new TypeError("Illegal invocation");
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok", service: "browser-api" }),
      } as Response);
    });
    const client = new ApiClient({ baseUrl: "http://api.test" });
    globalThis.fetch = browserFetch as typeof fetch;

    try {
      await expect(client.health()).resolves.toEqual({ status: "ok", service: "browser-api" });
      expect(browserFetch).toHaveBeenCalledOnce();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("stores an access token for protected requests after login", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => authResponse })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => authResponse.user });
    const client = new ApiClient({ baseUrl: "http://api.test", fetcher });

    await client.login("admin@example.com", "DemoOnly!2026");
    await client.me();

    expect(fetcher).toHaveBeenLastCalledWith("http://api.test/api/v1/auth/me", {
      method: "GET",
      body: undefined,
      credentials: "include",
      headers: { Accept: "application/json", Authorization: "Bearer access-token" },
    });
  });

  it("throws ApiError with the API detail for failed requests", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Service unavailable" }),
    });
    const client = new ApiClient({ baseUrl: "http://api.test", fetcher });

    await expect(client.health()).rejects.toEqual(new ApiError("Service unavailable", 503));
  });

  it("sends programme filters and multipart documents through authenticated requests", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => authResponse })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ items: [], total: 0 }) })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: "document-1", filename: "proof.pdf" }),
      });
    const client = new ApiClient({ baseUrl: "http://api.test", fetcher });

    await client.login("admin@example.com", "DemoOnly!2026");
    await client.programmes({ q: "credit", mode: "hybrid" });
    const file = new File(["proof"], "proof.pdf", { type: "application/pdf" });
    await client.uploadApplicationDocument("application-1", "eligibility", file);

    expect(fetcher.mock.calls[1][0]).toBe(
      "http://api.test/api/v1/programmes?q=credit&mode=hybrid",
    );
    const uploadOptions = fetcher.mock.calls[2][1] as RequestInit;
    expect(uploadOptions.body).toBeInstanceOf(FormData);
    expect(uploadOptions.headers).toEqual({
      Accept: "application/json",
      Authorization: "Bearer access-token",
    });
  });

  it("sends profile pagination filters and multipart profile documents", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => authResponse })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, page: 2, page_size: 20, pages: 0 }),
      })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ documents: [] }) });
    const client = new ApiClient({ baseUrl: "http://api.test", fetcher });

    await client.login("admin@example.com", "DemoOnly!2026");
    await client.trainees({ skill: "audit", minimum_completion: 75, page: 2 });
    await client.uploadProfileDocument(
      "education",
      new File(["proof"], "degree.pdf", { type: "application/pdf" }),
    );

    expect(fetcher.mock.calls[1][0]).toBe(
      "http://api.test/api/v1/profiles/trainees?skill=audit&minimum_completion=75&page=2",
    );
    const uploadOptions = fetcher.mock.calls[2][1] as RequestInit;
    expect(uploadOptions.body).toBeInstanceOf(FormData);
    expect(uploadOptions.headers).not.toHaveProperty("Content-Type");
  });

  it("authenticates kiosk synchronization with the registered device token", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], accepted: 0, duplicates: 0, rejected: 0 }),
    });
    const client = new ApiClient({ baseUrl: "http://api.test", fetcher });

    await client.syncKioskAttendance("device-token", [
      {
        idempotency_key: "8f05c7a7-91ed-47d8-909a-27d6dd02d865",
        session_id: "6acb9d76-2b2f-443f-90d2-e159dc9640e0",
        trainee_qr: "NCCT-TRAINEE:signed-value",
        captured_at: "2026-09-27T10:30:00.000Z",
      },
    ]);

    expect(fetcher).toHaveBeenCalledWith(
      "http://api.test/api/v1/attendance/kiosk/check-ins/sync",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-Kiosk-Token": "device-token" }),
      }),
    );
  });
});
