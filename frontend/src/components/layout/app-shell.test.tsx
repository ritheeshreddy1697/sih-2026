import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AuthContext, type AuthContextValue } from "../../auth/auth-context-value";
import { apiClient, type User } from "../../lib/api/client";
import { AppShell } from "./app-shell";

const user: User = {
  id: "user-1",
  email: "trainer@example.com",
  status: "active",
  roles: [{ code: "trainer", display_name: "Trainer" }],
  permissions: ["training:deliver"],
  profile: { full_name: "Meera Shah", phone: null, designation: "Trainer" },
  institution: null,
};

const authValue: AuthContextValue = {
  user,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  can: (permission) => user.permissions.includes(permission),
  canAny: (permissions) => permissions.some((permission) => user.permissions.includes(permission)),
};

describe("AppShell", () => {
  afterEach(() => {
    apiClient.setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it("opens the mobile navigation, moves focus and closes with Escape", () => {
    render(
      <MemoryRouter>
        <AuthContext.Provider value={authValue}>
          <AppShell user={user} onLogout={vi.fn()}>
            <p>Workspace content</p>
          </AppShell>
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));

    const mobileNavigation = screen.getByRole("navigation", {
      name: "Mobile workspace navigation",
    });
    expect(mobileNavigation).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Dashboard" }).at(-1)).toHaveFocus();
    expect(screen.queryByRole("link", { name: "My learning" })).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(
      screen.queryByRole("navigation", { name: "Mobile workspace navigation" }),
    ).not.toBeInTheDocument();
  });

  it("exposes notifications and profile actions with accessible controls", () => {
    render(
      <MemoryRouter>
        <AuthContext.Provider value={authValue}>
          <AppShell
            user={user}
            onLogout={vi.fn()}
            notifications={[
              {
                id: "notice-1",
                title: "Assessment due",
                description: "Review five submissions.",
                unread: true,
              },
            ]}
          >
            <p>Workspace content</p>
          </AppShell>
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Notifications, 1 unread" }));
    expect(screen.getByRole("region", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByText("Assessment due")).toBeInTheDocument();

    fireEvent.pointerDown(screen.getByText("Assessment due"));
    expect(screen.getByRole("region", { name: "Notifications" })).toBeInTheDocument();

    fireEvent.pointerDown(screen.getByText("Workspace content"));
    expect(screen.queryByRole("region", { name: "Notifications" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Notifications, 1 unread" }));

    fireEvent.click(screen.getByRole("button", { name: "Open profile menu" }));
    expect(screen.getByRole("menuitem", { name: "My profile" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Sign out" })).toBeInTheDocument();
  });

  it("exposes keyboard-accessible language and reduced-data preferences", () => {
    render(
      <MemoryRouter>
        <AuthContext.Provider value={authValue}>
          <AppShell user={user} onLogout={vi.fn()}>
            <p>Workspace content</p>
          </AppShell>
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    const preferences = screen.getByRole("button", { name: "App preferences" });
    preferences.focus();
    fireEvent.keyDown(preferences, { key: "Enter" });
    fireEvent.click(preferences);

    expect(screen.getByRole("dialog", { name: "App preferences" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Language" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Reduced-data mode/ })).toBeInTheDocument();
  });

  it("loads delivered notifications and marks them as read", async () => {
    apiClient.setAccessToken("notification-token");
    const fetcher = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/api/v1/notifications/notification-1/read")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: "notification-1",
            title: "New schedule",
            description: "The batch begins tomorrow.",
            sender_name: "Institute Administrator",
            created_at: "2026-09-30T08:00:00Z",
            unread: false,
          }),
        });
      }
      expect(options?.method).toBe("GET");
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [{
            id: "notification-1",
            title: "New schedule",
            description: "The batch begins tomorrow.",
            sender_name: "Institute Administrator",
            created_at: "2026-09-30T08:00:00Z",
            unread: true,
          }],
          unread_count: 1,
        }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      <MemoryRouter>
        <AuthContext.Provider value={authValue}>
          <AppShell user={user} onLogout={vi.fn()}><p>Workspace content</p></AppShell>
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Notifications, 1 unread" }));
    fireEvent.click(screen.getByRole("button", { name: /New schedule/ }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument());
    expect(fetcher.mock.calls.some(([url]) => String(url).endsWith("/notification-1/read"))).toBe(true);
  });
});
