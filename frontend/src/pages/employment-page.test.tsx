import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../App";
import type {
  AuthResponse,
  EmployerWorkspace,
  Job,
  TraineeEmploymentWorkspace,
  User,
} from "../lib/api/client";

const trainee: User = {
  id: "employment-trainee-1",
  email: "trainee.employment@example.test",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["employment:self"],
  profile: { full_name: "Asha Employment Demonstration", phone: null, designation: null },
  institution: null,
};

const employer: User = {
  id: "employment-employer-1",
  email: "recruiter.employment@example.test",
  status: "active",
  roles: [{ code: "employer_recruiter", display_name: "Employer / recruiter" }],
  permissions: ["employment:manage"],
  profile: { full_name: "Demonstration Recruiter", phone: null, designation: null },
  institution: {
    id: "employer-institution-1",
    name: "Fictional Cooperative Services Limited",
    code: "EMP-DEMO",
    institution_type: "employer",
  },
};

const job: Job = {
  id: "job-1",
  employer_profile_id: "employer-profile-1",
  company_name: "Fictional Cooperative Services Limited",
  title: "Digital Services Coordinator",
  description: "Support cooperative members through responsible digital service delivery.",
  location: "Hyderabad, Telangana",
  employment_type: "full_time",
  workplace_mode: "hybrid",
  required_skills: ["Digital member services"],
  preferred_skills: ["Member support"],
  minimum_experience_years: 0,
  vacancies: 2,
  salary_minimum: 300000,
  salary_maximum: 450000,
  application_deadline: "2026-11-01T00:00:00Z",
  status: "published",
  published_at: "2026-09-28T10:00:00Z",
  closed_at: null,
  required_programmes: [
    { id: "programme-1", code: "DIGI-DEMO", title: "Digital Services for Cooperatives" },
  ],
  saved: false,
  application_status: null,
  match: {
    score: 100,
    skill_score: 40,
    course_score: 25,
    location_score: 20,
    interest_score: 15,
    reasons: [
      "1 of 1 required verified skills match",
      "1 of 1 required certified courses match",
      "Work location matches a preference or the role is remote",
      "Career interest aligns: digital services",
    ],
    gaps: [],
  },
};

const traineeWorkspace: TraineeEmploymentWorkspace = {
  profile: {
    trainee_id: trainee.id,
    full_name: trainee.profile?.full_name ?? "",
    headline: "Certified digital services associate",
    professional_summary: "Fictional certified candidate.",
    preferred_roles: ["Digital services"],
    preferred_locations: ["Hyderabad"],
    open_to_work: true,
    location: "Hyderabad",
    career_interests: ["digital services"],
    placement_visibility_consent: true,
    data_sharing_consent: false,
    verified_skills: [
      {
        name: "Digital member services",
        certificate_id: "certificate-1",
        certificate_number: "NCCT-DEMO-001",
      },
    ],
    resume_filename: "demonstration-resume.pdf",
    resume_size_bytes: 1000,
    resume_uploaded_at: "2026-09-28T10:00:00Z",
  },
  recommendations: [job],
  saved_jobs: [],
  applications: [],
};

const employerWorkspace: EmployerWorkspace = {
  profile: {
    id: "employer-profile-1",
    institution_id: "employer-institution-1",
    company_name: "Fictional Cooperative Services Limited",
    institution_code: "EMP-DEMO",
    contact_name: "Demonstration Recruiter",
    contact_email: employer.email,
    industry: "Cooperative technology",
    website: "https://example.invalid",
    company_size: "51-200",
    description: "Fictional verified employer used only for component testing.",
    headquarters: "Hyderabad, Telangana",
    registration_number: "DEMO-001",
    verification_status: "verified",
    verification_notes: "Demonstration only",
    verified_at: "2026-09-28T10:00:00Z",
    updated_at: "2026-09-28T10:00:00Z",
  },
  jobs: [{ ...job, match: null }],
  applications: [
    {
      id: "application-1",
      job_id: job.id,
      job_title: job.title,
      company_name: job.company_name,
      trainee_id: trainee.id,
      trainee_name: "Asha Employment Demonstration",
      status: "applied",
      cover_note: null,
      applied_at: "2026-09-28T10:00:00Z",
      status_updated_at: "2026-09-28T10:00:00Z",
      interview_at: null,
      interview_mode: null,
      interview_details: null,
      employer_notes: null,
      certificates: [],
      contact: null,
    },
  ],
  shortlisted_count: 0,
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "employment-token", token_type: "bearer", expires_in: 900, user };
}

describe("employment exchange", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows an explainable recommendation and supports keyboard tab navigation", async () => {
    window.history.pushState({}, "", "/employment");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(trainee));
        if (url.endsWith("/api/v1/employment/me/workspace")) return response(traineeWorkspace);
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Jobs for certified trainees" })).toBeInTheDocument();
    expect(screen.getByText("100/100")).toBeInTheDocument();
    expect(screen.getByText("Skills 40/40")).toBeInTheDocument();
    expect(screen.getByText("1 of 1 required certified courses match")).toBeInTheDocument();

    const recommendedTab = screen.getByRole("tab", { name: "Recommended" });
    recommendedTab.focus();
    fireEvent.keyDown(recommendedTab, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Search jobs" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Search jobs" })).toBeInTheDocument();
  });

  it("shows employer-owned jobs and hiring applications", async () => {
    window.history.pushState({}, "", "/employment");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(employer));
        if (url.endsWith("/api/v1/employment/employer/workspace")) {
          return response(employerWorkspace);
        }
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Recruitment workspace" })).toBeInTheDocument();
    expect(screen.getByText("Digital Services Coordinator")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Applications" }));
    expect(screen.getByText("Asha Employment Demonstration")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /Update status/ })).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/employment/employer/workspace"), expect.anything()));
  });
});
