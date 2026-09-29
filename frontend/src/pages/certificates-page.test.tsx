import { render, screen } from "@testing-library/react";

import { App } from "../App";
import type {
  AuthResponse,
  CertificateVerification,
  DigitalCertificate,
  SkillWallet,
  User,
} from "../lib/api/client";

const trainee: User = {
  id: "trainee-certificate-1",
  email: "trainee.certificate@example.com",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["certificates:self"],
  profile: { full_name: "Asha Certificate Demo", phone: null, designation: null },
  institution: null,
};

const certificate: DigitalCertificate = {
  id: "certificate-1",
  enrollment_id: "enrollment-1",
  certificate_number: "NCCT-2026-DEMO123",
  title: "Certificate of Cooperative Leadership",
  recipient_name: "Asha Certificate Demo",
  recipient_email: "trainee.certificate@example.com",
  programme_id: "programme-1",
  programme_title: "Cooperative Leadership Programme",
  programme_code: "CLP-DEMO",
  institution_name: "ICM Pune Demonstration Centre",
  state: "valid",
  valid: true,
  metrics: {
    course_completion_percent: 100,
    attendance_percent: 88,
    assessment_score_percent: 84,
  },
  issued_at: "2026-09-20T10:00:00Z",
  expires_at: "2028-09-20T10:00:00Z",
  revoked_at: null,
  revocation_reason: null,
  verification_url: "http://localhost:5173/verify/certificate/demo-token",
  audit_history: [],
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({
    ok,
    status,
    json: async () => body,
    blob: async () => new Blob(["certificate"]),
  });
}

function authResponse(): AuthResponse {
  return {
    access_token: "certificate-access-token",
    token_type: "bearer",
    expires_in: 900,
    user: trainee,
  };
}

describe("certificate pages", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows issued achievements in the trainee skill wallet", async () => {
    window.history.pushState({}, "", "/certificates");
    const wallet: SkillWallet = { certificates: [certificate], total: 1, valid_count: 1 };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse());
        if (url.endsWith("/api/v1/certificates/wallet/me")) return response(wallet);
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Digital skill wallet" })).toBeInTheDocument();
    expect(await screen.findByText("Certificate of Cooperative Leadership")).toBeInTheDocument();
    expect(screen.getByText("NCCT-2026-DEMO123")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download PDF" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share" })).toBeInTheDocument();
  });

  it("shows a revoked public certificate as invalid without private fields", async () => {
    window.history.pushState({}, "", "/verify/certificate/revoked-demo-token");
    const publicCertificate: CertificateVerification = {
      certificate_number: "NCCT-2026-REVOKED1",
      title: "Certificate of Cooperative Leadership",
      recipient_name: "Asha Certificate Demo",
      programme_title: "Cooperative Leadership Programme",
      institution_name: "ICM Pune Demonstration Centre",
      state: "revoked",
      valid: false,
      issued_at: "2026-09-20T10:00:00Z",
      expires_at: "2028-09-20T10:00:00Z",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) {
          return response({ detail: "No session" }, false, 401);
        }
        if (url.endsWith("/api/v1/certificates/verify/revoked-demo-token")) {
          return response(publicCertificate);
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Revoked certificate" })).toBeInTheDocument();
    expect(screen.getByText("This certificate is no longer valid.")).toBeInTheDocument();
    expect(screen.getByText("Asha Certificate Demo")).toBeInTheDocument();
    expect(screen.queryByText("trainee.certificate@example.com")).not.toBeInTheDocument();
    expect(screen.queryByText(/revocation reason/i)).not.toBeInTheDocument();
  });
});
