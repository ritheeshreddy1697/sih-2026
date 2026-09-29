import {
  BedDouble,
  BusFront,
  CalendarDays,
  CheckCircle2,
  Clock3,
  DoorOpen,
  List,
  MapPin,
  PackageCheck,
  Phone,
  Plus,
  TriangleAlert,
  Utensils,
  Wrench,
} from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type BedAllocation,
  type MealPreference,
  type OperationsIssue,
  type OperationsWorkspace,
  type ParticipantLogistics,
  type ScheduleStatus,
  type TimetableSession,
  type TraineeOperations,
  type TransportMode,
} from "../lib/api/client";
import { cn } from "../lib/utils";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";
const tabs = ["Schedule", "Hostel", "Participants", "Materials", "Issues"] as const;
type AdminTab = (typeof tabs)[number];

function errorMessage(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

function formatDateTime(value: string | null) {
  if (!value) return "Not provided";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value));
}

function dateTimeValue(value: Date) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

function tone(value: string) {
  if (["scheduled", "checked_in", "resolved", "completed"].includes(value)) {
    return "bg-emerald-100 text-emerald-800";
  }
  if (["urgent", "cancelled", "closed"].includes(value)) {
    return "bg-red-100 text-red-800";
  }
  if (["high", "open", "reserved"].includes(value)) return "bg-amber-100 text-amber-900";
  return "bg-muted text-foreground";
}

function FieldLabel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <label className="text-sm font-medium">
      {title}
      <span className="mt-2 block">{children}</span>
    </label>
  );
}

