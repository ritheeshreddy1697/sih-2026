import { Wrench } from "lucide-react";
import { Navigate, useParams } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { Badge } from "../components/ui/badge";

const sectionNames: Record<string, string> = {
  institutions: "Institutions",
  training: "Training delivery",
  learning: "My learning",
  nominations: "Nominations",
  talent: "Talent",
  reports: "Reports",
  batches: "Batch management",
  trainers: "Trainer assignments",
  attendance: "Attendance",
  materials: "Learning materials",
  assessments: "Assessments",
  schedule: "Schedule",
  submissions: "Submissions",
  nominate: "Candidate nomination",
  outcomes: "Outcomes",
  shortlist: "Shortlist",
  profile: "My profile",
  settings: "Account settings",
};

export function WorkspacePage() {
  const { section } = useParams();
  const { user, logout } = useAuth();
  if (!user) return null;
  if (!section || !sectionNames[section]) return <Navigate to="/dashboard" replace />;

  return (
    <AppShell user={user} onLogout={logout}>
      <section className="mx-auto max-w-3xl py-8 sm:py-14">
        <Badge>Prepared workspace</Badge>
        <div className="mt-5 flex h-12 w-12 items-center justify-center rounded-md bg-muted text-primary">
          <Wrench className="h-6 w-6" aria-hidden="true" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold tracking-normal sm:text-3xl">
          {sectionNames[section]}
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground sm:text-base">
          This area is ready for the next business-module phase. Your dashboard and permissions are
          already connected.
        </p>
      </section>
    </AppShell>
  );
}
