import { type FormEvent, useState } from "react";
import { ArrowLeft, CheckCircle2, UserPlus } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AuthLayout } from "../components/auth/auth-layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ApiError, apiClient, type RegistrationPayload } from "../lib/api/client";

const accountTypes: Array<{ value: RegistrationPayload["role_code"]; label: string }> = [
  { value: "trainee", label: "Trainee" },
  { value: "nominating_institution", label: "Nominating institution" },
  { value: "employer_recruiter", label: "Employer / recruiter" },
];

export function RegisterPage() {
  const { user, isLoading } = useAuth();
  const [form, setForm] = useState<RegistrationPayload>({
    full_name: "",
    email: "",
    password: "",
    role_code: "trainee",
    phone: "",
    organisation_name: "",
    industry: "",
    website: "",
    company_size: "",
    company_description: "",
    headquarters: "",
    registration_number: "",
    consent_accepted: false,
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isLoading && user) return <Navigate to="/dashboard" replace />;

  const isOrganisation = form.role_code !== "trainee";
  const isEmployer = form.role_code === "employer_recruiter";
  const update = <Key extends keyof RegistrationPayload>(
    key: Key,
    value: RegistrationPayload[Key],
  ) => setForm((current) => ({ ...current, [key]: value }));

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await apiClient.register(form);
      setMessage(result.message);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Registration could not be completed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      description="Trainees, nominating institutions and employers can request access here."
      footer={
        <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
          <Link className="inline-flex items-center gap-2 font-medium text-primary hover:underline" to="/">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Home
          </Link>
          <Link className="font-medium text-primary hover:underline" to="/login">Already registered? Sign in</Link>
        </div>
      }
    >
      {message ? (
        <div className="space-y-5 text-center" aria-live="polite">
          <CheckCircle2 className="mx-auto h-10 w-10 text-primary" aria-hidden="true" />
          <p className="text-sm leading-6 text-muted-foreground">{message}</p>
          <Button asChild className="w-full"><Link to="/login">Go to sign in</Link></Button>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit} aria-describedby={error ? "registration-error" : undefined}>
          {error ? <p id="registration-error" className="rounded-md bg-destructive/5 p-3 text-sm text-destructive" role="alert">{error}</p> : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="full-name">Full name</label>
              <Input id="full-name" autoComplete="name" value={form.full_name} onChange={(event) => update("full_name", event.target.value)} required />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="registration-email">Email address</label>
              <Input id="registration-email" type="email" autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} required />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="account-type">Account type</label>
              <select
                id="account-type"
                className="h-11 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
                value={form.role_code}
                onChange={(event) => update("role_code", event.target.value as RegistrationPayload["role_code"])}
              >
                {accountTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="phone">Phone number</label>
              <Input id="phone" type="tel" autoComplete="tel" value={form.phone} onChange={(event) => update("phone", event.target.value)} />
            </div>
            {isOrganisation ? (
              <div className="space-y-2 sm:col-span-2">
                <label className="text-sm font-medium" htmlFor="organisation">Organisation name</label>
                <Input id="organisation" autoComplete="organization" value={form.organisation_name} onChange={(event) => update("organisation_name", event.target.value)} required />
              </div>
            ) : null}
            {isEmployer ? (
              <>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="industry">Industry</label>
                  <Input id="industry" value={form.industry} onChange={(event) => update("industry", event.target.value)} required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="company-size">Company size</label>
                  <Input id="company-size" placeholder="For example, 51-200" value={form.company_size} onChange={(event) => update("company_size", event.target.value)} />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <label className="text-sm font-medium" htmlFor="headquarters">Headquarters</label>
                  <Input id="headquarters" autoComplete="address-level2" value={form.headquarters} onChange={(event) => update("headquarters", event.target.value)} required />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <label className="text-sm font-medium" htmlFor="company-description">Company description</label>
                  <textarea id="company-description" className="min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary" minLength={20} value={form.company_description} onChange={(event) => update("company_description", event.target.value)} required />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="company-website">Website</label>
                  <Input id="company-website" type="url" autoComplete="url" value={form.website} onChange={(event) => update("website", event.target.value)} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="registration-number">Registration number</label>
                  <Input id="registration-number" value={form.registration_number} onChange={(event) => update("registration_number", event.target.value)} />
                </div>
              </>
            ) : null}
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="registration-password">Create password</label>
              <Input id="registration-password" type="password" autoComplete="new-password" minLength={12} value={form.password} onChange={(event) => update("password", event.target.value)} required />
              <p className="text-xs text-muted-foreground">Use at least 12 characters.</p>
            </div>
          </div>
          <label className="flex cursor-pointer items-start gap-3 rounded-md border p-3 text-sm leading-6">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-primary"
              checked={form.consent_accepted}
              onChange={(event) => update("consent_accepted", event.target.checked)}
              required
            />
            <span>I agree to the platform privacy and account-use terms.</span>
          </label>
          <Button className="h-11 w-full" type="submit" disabled={isSubmitting}>
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? "Submitting..." : "Request account"}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