function TabList({ active, onChange }: { active: AdminTab; onChange: (tab: AdminTab) => void }) {
  return (
    <div className="mt-6 overflow-x-auto border-b" role="tablist" aria-label="Operations sections">
      <div className="flex min-w-max gap-1">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={active === tab}
            className={cn(
              "min-h-11 border-b-2 px-4 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              active === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onChange(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  );
}

function SessionList({
  sessions,
  onStatus,
}: {
  sessions: TimetableSession[];
  onStatus?: (session: TimetableSession, status: ScheduleStatus) => void;
}) {
  if (!sessions.length) {
    return (
      <EmptyState
        icon={CalendarDays}
        title="No timetable sessions"
        description="Scheduled classes for the selected institution will appear here."
      />
    );
  }
  return (
    <>
      <div className="divide-y rounded-md border bg-card sm:hidden">
        {sessions.map((session) => (
          <article className="p-4" key={session.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium">{session.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {session.programme_code} · {session.batch_name}
                </p>
              </div>
              <Badge className={tone(session.status)}>{labelize(session.status)}</Badge>
            </div>
            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="text-xs font-medium uppercase text-muted-foreground">Time</dt>
                <dd className="mt-1">{formatDateTime(session.starts_at)}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase text-muted-foreground">Trainer</dt>
                <dd className="mt-1">{session.trainer_name}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase text-muted-foreground">Location</dt>
                <dd className="mt-1">
                  {session.venue_name}
                  {session.classroom_name ? ` · ${session.classroom_name}` : ""}
                </dd>
              </div>
            </dl>
            {onStatus && session.status === "scheduled" ? (
              <div className="mt-4 flex gap-2 border-t pt-4">
                <Button size="sm" variant="outline" onClick={() => onStatus(session, "completed")}>
                  Complete
                </Button>
                <Button size="sm" variant="ghost" onClick={() => onStatus(session, "cancelled")}>
                  Cancel
                </Button>
              </div>
            ) : null}
          </article>
        ))}
      </div>
      <div className="hidden overflow-x-auto rounded-md border sm:block">
        <table className="w-full min-w-[760px] text-left text-sm">
        <thead className="bg-muted text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3">Class</th>
            <th className="px-4 py-3">Time</th>
            <th className="px-4 py-3">Allocation</th>
            <th className="px-4 py-3">Status</th>
            {onStatus ? <th className="px-4 py-3 text-right">Actions</th> : null}
          </tr>
        </thead>
        <tbody className="divide-y">
          {sessions.map((session) => (
            <tr key={session.id}>
              <td className="px-4 py-4">
                <p className="font-medium">{session.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {session.programme_code} · {session.batch_name}
                </p>
              </td>
              <td className="px-4 py-4 text-muted-foreground">
                <p>{formatDateTime(session.starts_at)}</p>
                <p className="mt-1 text-xs">to {formatDateTime(session.ends_at)}</p>
              </td>
              <td className="px-4 py-4">
                <p>{session.trainer_name}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {session.venue_name}
                  {session.classroom_name ? ` · ${session.classroom_name}` : ""}
                </p>
              </td>
              <td className="px-4 py-4">
                <Badge className={tone(session.status)}>{labelize(session.status)}</Badge>
              </td>
              {onStatus ? (
                <td className="px-4 py-4 text-right">
                  {session.status === "scheduled" ? (
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={() => onStatus(session, "completed")}>
                        Complete
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => onStatus(session, "cancelled")}>
                        Cancel
                      </Button>
                    </div>
                  ) : null}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
        </table>
      </div>
    </>
  );
}

function CalendarView({ sessions }: { sessions: TimetableSession[] }) {
  const grouped = useMemo(() => {
    const groups = new Map<string, TimetableSession[]>();
    sessions.forEach((session) => {
      const day = session.starts_at.slice(0, 10);
      groups.set(day, [...(groups.get(day) ?? []), session]);
    });
    return [...groups.entries()].sort(([first], [second]) => first.localeCompare(second));
  }, [sessions]);
  if (!grouped.length) return <SessionList sessions={[]} />;
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {grouped.map(([day, daySessions]) => (
        <section key={day} className="rounded-md border bg-card" aria-label={formatDate(day)}>
          <h3 className="border-b bg-muted px-4 py-3 text-sm font-semibold">{formatDate(day)}</h3>
          <div className="divide-y">
            {daySessions.map((session) => (
              <article className="p-4" key={session.id}>
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{session.title}</p>
                  <Badge className={tone(session.status)}>{labelize(session.status)}</Badge>
                </div>
                <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock3 className="h-4 w-4" aria-hidden="true" />
                  {new Date(session.starts_at).toLocaleTimeString("en-IN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
                <p className="mt-2 flex items-start gap-2 text-sm text-muted-foreground">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  {session.venue_name}
                  {session.classroom_name ? `, ${session.classroom_name}` : ""}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">Trainer: {session.trainer_name}</p>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function AdminSchedule({
  data,
  reload,
  notify,
}: {
  data: OperationsWorkspace;
  reload: () => Promise<void>;
  notify: (message: string) => void;
}) {
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [form, setForm] = useState<"session" | "venue" | "classroom" | null>(null);
  const [programmeId, setProgrammeId] = useState("");
  const [venueId, setVenueId] = useState("");
  const selectedProgramme = data.programmes.find((item) => item.id === programmeId);
  const selectedVenue = data.venues.find((item) => item.id === venueId);

  const run = async (work: () => Promise<unknown>, success: string) => {
    try {
      await work();
      setForm(null);
      await reload();
      notify(success);
    } catch (caught) {
      notify(errorMessage(caught, "Unable to save the schedule change."));
    }
  };

  const createSession = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    void run(
      () =>
        apiClient.createTimetableSession({
          programme_id: String(values.get("programme_id")),
          batch_id: String(values.get("batch_id")),
          trainer_id: String(values.get("trainer_id")),
          venue_id: String(values.get("venue_id")),
          classroom_id: String(values.get("classroom_id")) || null,
          title: String(values.get("title")),
          description: String(values.get("description")) || null,
          starts_at: new Date(String(values.get("starts_at"))).toISOString(),
          ends_at: new Date(String(values.get("ends_at"))).toISOString(),
        }),
      "Class added to the timetable.",
    );
  };

  return (
    <section role="tabpanel" aria-label="Schedule">
      <div className="flex flex-wrap items-center justify-between gap-3 py-5">
        <div>
          <h2 className="text-lg font-semibold">Class timetable</h2>
          <p className="mt-1 text-sm text-muted-foreground">Allocate trainers and teaching spaces without overlapping bookings.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="flex rounded-md border p-1" aria-label="Timetable view">
            <Button size="sm" variant={view === "calendar" ? "default" : "ghost"} onClick={() => setView("calendar")} aria-pressed={view === "calendar"}>
              <CalendarDays className="h-4 w-4" aria-hidden="true" /> Calendar
            </Button>
            <Button size="sm" variant={view === "list" ? "default" : "ghost"} onClick={() => setView("list")} aria-pressed={view === "list"}>
              <List className="h-4 w-4" aria-hidden="true" /> List
            </Button>
          </div>
          <Button variant="outline" onClick={() => setForm(form === "venue" ? null : "venue")}>Venue</Button>
          <Button variant="outline" onClick={() => setForm(form === "classroom" ? null : "classroom")}>Classroom</Button>
          <Button onClick={() => setForm(form === "session" ? null : "session")}><Plus className="h-4 w-4" aria-hidden="true" /> Add class</Button>
        </div>
      </div>

      {form === "venue" ? (
        <form className="mb-6 grid gap-4 border-b bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => {
          event.preventDefault();
          const values = new FormData(event.currentTarget);
          void run(() => apiClient.createVenue({ institution_id: data.institution.id, name: String(values.get("name")), address: String(values.get("address")), capacity: Number(values.get("capacity")) }), "Venue added.");
        }}>
          <h3 className="md:col-span-2 font-semibold">Add venue</h3>
          <FieldLabel title="Venue name"><Input name="name" minLength={2} required /></FieldLabel>
          <FieldLabel title="Capacity"><Input name="capacity" type="number" min={1} required /></FieldLabel>
          <FieldLabel title="Address"><textarea className={`${fieldClass} min-h-24`} name="address" minLength={5} required /></FieldLabel>
          <div className="flex items-end"><Button type="submit">Save venue</Button></div>
        </form>
      ) : null}

      {form === "classroom" ? (
        <form className="mb-6 grid gap-4 border-b bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => {
          event.preventDefault();
          const values = new FormData(event.currentTarget);
          void run(() => apiClient.createClassroom({ venue_id: String(values.get("venue_id")), name: String(values.get("name")), code: String(values.get("code")), capacity: Number(values.get("capacity")), equipment: String(values.get("equipment")) || null }), "Classroom added.");
        }}>
          <h3 className="md:col-span-2 font-semibold">Add classroom</h3>
          <FieldLabel title="Venue"><select className={fieldClass} name="venue_id" required><option value="">Select venue</option>{data.venues.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></FieldLabel>
          <FieldLabel title="Classroom name"><Input name="name" required /></FieldLabel>
          <FieldLabel title="Code"><Input name="code" required /></FieldLabel>
          <FieldLabel title="Capacity"><Input name="capacity" type="number" min={1} required /></FieldLabel>
          <FieldLabel title="Equipment"><Input name="equipment" /></FieldLabel>
          <div className="flex items-end"><Button type="submit">Save classroom</Button></div>
        </form>
      ) : null}

      {form === "session" ? (
        <form className="mb-6 grid gap-4 border-b bg-muted/40 p-5 md:grid-cols-2 xl:grid-cols-3" onSubmit={createSession}>
          <h3 className="md:col-span-2 xl:col-span-3 font-semibold">Schedule class</h3>
          <FieldLabel title="Programme"><select className={fieldClass} name="programme_id" value={programmeId} onChange={(event) => setProgrammeId(event.target.value)} required><option value="">Select programme</option>{data.programmes.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.title}</option>)}</select></FieldLabel>
          <FieldLabel title="Batch"><select className={fieldClass} name="batch_id" required><option value="">Select batch</option>{selectedProgramme?.batches.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></FieldLabel>
          <FieldLabel title="Trainer"><select className={fieldClass} name="trainer_id" required><option value="">Select trainer</option>{data.trainers.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></FieldLabel>
          <FieldLabel title="Venue"><select className={fieldClass} name="venue_id" value={venueId} onChange={(event) => setVenueId(event.target.value)} required><option value="">Select venue</option>{data.venues.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></FieldLabel>
          <FieldLabel title="Classroom"><select className={fieldClass} name="classroom_id"><option value="">Use whole venue</option>{selectedVenue?.classrooms.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.capacity} seats</option>)}</select></FieldLabel>
          <FieldLabel title="Class title"><Input name="title" minLength={3} required /></FieldLabel>
          <FieldLabel title="Starts at"><Input name="starts_at" type="datetime-local" defaultValue={dateTimeValue(new Date(Date.now() + 86_400_000))} required /></FieldLabel>
          <FieldLabel title="Ends at"><Input name="ends_at" type="datetime-local" defaultValue={dateTimeValue(new Date(Date.now() + 90_000_000))} required /></FieldLabel>
          <FieldLabel title="Description"><Input name="description" /></FieldLabel>
          <div className="flex items-end"><Button type="submit">Check and schedule</Button></div>
        </form>
      ) : null}

      {view === "calendar" ? <CalendarView sessions={data.timetable} /> : <SessionList sessions={data.timetable} onStatus={(session, status) => void run(() => apiClient.updateTimetableSession(session.id, { status }), `Class marked ${labelize(status).toLowerCase()}.`)} />}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data.venues.map((venue) => (
          <article className="border-l-4 border-l-sky-600 bg-card p-4 shadow-sm" key={venue.id}>
            <p className="font-medium">{venue.name}</p>
            <p className="mt-1 text-sm text-muted-foreground">{venue.address}</p>
            <p className="mt-3 text-xs text-muted-foreground">{venue.capacity} people · {venue.classrooms.length} classrooms</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function AllocationRow({ allocation, action }: { allocation: BedAllocation; action: (item: BedAllocation, out: boolean) => void }) {
  return (
    <article className="flex flex-col gap-3 border-b py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-2"><p className="font-medium">{allocation.trainee_name}</p><Badge className={tone(allocation.status)}>{labelize(allocation.status)}</Badge></div>
        <p className="mt-1 text-sm text-muted-foreground">{allocation.building_name} · Room {allocation.room_number} · Bed {allocation.bed_number}</p>
        <p className="mt-1 text-xs text-muted-foreground">{formatDate(allocation.start_date)} to {formatDate(allocation.end_date)}</p>
      </div>
      {allocation.status === "reserved" ? <Button size="sm" onClick={() => action(allocation, false)}><DoorOpen className="h-4 w-4" aria-hidden="true" /> Check in</Button> : null}
      {allocation.status === "checked_in" ? <Button size="sm" variant="outline" onClick={() => action(allocation, true)}>Check out</Button> : null}
    </article>
  );
}

function AdminHostel({ data, reload, notify }: { data: OperationsWorkspace; reload: () => Promise<void>; notify: (message: string) => void }) {
  const [form, setForm] = useState<"building" | "room" | "allocation" | null>(null);
  const [buildingId, setBuildingId] = useState("");
  const [roomId, setRoomId] = useState("");
  const selectedBuilding = data.hostels.find((item) => item.id === buildingId);
  const selectedRoom = selectedBuilding?.rooms.find((item) => item.id === roomId);
  const run = async (work: () => Promise<unknown>, success: string) => {
    try { await work(); setForm(null); await reload(); notify(success); }
    catch (caught) { notify(errorMessage(caught, "Unable to save the hostel change.")); }
  };
  return (
    <section role="tabpanel" aria-label="Hostel">
      <div className="flex flex-wrap items-center justify-between gap-3 py-5">
        <div><h2 className="text-lg font-semibold">Hostel and room allocation</h2><p className="mt-1 text-sm text-muted-foreground">Manage room capacity, dated bed reservations, check-in and check-out.</p></div>
        <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setForm("building")}>Building</Button><Button variant="outline" onClick={() => setForm("room")}>Room and beds</Button><Button onClick={() => setForm("allocation")}><Plus className="h-4 w-4" aria-hidden="true" /> Allocate bed</Button></div>
      </div>
      {form === "building" ? <form className="mb-6 grid gap-4 bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void run(() => apiClient.createHostel({ institution_id: data.institution.id, name: String(value.get("name")), address: String(value.get("address")), contact_phone: String(value.get("phone")) || null }), "Hostel building added."); }}><FieldLabel title="Building name"><Input name="name" required /></FieldLabel><FieldLabel title="Contact phone"><Input name="phone" /></FieldLabel><FieldLabel title="Address"><textarea className={`${fieldClass} min-h-24`} name="address" required /></FieldLabel><div className="flex items-end"><Button type="submit">Save building</Button></div></form> : null}
      {form === "room" ? <form className="mb-6 grid gap-4 bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void run(() => apiClient.createHostelRoom(String(value.get("building_id")), { room_number: String(value.get("room_number")), floor: String(value.get("floor")) || null, capacity: Number(value.get("capacity")), bed_numbers: String(value.get("beds")).split(",").map((item) => item.trim()).filter(Boolean), is_accessible: value.get("accessible") === "on" }), "Hostel room added."); }}><FieldLabel title="Building"><select className={fieldClass} name="building_id" required><option value="">Select building</option>{data.hostels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></FieldLabel><FieldLabel title="Room number"><Input name="room_number" required /></FieldLabel><FieldLabel title="Floor"><Input name="floor" /></FieldLabel><FieldLabel title="Capacity"><Input name="capacity" type="number" min={1} max={100} required /></FieldLabel><FieldLabel title="Bed numbers, separated by commas"><Input name="beds" placeholder="A, B" required /></FieldLabel><label className="flex min-h-11 items-center gap-3 text-sm font-medium"><input className="h-5 w-5" type="checkbox" name="accessible" /> Accessible room</label><Button type="submit">Save room and beds</Button></form> : null}
      {form === "allocation" ? <form className="mb-6 grid gap-4 bg-muted/40 p-5 md:grid-cols-2 xl:grid-cols-3" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void run(() => apiClient.allocateBed({ bed_id: String(value.get("bed_id")), enrollment_id: String(value.get("enrollment_id")), start_date: String(value.get("start_date")), end_date: String(value.get("end_date")) }), "Bed reserved."); }}><FieldLabel title="Participant"><select className={fieldClass} name="enrollment_id" required><option value="">Select participant</option>{data.enrollments.map((item) => <option key={item.id} value={item.id}>{item.trainee.full_name} · {item.programme_title}</option>)}</select></FieldLabel><FieldLabel title="Building"><select className={fieldClass} value={buildingId} onChange={(event) => { setBuildingId(event.target.value); setRoomId(""); }} required><option value="">Select building</option>{data.hostels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></FieldLabel><FieldLabel title="Room"><select className={fieldClass} value={roomId} onChange={(event) => setRoomId(event.target.value)} required><option value="">Select room</option>{selectedBuilding?.rooms.map((item) => <option key={item.id} value={item.id}>{item.room_number} · {item.capacity} beds</option>)}</select></FieldLabel><FieldLabel title="Bed"><select className={fieldClass} name="bed_id" required><option value="">Select bed</option>{selectedRoom?.beds.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.bed_number}</option>)}</select></FieldLabel><FieldLabel title="From"><Input name="start_date" type="date" required /></FieldLabel><FieldLabel title="To"><Input name="end_date" type="date" required /></FieldLabel><Button type="submit">Check and reserve</Button></form> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
        <div className="grid gap-3 sm:grid-cols-2">
          {data.hostels.length ? data.hostels.map((building) => <article className="rounded-md border bg-card p-5" key={building.id}><BedDouble className="h-6 w-6 text-primary" aria-hidden="true" /><h3 className="mt-3 font-semibold">{building.name}</h3><p className="mt-1 text-sm text-muted-foreground">{building.address}</p><div className="mt-4 space-y-2">{building.rooms.map((room) => <div className="flex justify-between border-t pt-2 text-sm" key={room.id}><span>Room {room.room_number}{room.is_accessible ? " · Accessible" : ""}</span><span className="text-muted-foreground">{room.beds.length}/{room.capacity} beds</span></div>)}</div></article>) : <EmptyState icon={BedDouble} title="No hostel buildings" description="Add a building, then create rooms and beds." />}
        </div>
        <section className="rounded-md border bg-card p-5"><h3 className="font-semibold">Current allocations</h3>{data.bed_allocations.length ? <div className="mt-2">{data.bed_allocations.map((item) => <AllocationRow key={item.id} allocation={item} action={(allocation, out) => void run(() => out ? apiClient.checkOutBed(allocation.id) : apiClient.checkInBed(allocation.id), out ? "Participant checked out." : "Participant checked in.")} />)}</div> : <p className="mt-4 text-sm text-muted-foreground">No beds allocated.</p>}</section>
      </div>
    </section>
  );
}

function AdminParticipants({ data, reload, notify }: { data: OperationsWorkspace; reload: () => Promise<void>; notify: (message: string) => void }) {
  const [enrollmentId, setEnrollmentId] = useState(data.enrollments[0]?.id ?? "");
  const existing = data.participant_logistics.find((item) => item.enrollment_id === enrollmentId);
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = new FormData(event.currentTarget);
    try {
      await apiClient.updateParticipantLogistics(enrollmentId, {
        meal_preference: String(value.get("meal")) as MealPreference,
        dietary_notes: String(value.get("dietary")) || null,
        arrival_mode: (String(value.get("arrival_mode")) || null) as TransportMode | null,
        arrival_details: String(value.get("arrival_details")) || null,
        arrival_at: value.get("arrival_at") ? new Date(String(value.get("arrival_at"))).toISOString() : null,
        departure_mode: (String(value.get("departure_mode")) || null) as TransportMode | null,
        departure_details: String(value.get("departure_details")) || null,
        departure_at: value.get("departure_at") ? new Date(String(value.get("departure_at"))).toISOString() : null,
        emergency_contact_name: String(value.get("contact_name")),
        emergency_contact_phone: String(value.get("contact_phone")),
        emergency_contact_relationship: String(value.get("relationship")),
      });
      await reload(); notify("Participant logistics saved.");
    } catch (caught) { notify(errorMessage(caught, "Unable to save participant logistics.")); }
  };
  return <section role="tabpanel" aria-label="Participants"><div className="py-5"><h2 className="text-lg font-semibold">Participant logistics</h2><p className="mt-1 text-sm text-muted-foreground">Record meals, journeys and an emergency contact for each enrolled participant.</p></div>{data.enrollments.length ? <form key={`${enrollmentId}-${existing?.id ?? "new"}`} className="grid gap-5 border-t pt-5 md:grid-cols-2 xl:grid-cols-3" onSubmit={(event) => void save(event)}><FieldLabel title="Participant"><select className={fieldClass} value={enrollmentId} onChange={(event) => setEnrollmentId(event.target.value)}>{data.enrollments.map((item) => <option key={item.id} value={item.id}>{item.trainee.full_name} · {item.programme_title}</option>)}</select></FieldLabel><FieldLabel title="Meal preference"><select className={fieldClass} name="meal" defaultValue={existing?.meal_preference ?? "vegetarian"}>{["vegetarian", "vegan", "eggetarian", "non_vegetarian", "jain", "other"].map((item) => <option value={item} key={item}>{labelize(item)}</option>)}</select></FieldLabel><FieldLabel title="Dietary notes"><Input name="dietary" defaultValue={existing?.dietary_notes ?? ""} /></FieldLabel><FieldLabel title="Arrival mode"><TransportSelect name="arrival_mode" value={existing?.arrival_mode} /></FieldLabel><FieldLabel title="Arrival details"><Input name="arrival_details" defaultValue={existing?.arrival_details ?? ""} /></FieldLabel><FieldLabel title="Arrival date and time"><Input name="arrival_at" type="datetime-local" defaultValue={existing?.arrival_at ? dateTimeValue(new Date(existing.arrival_at)) : ""} /></FieldLabel><FieldLabel title="Departure mode"><TransportSelect name="departure_mode" value={existing?.departure_mode} /></FieldLabel><FieldLabel title="Departure details"><Input name="departure_details" defaultValue={existing?.departure_details ?? ""} /></FieldLabel><FieldLabel title="Departure date and time"><Input name="departure_at" type="datetime-local" defaultValue={existing?.departure_at ? dateTimeValue(new Date(existing.departure_at)) : ""} /></FieldLabel><FieldLabel title="Emergency contact"><Input name="contact_name" minLength={2} defaultValue={existing?.emergency_contact_name ?? ""} required /></FieldLabel><FieldLabel title="Emergency phone"><Input name="contact_phone" type="tel" minLength={7} defaultValue={existing?.emergency_contact_phone ?? ""} required /></FieldLabel><FieldLabel title="Relationship"><Input name="relationship" minLength={2} defaultValue={existing?.emergency_contact_relationship ?? ""} required /></FieldLabel><div className="md:col-span-2 xl:col-span-3"><Button type="submit">Save participant logistics</Button></div></form> : <EmptyState title="No enrolled participants" description="Approved programme enrolments will be available here." />}</section>;
}

function TransportSelect({ name, value }: { name: string; value?: TransportMode | null }) {
  return <select className={fieldClass} name={name} defaultValue={value ?? ""}><option value="">Not provided</option>{["self", "train", "bus", "flight", "institutional", "other"].map((item) => <option key={item} value={item}>{labelize(item)}</option>)}</select>;
}

function AdminMaterials({ data, reload, notify }: { data: OperationsWorkspace; reload: () => Promise<void>; notify: (message: string) => void }) {
  const [showCreate, setShowCreate] = useState(false);
  const run = async (work: () => Promise<unknown>, success: string) => { try { await work(); await reload(); notify(success); } catch (caught) { notify(errorMessage(caught, "Unable to update materials.")); } };
  return <section role="tabpanel" aria-label="Materials"><div className="flex flex-wrap items-center justify-between gap-3 py-5"><div><h2 className="text-lg font-semibold">Training materials</h2><p className="mt-1 text-sm text-muted-foreground">Track stock and one-time distribution to enrolled participants.</p></div><Button onClick={() => setShowCreate((value) => !value)}><Plus className="h-4 w-4" aria-hidden="true" /> Add material</Button></div>{showCreate ? <form className="mb-6 grid gap-4 bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void run(() => apiClient.createTrainingMaterial({ programme_id: String(value.get("programme_id")), name: String(value.get("name")), description: String(value.get("description")) || null, quantity_available: Number(value.get("quantity")) }), "Training material added."); setShowCreate(false); }}><FieldLabel title="Programme"><select className={fieldClass} name="programme_id" required><option value="">Select programme</option>{data.programmes.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></FieldLabel><FieldLabel title="Material name"><Input name="name" required /></FieldLabel><FieldLabel title="Quantity available"><Input name="quantity" type="number" min={0} required /></FieldLabel><FieldLabel title="Description"><Input name="description" /></FieldLabel><Button type="submit">Save material</Button></form> : null}{data.materials.length ? <div className="grid gap-4 lg:grid-cols-2">{data.materials.map((material) => { const eligible = data.enrollments.filter((item) => item.programme_id === material.programme_id && !material.distributions.some((row) => row.enrollment_id === item.id)); return <article className="rounded-md border bg-card p-5" key={material.id}><div className="flex items-start justify-between gap-3"><div><PackageCheck className="h-6 w-6 text-primary" aria-hidden="true" /><h3 className="mt-3 font-semibold">{material.name}</h3><p className="mt-1 text-sm text-muted-foreground">{material.programme_title}</p></div><Badge>{material.quantity_distributed}/{material.quantity_available} issued</Badge></div>{material.description ? <p className="mt-3 text-sm">{material.description}</p> : null}<form className="mt-4 flex flex-col gap-2 border-t pt-4 sm:flex-row" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void run(() => apiClient.distributeTrainingMaterial(material.id, { enrollment_id: String(value.get("enrollment_id")), quantity: Number(value.get("quantity")) }), "Material distribution recorded."); }}><select className={fieldClass} name="enrollment_id" required><option value="">Select participant</option>{eligible.map((item) => <option key={item.id} value={item.id}>{item.trainee.full_name}</option>)}</select><Input className="sm:w-24" name="quantity" type="number" min={1} defaultValue={1} required /><Button type="submit" disabled={!eligible.length}>Issue</Button></form><div className="mt-3 text-xs text-muted-foreground">{material.distributions.length ? material.distributions.map((item) => `${item.trainee_name} (${item.quantity})`).join(", ") : "No distributions recorded."}</div></article>; })}</div> : <EmptyState icon={PackageCheck} title="No materials" description="Add programme workbooks, kits or other physical materials." />}</section>;
}

function AdminIssues({ data, reload, notify }: { data: OperationsWorkspace; reload: () => Promise<void>; notify: (message: string) => void }) {
  const [showCreate, setShowCreate] = useState(false);
  const run = async (work: () => Promise<unknown>, success: string) => { try { await work(); await reload(); notify(success); } catch (caught) { notify(errorMessage(caught, "Unable to update the issue.")); } };
  return <section role="tabpanel" aria-label="Issues"><div className="flex flex-wrap items-center justify-between gap-3 py-5"><div><h2 className="text-lg font-semibold">Maintenance and participant issues</h2><p className="mt-1 text-sm text-muted-foreground">Record, assign priority and close operational concerns with notes.</p></div><Button onClick={() => setShowCreate((value) => !value)}><Plus className="h-4 w-4" aria-hidden="true" /> Report issue</Button></div>{showCreate ? <form className="mb-6 grid gap-4 bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void run(() => apiClient.createOperationsIssue({ institution_id: data.institution.id, enrollment_id: String(value.get("enrollment_id")) || null, issue_type: String(value.get("issue_type")) as "maintenance" | "participant", priority: String(value.get("priority")) as "low" | "medium" | "high" | "urgent", title: String(value.get("title")), description: String(value.get("description")), location: String(value.get("location")) || null }), "Issue reported."); setShowCreate(false); }}><FieldLabel title="Type"><select className={fieldClass} name="issue_type"><option value="maintenance">Maintenance</option><option value="participant">Participant</option></select></FieldLabel><FieldLabel title="Priority"><select className={fieldClass} name="priority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></FieldLabel><FieldLabel title="Participant, if applicable"><select className={fieldClass} name="enrollment_id"><option value="">General issue</option>{data.enrollments.map((item) => <option key={item.id} value={item.id}>{item.trainee.full_name}</option>)}</select></FieldLabel><FieldLabel title="Location"><Input name="location" /></FieldLabel><FieldLabel title="Title"><Input name="title" minLength={3} required /></FieldLabel><FieldLabel title="Description"><textarea className={`${fieldClass} min-h-24`} name="description" minLength={5} required /></FieldLabel><Button type="submit">Submit issue</Button></form> : null}{data.issues.length ? <div className="divide-y rounded-md border bg-card">{data.issues.map((issue) => <IssueRow key={issue.id} issue={issue} onUpdate={(status, notes) => void run(() => apiClient.updateOperationsIssue(issue.id, { status, resolution_notes: notes }), "Issue updated.")} />)}</div> : <EmptyState icon={Wrench} title="No issues reported" description="Maintenance and participant concerns will appear here." />}</section>;
}

function IssueRow({ issue, onUpdate }: { issue: OperationsIssue; onUpdate?: (status: "in_progress" | "resolved", notes: string | null) => void }) {
  const [resolve, setResolve] = useState(false);
  return <article className="p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><Badge className={tone(issue.priority)}>{labelize(issue.priority)}</Badge><Badge className={tone(issue.status)}>{labelize(issue.status)}</Badge></div><h3 className="mt-3 font-semibold">{issue.title}</h3><p className="mt-1 text-sm text-muted-foreground">{labelize(issue.issue_type)} · Reported by {issue.reported_by_name}{issue.location ? ` · ${issue.location}` : ""}</p></div>{onUpdate && issue.status === "open" ? <Button size="sm" variant="outline" onClick={() => onUpdate("in_progress", null)}>Start work</Button> : null}{onUpdate && issue.status === "in_progress" ? <Button size="sm" onClick={() => setResolve(true)}><CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Resolve</Button> : null}</div><p className="mt-3 text-sm leading-6">{issue.description}</p>{issue.resolution_notes ? <p className="mt-3 border-l-4 border-emerald-500 bg-emerald-50 p-3 text-sm text-emerald-950">{issue.resolution_notes}</p> : null}{resolve ? <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); onUpdate?.("resolved", String(value.get("notes"))); setResolve(false); }}><Input name="notes" minLength={5} placeholder="Resolution notes" required /><Button type="submit">Confirm resolution</Button></form> : null}</article>;
}

function AdminOperations() {
  const [data, setData] = useState<OperationsWorkspace | null>(null);
  const [institutionId, setInstitutionId] = useState<string>();
  const [activeTab, setActiveTab] = useState<AdminTab>("Schedule");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(async () => {
    setIsLoading(true); setError(null);
    try { setData(await apiClient.operationsWorkspace(institutionId)); }
    catch (caught) { setError(errorMessage(caught, "Unable to load training operations.")); }
    finally { setIsLoading(false); }
  }, [institutionId]);
  useEffect(() => void load(), [load]);
  if (isLoading && !data) return <LoadingState label="Loading training operations" />;
  if (error && !data) return <ErrorState title="Operations unavailable" description={error} onRetry={load} />;
  if (!data) return null;
  const shared = { data, reload: load, notify: setMessage };
  return <><header className="flex flex-col gap-4 border-b pb-6 md:flex-row md:items-end md:justify-between"><div><p className="text-sm font-semibold text-primary">Training delivery</p><h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Operations and logistics</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Plan classes, accommodation, journeys, meals, materials and participant support.</p></div>{data.available_institutions.length > 1 ? <label className="text-sm font-medium">Institution<select className={`${fieldClass} mt-2 min-w-72`} value={data.institution.id} onChange={(event) => setInstitutionId(event.target.value)}>{data.available_institutions.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></label> : <div className="text-sm"><p className="font-medium">{data.institution.name}</p><p className="text-muted-foreground">{data.institution.code}</p></div>}</header>{message ? <p className="mt-4 border-l-4 border-primary bg-muted px-4 py-3 text-sm" role="status">{message}</p> : null}<TabList active={activeTab} onChange={setActiveTab} />{activeTab === "Schedule" ? <AdminSchedule {...shared} /> : null}{activeTab === "Hostel" ? <AdminHostel {...shared} /> : null}{activeTab === "Participants" ? <AdminParticipants {...shared} /> : null}{activeTab === "Materials" ? <AdminMaterials {...shared} /> : null}{activeTab === "Issues" ? <AdminIssues {...shared} /> : null}</>;
}

function LogisticsSummary({ logistics }: { logistics: ParticipantLogistics | null }) {
  if (!logistics) return <p className="text-sm text-muted-foreground">Journey, meal and emergency details have not been assigned.</p>;
  return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><Info icon={Utensils} label="Meals" value={`${labelize(logistics.meal_preference)}${logistics.dietary_notes ? ` · ${logistics.dietary_notes}` : ""}`} /><Info icon={BusFront} label="Arrival" value={`${logistics.arrival_mode ? labelize(logistics.arrival_mode) : "Not provided"} · ${formatDateTime(logistics.arrival_at)}${logistics.arrival_details ? ` · ${logistics.arrival_details}` : ""}`} /><Info icon={BusFront} label="Departure" value={`${logistics.departure_mode ? labelize(logistics.departure_mode) : "Not provided"} · ${formatDateTime(logistics.departure_at)}${logistics.departure_details ? ` · ${logistics.departure_details}` : ""}`} /><Info icon={Phone} label="Emergency contact" value={`${logistics.emergency_contact_name} · ${logistics.emergency_contact_relationship} · ${logistics.emergency_contact_phone}`} /></div>;
}

function Info({ icon: Icon, label, value }: { icon: typeof Utensils; label: string; value: string }) {
  return <div className="border-l-4 border-l-primary bg-card p-4 shadow-sm"><Icon className="h-5 w-5 text-primary" aria-hidden="true" /><p className="mt-3 text-xs font-medium uppercase text-muted-foreground">{label}</p><p className="mt-1 text-sm leading-6">{value}</p></div>;
}

function TraineeOperationsView() {
  const [data, setData] = useState<TraineeOperations | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);
  const load = useCallback(async () => { setError(null); try { setData(await apiClient.myOperations()); } catch (caught) { setError(errorMessage(caught, "Unable to load your timetable and logistics.")); } }, []);
  useEffect(() => void load(), [load]);
  if (error) return <ErrorState title="Your operations information is unavailable" description={error} onRetry={load} />;
  if (!data) return <LoadingState label="Loading your timetable and logistics" />;
  if (!data.programmes.length) return <EmptyState icon={CalendarDays} title="No assigned training logistics" description="Your timetable and travel information will appear after you are enrolled in a programme batch." />;
  return <><header className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-semibold text-primary">My training</p><h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Timetable and logistics</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">See only your assigned classes, stay, journeys, meals and materials.</p></div><Button onClick={() => setShowReport((value) => !value)}><TriangleAlert className="h-4 w-4" aria-hidden="true" /> Report an issue</Button></header>{message ? <p className="mt-4 border-l-4 border-primary bg-muted px-4 py-3 text-sm" role="status">{message}</p> : null}{showReport ? <form className="mt-5 grid gap-4 bg-muted/40 p-5 md:grid-cols-2" onSubmit={(event) => { event.preventDefault(); const value = new FormData(event.currentTarget); void apiClient.reportMyOperationsIssue({ enrollment_id: String(value.get("enrollment_id")), issue_type: "participant", priority: String(value.get("priority")) as "low" | "medium" | "high" | "urgent", title: String(value.get("title")), description: String(value.get("description")), location: String(value.get("location")) || null }).then(async () => { setShowReport(false); await load(); setMessage("Your issue was submitted to the institute."); }).catch((caught) => setMessage(errorMessage(caught, "Unable to submit the issue."))); }}><FieldLabel title="Programme"><select className={fieldClass} name="enrollment_id" required>{data.programmes.map((item) => <option key={item.enrollment_id} value={item.enrollment_id}>{item.programme_title}</option>)}</select></FieldLabel><FieldLabel title="Priority"><select className={fieldClass} name="priority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></FieldLabel><FieldLabel title="Title"><Input name="title" minLength={3} required /></FieldLabel><FieldLabel title="Location"><Input name="location" /></FieldLabel><FieldLabel title="Description"><textarea className={`${fieldClass} min-h-24`} name="description" minLength={5} required /></FieldLabel><div className="flex items-end"><Button type="submit">Submit issue</Button></div></form> : null}<div className="mt-7 space-y-10">{data.programmes.map((programme) => <section key={programme.enrollment_id} aria-labelledby={`programme-${programme.enrollment_id}`}><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium text-primary">{programme.programme_code}{programme.batch_name ? ` · ${programme.batch_name}` : ""}</p><h2 id={`programme-${programme.enrollment_id}`} className="mt-1 text-xl font-semibold">{programme.programme_title}</h2></div>{programme.accommodation ? <Badge className={tone(programme.accommodation.status)}>{labelize(programme.accommodation.status)}</Badge> : null}</div><div className="mt-5"><h3 className="mb-3 font-semibold">Assigned timetable</h3><SessionList sessions={programme.timetable} /></div><div className="mt-7"><h3 className="mb-3 font-semibold">Travel, meals and emergency contact</h3><LogisticsSummary logistics={programme.logistics} /></div><div className="mt-7 grid gap-6 lg:grid-cols-2"><div><h3 className="mb-3 font-semibold">Accommodation</h3>{programme.accommodation ? <div className="rounded-md border bg-card p-5"><BedDouble className="h-6 w-6 text-primary" aria-hidden="true" /><p className="mt-3 font-medium">{programme.accommodation.building_name}</p><p className="mt-1 text-sm text-muted-foreground">Room {programme.accommodation.room_number} · Bed {programme.accommodation.bed_number}</p><p className="mt-3 text-sm">{formatDate(programme.accommodation.start_date)} to {formatDate(programme.accommodation.end_date)}</p></div> : <p className="text-sm text-muted-foreground">No hostel accommodation assigned.</p>}</div><div><h3 className="mb-3 font-semibold">Materials issued</h3>{programme.materials.length ? <div className="divide-y rounded-md border bg-card">{programme.materials.map((item) => <div className="flex items-center gap-3 p-4" key={item.id}><PackageCheck className="h-5 w-5 text-primary" aria-hidden="true" /><div><p className="text-sm font-medium">{item.name}</p><p className="text-xs text-muted-foreground">Quantity {item.distributions.find((row) => row.enrollment_id === programme.enrollment_id)?.quantity ?? 0}</p></div></div>)}</div> : <p className="text-sm text-muted-foreground">No materials have been issued.</p>}</div></div>{programme.issues.length ? <div className="mt-7"><h3 className="mb-3 font-semibold">My reported issues</h3><div className="divide-y rounded-md border bg-card">{programme.issues.map((item) => <IssueRow key={item.id} issue={item} />)}</div></div> : null}</section>)}</div></>;
}

export function OperationsPage() {
  const { user, logout, can } = useAuth();
  if (!user) return null;
  return <AppShell user={user} onLogout={logout}>{can("operations:manage") ? <AdminOperations /> : <TraineeOperationsView />}</AppShell>;
}
