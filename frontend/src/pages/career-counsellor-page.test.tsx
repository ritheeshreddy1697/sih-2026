import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../App";
import type {
  AuthResponse,
  CareerConversation,
  CareerConversationSummary,
  CareerMessageExchange,
  User,
} from "../lib/api/client";

const trainee: User = {
  id: "career-trainee-1",
  email: "career.trainee@example.test",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["career:counselling"],
  profile: { full_name: "Asha Career Demonstration", phone: null, designation: null },
  institution: null,
};

const summary: CareerConversationSummary = {
  id: "conversation-1",
  language: "en",
  title: "New conversation",
  status: "active",
  last_message_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T10:00:00Z",
};

const conversation: CareerConversation = {
  ...summary,
  messages: [],
  escalation: null,
};

const exchange: CareerMessageExchange = {
  user_message: {
    id: "message-user-1",
    role: "user",
    content: "Which training programmes suit me?",
    sources: [],
    provider: null,
    created_at: "2026-09-28T10:01:00Z",
    feedback: null,
  },
  assistant_message: {
    id: "message-assistant-1",
    role: "assistant",
    content: "I found one currently available programme in the platform.",
    sources: [
      {
        source_type: "programme",
        record_id: "programme-1",
        title: "Cooperative Leadership (DEMO-01)",
        url: "/programmes/programme-1",
        summary: "Eligibility and deadline are taken from the programme record.",
      },
    ],
    provider: "platform-retrieval",
    created_at: "2026-09-28T10:01:01Z",
    feedback: null,
  },
  used_local_fallback: false,
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(): AuthResponse {
  return { access_token: "career-token", token_type: "bearer", expires_in: 900, user: trainee };
}

describe("career counsellor", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows grounded references and records feedback and support escalation", async () => {
    window.history.pushState({}, "", "/career-counsellor");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, options?: RequestInit) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse());
        if (url.endsWith("/api/v1/career/conversations") && options?.method === "GET") {
          return response([summary]);
        }
        if (url.endsWith("/api/v1/career/conversations/conversation-1")) {
          return response(conversation);
        }
        if (url.endsWith("/api/v1/career/conversations/conversation-1/messages")) {
          return response(exchange, true, 201);
        }
        if (url.endsWith("/message-assistant-1/feedback")) {
          return response({ id: "feedback-1", rating: "helpful", comment: null });
        }
        if (url.endsWith("/api/v1/career/conversations/conversation-1/escalate")) {
          return response(
            {
              id: "escalation-1",
              conversation_id: conversation.id,
              requested_by_id: trainee.id,
              requester_name: trainee.profile?.full_name,
              requester_email: trainee.email,
              reason: "I need help choosing between two paths.",
              status: "open",
              resolution_notes: null,
              resolved_at: null,
              created_at: "2026-09-28T10:02:00Z",
            },
            true,
            201,
          );
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Career counsellor" })).toBeInTheDocument();
    fireEvent.click(
      await screen.findByRole("button", { name: "Which training programmes suit me?" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(
      await screen.findByText("I found one currently available programme in the platform."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Cooperative Leadership/ })).toHaveAttribute(
      "href",
      "/programmes/programme-1",
    );

    fireEvent.click(screen.getByRole("button", { name: "Helpful" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Helpful" })).toHaveClass("bg-emerald-50"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Human support" }));
    fireEvent.change(screen.getByLabelText("What would you like help with?"), {
      target: { value: "I need help choosing between two paths." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send to support" }));
    expect(await screen.findByText("Sent to human support")).toBeInTheDocument();
  });

  it("starts a new conversation when the interface language changes", async () => {
    window.history.pushState({}, "", "/career-counsellor");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, options?: RequestInit) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse());
        if (url.endsWith("/api/v1/career/conversations") && options?.method === "GET") {
          return response([summary]);
        }
        if (url.endsWith("/api/v1/career/conversations/conversation-1")) {
          return response(conversation);
        }
        if (url.endsWith("/api/v1/career/conversations") && options?.method === "POST") {
          return response(
            {
              ...conversation,
              id: "conversation-hi",
              language: "hi",
              title: "New conversation",
            },
            true,
            201,
          );
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    await screen.findByRole("heading", { name: "Career counsellor" });
    fireEvent.click(screen.getByRole("button", { name: "हिन्दी" }));
    expect(await screen.findByRole("heading", { name: "करियर परामर्शदाता" })).toBeInTheDocument();
    expect(screen.getByText("आप किस विषय पर बात करना चाहते हैं?")).toBeInTheDocument();
  });
});
