import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../App";
import type {
  AnalyticsDashboard,
  AnalyticsDrilldown,
  AnalyticsFilterOptions,
  AuthResponse,
  User,
} from "../lib/api/client";

const administrator: User = {
  id: "analytics-admin-1",
  email: "analytics.admin@example.test",
  status: "active",
  roles: [{ code: "institute_admin", display_name: "Institute administrator" }],
  permissions: ["analytics:view"],
  profile: { full_name: "Analytics Administrator", phone: null, designation: null },
  institution: {
    id: "institution-1",
    name: "Demonstration ICM",
    code: "ICM-DEMO",
    institution_type: "icm",
  },
};

const options: AnalyticsFilterOptions = {
  institutions: [
    {
      id: "institution-1",
      name: "Demonstration ICM",
      code: "ICM-DEMO",
      state: "Telangana",
      is_demo: true,
    },
  ],
  programmes: [
    {
      id: "programme-1",
      institution_id: "institution-1",
      title: "Cooperative Operations Demonstration",
      code: "COOP-DEMO",
      start_date: "2026-09-01",
      is_demo: true,
    },
  ],
  states: ["Telangana"],
  genders: ["Woman"],
  participant_categories: ["individual", "pacs", "shg", "cooperative_institution"],
  start_date_min: "2026-09-01",
  start_date_max: "2026-09-01",
};

const definitions = {
  registrations: "Individual applications plus institutional nominations for the selected programmes.",
  approved_participants: "Registrations whose current review status is approved.",
  attendance_percentage: "Present check-ins divided by expected attendances.",
  course_completion_rate: "Enrolments completing every required lesson.",
  assessment_improvement: "Average post-training score minus pre-training score.",
  dropout_rate: "Withdrawn enrolments divided by all enrolments.",
  certificates_issued: "Digital certificates issued for selected enrolments.",
  job_applications: "Employment applications from the selected cohort.",
  interviews: "Applications with an interview date.",
  placements: "Applications whose hiring status is hired.",
} as const;

const dashboard: AnalyticsDashboard = {
  generated_at: "2026-09-28T09:00:00Z",
  scope_label: "Demonstration ICM",
  contains_demo_data: true,
  filters: {
    institution_id: null,
    programme_id: null,
    start_date: null,
    end_date: null,
    state: null,
    gender: null,
    participant_category: null,
  },
  metrics: [
    ["registrations", "Registrations", 12, "count", 12, null],
    ["approved_participants", "Approved participants", 10, "count", 10, null],
    ["attendance_percentage", "Attendance percentage", 87.5, "percent", 35, 40],
    ["course_completion_rate", "Course-completion rate", 75, "percent", 9, 12],
    ["assessment_improvement", "Assessment improvement", 18, "percentage_points", 8, 8],
    ["dropout_rate", "Dropout rate", 8.3, "percent", 1, 12],
    ["certificates_issued", "Certificates issued", 8, "count", 8, null],
    ["job_applications", "Job applications", 5, "count", 5, null],
    ["interviews", "Interviews", 3, "count", 3, null],
    ["placements", "Placements", 2, "count", 2, null],
  ].map(([key, label, value, unit, numerator, denominator]) => ({
    key: key as keyof typeof definitions,
    label: String(label),
    value: Number(value),
    unit: unit as "count" | "percent" | "percentage_points",
    numerator: Number(numerator),
    denominator: denominator === null ? null : Number(denominator),
    definition: definitions[key as keyof typeof definitions],
  })),
  institution_performance: [
    {
      id: "institution-1",
      label: "Demonstration ICM",
      secondary_label: "ICM-DEMO",
      is_demo: true,
      registrations: 12,
      approved_participants: 10,
      enrollments: 12,
      attendance_percentage: 87.5,
      course_completion_rate: 75,
      assessment_improvement: 18,
      dropout_rate: 8.3,
      certificates_issued: 8,
      job_applications: 5,
      interviews: 3,
      placements: 2,
    },
  ],
  programme_performance: [
    {
      id: "programme-1",
      label: "Cooperative Operations Demonstration",
      secondary_label: "COOP-DEMO | Demonstration ICM",
      is_demo: true,
      registrations: 12,
      approved_participants: 10,
      enrollments: 12,
      attendance_percentage: 87.5,
      course_completion_rate: 75,
      assessment_improvement: 18,
      dropout_rate: 8.3,
      certificates_issued: 8,
      job_applications: 5,
      interviews: 3,
      placements: 2,
    },
  ],
  geographic_distribution: [
    {
      state: "Telangana",
      registrations: 12,
      approved_participants: 10,
      enrollments: 12,
      certificates_issued: 8,
      placements: 2,
    },
  ],
};

const drilldown: AnalyticsDrilldown = {
  metric: "registrations",
  title: "Registrations detail",
  definition: definitions.registrations,
  columns: [
    { key: "participant", label: "Participant" },
    { key: "programme", label: "Programme" },
  ],
  rows: [
    {
      participant: "Asha Demonstration",
      programme: "Cooperative Operations Demonstration",
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
  pages: 1,
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "analytics-token", token_type: "bearer", expires_in: 900, user };
}

describe("analytics dashboard", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows persisted metrics, accessible charts, filters and drill-down records", async () => {
    window.history.pushState({}, "", "/analytics");
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/refresh")) return response(authResponse(administrator));
      if (url.includes("/analytics/options")) return response(options);
      if (url.includes("/analytics/drilldown/registrations")) return response(drilldown);
      if (url.includes("/analytics/dashboard")) return response(dashboard);
      return response({ detail: "Not found" }, false, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Training analytics" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Analytics institution")).toHaveTextContent("Demonstration ICM");
    expect(screen.queryByRole("option", { name: "All in my scope" })).not.toBeInTheDocument();
    expect(await screen.findByText(/Seeded demonstration data is included/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Institute performance comparison/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Enrolments by participant home state/i })).toBeInTheDocument();

    const registrations = screen.getByRole("button", { name: /Registrations 12/i });
    registrations.focus();
    expect(registrations).toHaveFocus();
    fireEvent.click(registrations);
    expect(await screen.findByRole("heading", { name: "Registrations detail" })).toBeInTheDocument();
    expect(screen.getByText("Asha Demonstration")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Participant state"), {
      target: { value: "Telangana" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/analytics/dashboard?state=Telangana"),
        expect.anything(),
      ),
    );
  });

  it("blocks accounts without the backend analytics permission from the route", async () => {
    const trainee: User = {
      ...administrator,
      id: "trainee-1",
      roles: [{ code: "trainee", display_name: "Trainee" }],
      permissions: ["programmes:view"],
    };
    window.history.pushState({}, "", "/analytics");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/auth/refresh")) return response(authResponse(trainee));
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Access not permitted" })).toBeInTheDocument();
  });
});
