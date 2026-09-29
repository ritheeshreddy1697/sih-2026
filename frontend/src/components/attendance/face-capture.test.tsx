import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { FaceCapture } from "./face-capture";

const originalMediaDevices = navigator.mediaDevices;

describe("FaceCapture", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: originalMediaDevices,
    });
  });

  it("shows a clear error when webcam permission is denied", async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException("Permission denied", "NotAllowedError"));
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });

    render(
      <FaceCapture
        instruction="Turn your head and return to the centre."
        actionLabel="Capture and verify"
        onCapture={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Enable camera" }));

    await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("alert")).toHaveTextContent("Camera permission was denied");
    expect(screen.queryByRole("button", { name: "Capture and verify" })).not.toBeInTheDocument();
  });
});
