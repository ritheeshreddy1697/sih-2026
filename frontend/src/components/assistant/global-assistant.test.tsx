import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { apiClient, type User } from "../../lib/api/client";
import { GlobalAssistant } from "./global-assistant";

const user: User = {
  id: "assistant-user",
  email: "trainer@example.com",
  status: "active",
  roles: [{ code: "trainer", display_name: "Trainer" }],
  permissions: ["training:deliver"],
  profile: { full_name: "Meera Shah", phone: null, designation: "Trainer" },
  institution: null,
};

describe("GlobalAssistant", () => {
  afterEach(() => {
    apiClient.setAccessToken(null);
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("sends the current page context to the authenticated assistant API", async () => {
    apiClient.setAccessToken("assistant-token");
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        answer: "Open the Programmes section to review available training.",
        provider: "gemini",
        used_local_fallback: false,
      }),
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      <MemoryRouter initialEntries={["/programmes?mode=hybrid"]}>
        <GlobalAssistant user={user} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Open AI assistant" }));
    fireEvent.change(screen.getByLabelText("Ask about this page..."), {
      target: { value: "What can I do here?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("Open the Programmes section to review available training.")).toBeInTheDocument();
    expect(screen.getByText("Gemini")).toBeInTheDocument();
    const [url, options] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url.endsWith("/api/v1/assistant/chat")).toBe(true);
    expect(options.headers).toMatchObject({ Authorization: "Bearer assistant-token" });
    expect(JSON.parse(String(options.body))).toMatchObject({
      message: "What can I do here?",
      page_path: "/programmes?mode=hybrid",
      language: "en",
    });

    await waitFor(() => {
      expect(window.sessionStorage.getItem("ncct-assistant:assistant-user")).toContain(
        "Open the Programmes section",
      );
    });
  });
});
