import { type FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Check, Save } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type EligibilityType,
  type ProgrammeMode,
  type ProgrammePayload,
} from "../lib/api/client";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";
const eligibilityOptions: Array<{ value: EligibilityType; label: string }> = [
  { value: "individual", label: "Individual trainees" },
  { value: "pacs", label: "PACS nominees" },
  { value: "shg", label: "SHG nominees" },
  { value: "cooperative_institution", label: "Cooperative-institution nominees" },
];

const initialValues: ProgrammePayload = {
  title: "",
  code: "",
  summary: "",
  description: "",
  mode: "offline",
  eligibility_criteria: "",
  eligible_applicant_types: ["individual"],
  capacity: 30,
  location: "",
  language: "English and Hindi",
  duration_days: 3,
  application_deadline: "",
  start_date: "",
  end_date: "",
};

function toLocalDateTime(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function ProgrammeFormPage() {
  const { programmeId } = useParams();
  const { user, logout, can } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState<ProgrammePayload>(initialValues);
  const [institutions, setInstitutions] = useState<Array<{ id: string; name: string; code: string }>>(
    [],
  );
  const [isLoading, setIsLoading] = useState(Boolean(programmeId));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const requests: Promise<unknown>[] = [];
        if (programmeId) requests.push(apiClient.programme(programmeId));
        if (can("programmes:approve")) requests.push(apiClient.trainingInstitutions());
        const results = await Promise.all(requests);
        let resultIndex = 0;
        if (programmeId) {
          const programme = results[resultIndex] as Awaited<ReturnType<typeof apiClient.programme>>;
          resultIndex += 1;
          setValues({
            institution_id: programme.institution.id,
            title: programme.title,
            code: programme.code,
            summary: programme.summary,
            description: programme.description ?? "",
            mode: programme.mode,
            eligibility_criteria: programme.eligibility_criteria ?? "",
            eligible_applicant_types: programme.eligible_applicant_types,
            capacity: programme.capacity,
            location: programme.location ?? "",
            language: programme.language,
            duration_days: programme.duration_days,
            application_deadline: toLocalDateTime(programme.application_deadline),
            start_date: programme.start_date,
            end_date: programme.end_date,
          });
        }
        if (can("programmes:approve")) {
          setInstitutions(results[resultIndex] as Array<{ id: string; name: string; code: string }>);
        }
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "Unable to load programme details.");
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, [can, programmeId]);

  if (!user) return null;

  const update = <Key extends keyof ProgrammePayload>(key: Key, value: ProgrammePayload[Key]) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  const toggleEligibility = (value: EligibilityType) => {
    setValues((current) => ({
      ...current,
      eligible_applicant_types: current.eligible_applicant_types.includes(value)
        ? current.eligible_applicant_types.filter((item) => item !== value)
        : [...current.eligible_applicant_types, value],
    }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSaving(true);
    try {
      const payload = {
        ...values,
        application_deadline: new Date(values.application_deadline).toISOString(),
        location: values.location || null,
      };
      const programme = programmeId
        ? await apiClient.updateProgramme(programmeId, payload)
        : await apiClient.createProgramme(payload);
      navigate(`/programmes/${programme.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to save the programme.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      <Button asChild variant="ghost" size="sm" className="mb-4 -ml-3">
        <Link to={programmeId ? `/programmes/${programmeId}` : "/programmes"}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to programmes
        </Link>
      </Button>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold text-primary">Programme setup</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">
          {programmeId ? "Edit programme" : "Create programme"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Keep the details specific enough for applicants and NCCT reviewers to make a clear decision.
        </p>
      </div>

      {isLoading ? <div className="mt-6"><LoadingState label="Loading programme" /></div> : null}
      {error ? <div className="mt-6"><ErrorState title="Programme could not be saved" description={error} /></div> : null}

      {!isLoading ? (
        <form className="mt-7 max-w-5xl space-y-9" onSubmit={handleSubmit}>
          <section className="border-t pt-6" aria-labelledby="programme-basics">
            <h2 id="programme-basics" className="text-lg font-semibold">Programme details</h2>
            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              {can("programmes:approve") && !programmeId ? (
                <label className="space-y-2 sm:col-span-2">
                  <span className="text-sm font-medium">Training institution</span>
                  <select
                    className={fieldClass}
                    required
                    value={values.institution_id ?? ""}
                    onChange={(event) => update("institution_id", event.target.value)}
                  >
                    <option value="">Select an institution</option>
                    {institutions.map((institution) => (
                      <option key={institution.id} value={institution.id}>
                        {institution.name} ({institution.code})
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <label className="space-y-2 sm:col-span-2">
                <span className="text-sm font-medium">Title</span>
                <Input required minLength={3} value={values.title} onChange={(event) => update("title", event.target.value)} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">Programme code</span>
                <Input required pattern="[A-Za-z0-9-]+" value={values.code} onChange={(event) => update("code", event.target.value.toUpperCase())} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">Language</span>
                <Input required value={values.language} onChange={(event) => update("language", event.target.value)} />
              </label>
              <label className="space-y-2 sm:col-span-2">
                <span className="text-sm font-medium">Short summary</span>
                <textarea className={fieldClass} required minLength={10} maxLength={500} rows={3} value={values.summary} onChange={(event) => update("summary", event.target.value)} />
              </label>
              <label className="space-y-2 sm:col-span-2">
                <span className="text-sm font-medium">Full description</span>
                <textarea className={fieldClass} required minLength={20} rows={6} value={values.description} onChange={(event) => update("description", event.target.value)} />
              </label>
            </div>
          </section>

          <section className="border-t pt-6" aria-labelledby="delivery-details">
            <h2 id="delivery-details" className="text-lg font-semibold">Delivery and schedule</h2>
            <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              <label className="space-y-2">
                <span className="text-sm font-medium">Delivery mode</span>
                <select className={fieldClass} value={values.mode} onChange={(event) => update("mode", event.target.value as ProgrammeMode)}>
                  <option value="online">Online</option>
                  <option value="offline">Offline</option>
                  <option value="hybrid">Hybrid</option>
                </select>
              </label>
              <label className="space-y-2 lg:col-span-2">
                <span className="text-sm font-medium">Location</span>
                <Input required={values.mode !== "online"} value={values.location ?? ""} onChange={(event) => update("location", event.target.value)} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">Capacity</span>
                <Input type="number" min={1} max={10000} required value={values.capacity} onChange={(event) => update("capacity", Number(event.target.value))} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">Duration in days</span>
                <Input type="number" min={1} required value={values.duration_days} onChange={(event) => update("duration_days", Number(event.target.value))} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">Application deadline</span>
                <Input type="datetime-local" required value={values.application_deadline} onChange={(event) => update("application_deadline", event.target.value)} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">Start date</span>
                <Input type="date" required value={values.start_date} onChange={(event) => update("start_date", event.target.value)} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium">End date</span>
                <Input type="date" required value={values.end_date} onChange={(event) => update("end_date", event.target.value)} />
              </label>
            </div>
          </section>

          <section className="border-t pt-6" aria-labelledby="eligibility-details">
            <h2 id="eligibility-details" className="text-lg font-semibold">Eligibility</h2>
            <p className="mt-1 text-sm text-muted-foreground">Only selected applicant types can find and apply or nominate.</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {eligibilityOptions.map((option) => (
                <label key={option.value} className="flex min-h-12 items-center gap-3 rounded-md border bg-card px-4 py-3 text-sm">
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-primary"
                    checked={values.eligible_applicant_types.includes(option.value)}
                    onChange={() => toggleEligibility(option.value)}
                  />
                  <span>{option.label}</span>
                  {values.eligible_applicant_types.includes(option.value) ? <Check className="ml-auto h-4 w-4 text-primary" aria-hidden="true" /> : null}
                </label>
              ))}
            </div>
            <label className="mt-5 block space-y-2">
              <span className="text-sm font-medium">Eligibility criteria</span>
              <textarea className={fieldClass} required minLength={5} rows={4} value={values.eligibility_criteria} onChange={(event) => update("eligibility_criteria", event.target.value)} />
            </label>
          </section>

          <div className="flex flex-col-reverse gap-3 border-t pt-6 sm:flex-row sm:justify-end">
            <Button asChild variant="outline">
              <Link to="/programmes">Cancel</Link>
            </Button>
            <Button type="submit" disabled={isSaving || values.eligible_applicant_types.length === 0}>
              <Save className="h-4 w-4" aria-hidden="true" />
              {isSaving ? "Saving..." : "Save draft"}
            </Button>
          </div>
        </form>
      ) : null}
    </AppShell>
  );
}
