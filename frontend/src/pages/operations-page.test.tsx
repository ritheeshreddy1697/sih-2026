import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../App";
import type {
  AuthResponse,
  OperationsWorkspace,
  TraineeOperations,
  User,
} from "../lib/api/client";

const trainee: User = {
  id: "trainee-operations-1",
  email: "trainee.operations@example.test",
  status: "active",
  roles: [{ code: "trainee", display_name: "Trainee" }],
  permissions: ["operations:self"],
  profile: { full_name: "Asha Operations Demonstration", phone: null, designation: null },
  institution: null,
};

const administrator: User = {
  id: "admin-operations-1",
  email: "admin.operations@example.test",
  status: "active",
  roles: [{ code: "institute_admin", display_name: "Institute administrator" }],
  permissions: ["operations:manage"],
  profile: { full_name: "Operations Administrator", phone: null, designation: null },
  institution: {
    id: "institution-1",
    name: "Demonstration ICM",
    code: "ICM-DEMO",
    institution_type: "icm",
  },
};

const session = {
  id: "session-1",
  institution_id: "institution-1",
  programme_id: "programme-1",
  programme_title: "Cooperative Operations Programme",
  programme_code: "OPS-DEMO",
  batch_id: "batch-1",
  batch_name: "Residential batch",
  trainer_id: "trainer-1",
  trainer_name: "Demonstration Trainer",
  venue_id: "venue-1",
  venue_name: "Demonstration Learning Centre",
  classroom_id: "classroom-1",
  classroom_name: "Hall A",
  title: "Cooperative leadership workshop",
  description: "Fictional session",
  starts_at: "2026-10-12T09:00:00Z",
  ends_at: "2026-10-12T12:00:00Z",
  status: "scheduled" as const,
};

const traineeData: TraineeOperations = {
  programmes: [
    {
      enrollment_id: "enrollment-1",
      programme_id: "programme-1",
      programme_title: "Cooperative Operations Programme",
      programme_code: "OPS-DEMO",
      batch_name: "Residential batch",
      timetable: [session],
      logistics: {
        id: "logistics-1",
        enrollment_id: "enrollment-1",
        trainee_name: "Asha Operations Demonstration",
        programme_title: "Cooperative Operations Programme",
        meal_preference: "vegetarian",
        dietary_notes: "No peanuts",
        arrival_mode: "train",
        arrival_details: "Demonstration Express",
        arrival_at: "2026-10-11T15:00:00Z",
        departure_mode: "institutional",
        departure_details: "Institute shuttle",
        departure_at: "2026-10-16T10:00:00Z",
        emergency_contact_name: "Meera Demonstration",
        emergency_contact_phone: "+91 90000 10002",
        emergency_contact_relationship: "Sibling",
      },
      accommodation: {
        id: "allocation-1",
        bed_id: "bed-1",
        bed_number: "A",
        room_id: "room-1",
        room_number: "D-101",
        building_id: "building-1",
        building_name: "Sahyadri Demonstration Hostel",
        enrollment_id: "enrollment-1",
        trainee_name: "Asha Operations Demonstration",
        programme_title: "Cooperative Operations Programme",
        start_date: "2026-10-11",
        end_date: "2026-10-16",
        status: "reserved",
        checked_in_at: null,
        checked_out_at: null,
      },
      materials: [
        {
          id: "material-1",
          programme_id: "programme-1",
          programme_title: "Cooperative Operations Programme",
          name: "Demonstration workbook",
          description: null,
          quantity_available: 20,
          quantity_distributed: 1,
          distributions: [
            {
              id: "distribution-1",
              enrollment_id: "enrollment-1",
              trainee_name: "Asha Operations Demonstration",
              quantity: 1,
              distributed_at: "2026-10-01T09:00:00Z",
            },
          ],
        },
      ],
      issues: [],
    },
  ],
};

const adminData: OperationsWorkspace = {
  institution: { id: "institution-1", name: "Demonstration ICM", code: "ICM-DEMO" },
  available_institutions: [
    { id: "institution-1", name: "Demonstration ICM", code: "ICM-DEMO" },
  ],
  programmes: [
    {
      id: "programme-1",
      title: "Cooperative Operations Programme",
      code: "OPS-DEMO",
      batches: [{ id: "batch-1", name: "Residential batch", code: "RES-1" }],
    },
  ],
  trainers: [
    {
      id: "trainer-1",
      full_name: "Demonstration Trainer",
      email: "trainer@example.test",
    },
  ],
  enrollments: [],
  venues: [
    {
      id: "venue-1",
      institution_id: "institution-1",
      name: "Demonstration Learning Centre",
      address: "Training Road",
      capacity: 40,
      is_active: true,
      classrooms: [],
    },
  ],
  timetable: [session],
  hostels: [],
  bed_allocations: [],
  participant_logistics: [],
  materials: [],
  issues: [],
};

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => body });
}

function authResponse(user: User): AuthResponse {
  return { access_token: "operations-token", token_type: "bearer", expires_in: 900, user };
}

describe("operations pages", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows only the signed-in trainee's assigned timetable and logistics", async () => {
    window.history.pushState({}, "", "/operations");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(trainee));
        if (url.endsWith("/api/v1/operations/me")) return response(traineeData);
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Timetable and logistics" })).toBeInTheDocument();
    expect(screen.getAllByText("Cooperative leadership workshop")).toHaveLength(2);
    expect(screen.getByText("Sahyadri Demonstration Hostel")).toBeInTheDocument();
    expect(screen.getByText(/No peanuts/)).toBeInTheDocument();
    expect(screen.getByText("Demonstration workbook")).toBeInTheDocument();
    expect(screen.queryByText("Operations Administrator")).not.toBeInTheDocument();
  });

  it("provides calendar and list views in the institution-scoped administrator workspace", async () => {
    window.history.pushState({}, "", "/operations");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return response(authResponse(administrator));
        if (url.endsWith("/api/v1/operations/workspace")) return response(adminData);
        return response({ detail: "Not found" }, false, 404);
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Operations and logistics" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Schedule" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Demonstration Learning Centre")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /List/ }));
    expect(screen.getByRole("columnheader", { name: "Allocation" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Hostel" }));
    expect(screen.getByRole("heading", { name: "Hostel and room allocation" })).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/operations/workspace"), expect.anything()));
  });
});
