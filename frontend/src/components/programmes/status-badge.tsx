import { Badge } from "../ui/badge";

const labels: Record<string, string> = {
  draft: "Draft",
  pending_approval: "Pending approval",
  approved: "Approved",
  rejected: "Rejected",
  published: "Published",
  archived: "Archived",
  submitted: "Submitted",
  under_review: "Under review",
  waitlisted: "Wait-listed",
  withdrawn: "Withdrawn",
};

const colours: Record<string, string> = {
  published: "bg-emerald-100 text-emerald-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  pending_approval: "bg-amber-100 text-amber-900",
  waitlisted: "bg-amber-100 text-amber-900",
  under_review: "bg-sky-100 text-sky-800",
  submitted: "bg-sky-100 text-sky-800",
  archived: "bg-slate-200 text-slate-700",
  draft: "bg-slate-200 text-slate-700",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge className={colours[status]}>{labels[status] ?? status}</Badge>;
}
