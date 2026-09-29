import "fake-indexeddb/auto";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { apiClient } from "../lib/api/client";
import { clearKioskData, setDeviceToken, setPairedSession } from "../lib/kiosk-db";
import { AttendanceKioskPage } from "./attendance-kiosk-page";

describe("AttendanceKioskPage", () => {
  afterEach(async () => {
    await clearKioskData();
    vi.restoreAllMocks();
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
  });

  it("uses large activation controls and clearly shows offline state", async () => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
    render(<AttendanceKioskPage />);

    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Activate this kiosk" })).toBeInTheDocument();
    const activate = screen.getByRole("button", { name: "Activate device" });
    expect(activate).toHaveClass("h-14");

    fireEvent.change(screen.getByLabelText("Device token"), {
      target: { value: "demonstration-device-token" },
    });
    fireEvent.click(activate);

    await waitFor(() => expect(screen.getByText("Device activated")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Start camera" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Synchronize now" })).toBeDisabled();
  });

  it("keeps QR fallback and limits face mode to a claimed enrolled identity", async () => {
    await setDeviceToken("demonstration-device-token");
    await setPairedSession({
      session_id: "0a2fdca5-7194-4b1b-8860-a4dacdd745be",
      title: "Morning attendance",
      programme_title: "Cooperative leadership",
      programme_code: "DEMO-01",
      batch_name: "Morning batch",
      starts_at: new Date(Date.now() - 60_000).toISOString(),
      ends_at: new Date(Date.now() + 3_600_000).toISOString(),
      offline_until: new Date(Date.now() + 4_500_000).toISOString(),
    });
    vi.spyOn(apiClient, "syncKioskAttendance").mockResolvedValue({
      items: [],
      accepted: 0,
      duplicates: 0,
      rejected: 0,
    });
    const challenge = vi.spyOn(apiClient, "createKioskBiometricChallenge").mockResolvedValue({
      id: "7fc5e598-1c56-41d5-891a-99f8aa78972b",
      challenge_type: "turn_head",
      instruction: "Turn your head and return to the centre.",
      expires_at: new Date(Date.now() + 120_000).toISOString(),
      trainee_name: "Demonstration Trainee",
      provider_mode: "demonstration",
      is_demo: true,
    });

    render(<AttendanceKioskPage />);

    expect(await screen.findByRole("heading", { name: "Optional face verification" })).toBeInTheDocument();
    expect(screen.getByText(/Demo mode:/)).toBeInTheDocument();
    expect(screen.getByLabelText("QR text fallback")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Trainee identity code"), {
      target: { value: "NCCT-1234ABCD" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start face challenge" }));

    await waitFor(() =>
      expect(challenge).toHaveBeenCalledWith(
        "demonstration-device-token",
        "0a2fdca5-7194-4b1b-8860-a4dacdd745be",
        "NCCT-1234ABCD",
      ),
    );
    expect(screen.getAllByText("Turn your head and return to the centre.")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Enable camera" })).toBeInTheDocument();
  });
});
