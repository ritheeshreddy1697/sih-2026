import "fake-indexeddb/auto";

import { afterEach, describe, expect, it, vi } from "vitest";

import type { AttendanceSyncResponse } from "./api/client";
import {
  clearKioskData,
  enqueueAttendance,
  queuedAttendance,
  synchronizeAttendanceQueue,
} from "./kiosk-db";

describe("offline attendance queue", () => {
  afterEach(async () => {
    await clearKioskData();
  });

  it("synchronizes a captured event exactly once after connectivity returns", async () => {
    const event = {
      idempotency_key: "8f05c7a7-91ed-47d8-909a-27d6dd02d865",
      session_id: "6acb9d76-2b2f-443f-90d2-e159dc9640e0",
      trainee_qr: "NCCT-TRAINEE:signed-demonstration-value",
      captured_at: "2026-09-27T10:30:00.000Z",
    };
    await enqueueAttendance(event);
    expect(await queuedAttendance()).toHaveLength(1);

    const synchronize = vi.fn(async (): Promise<AttendanceSyncResponse> => ({
      items: [
        {
          idempotency_key: event.idempotency_key,
          result: "created",
          check_in_id: "414ada0c-93bf-4b5b-a53f-82ef17a39495",
          trainee_name: "Demonstration Trainee",
          detail: "Attendance recorded",
        },
      ],
      accepted: 1,
      duplicates: 0,
      rejected: 0,
    }));

    await synchronizeAttendanceQueue(synchronize);
    await synchronizeAttendanceQueue(synchronize);

    expect(synchronize).toHaveBeenCalledTimes(1);
    expect(synchronize).toHaveBeenCalledWith([event]);
    expect(await queuedAttendance()).toEqual([]);
  });

  it("keeps rejected events with the server reason for operator review", async () => {
    await enqueueAttendance({
      idempotency_key: "a16315fc-63c7-42d1-a6f1-8fa54dd603be",
      session_id: "34972e29-ff20-4fe6-86af-d54e2dfeac79",
      trainee_qr: "NCCT-TRAINEE:invalid",
      captured_at: "2026-09-27T10:30:00.000Z",
    });
    await synchronizeAttendanceQueue(async (items) => ({
      items: [
        {
          idempotency_key: items[0].idempotency_key,
          result: "rejected",
          check_in_id: null,
          trainee_name: null,
          detail: "Trainee is not enrolled in this session batch",
        },
      ],
      accepted: 0,
      duplicates: 0,
      rejected: 1,
    }));

    const queued = await queuedAttendance();
    expect(queued).toHaveLength(1);
    expect(queued[0].attempts).toBe(1);
    expect(queued[0].last_error).toContain("not enrolled");
  });
});
