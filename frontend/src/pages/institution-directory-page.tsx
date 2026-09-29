import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Building2, ChevronRight, Network, Plus, Save, Search } from "lucide-react";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ApiError, apiClient, type InstitutionRecord, type InstitutionType } from "../lib/api/client";

const fieldClass = "h-11 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary";
const types: Array<{ value: InstitutionType; label: string }> = [
  { value: "ncct", label: "NCCT" }, { value: "vamnicom", label: "VAMNICOM" },
  { value: "ricm", label: "RICM" }, { value: "icm", label: "ICM" },
  { value: "pacs", label: "PACS" }, { value: "shg", label: "SHG" },
  { value: "dairy_cooperative", label: "Dairy cooperative" },
  { value: "other_cooperative", label: "Other cooperative" },
  { value: "nominating_institution", label: "Nominating institution" },
  { value: "employer", label: "Employer" },
];
const typeLabel = (value: InstitutionType) => types.find((item) => item.value === value)?.label ?? value;

export function InstitutionDirectoryPage() {
  const { user, logout } = useAuth();
  const [institutions, setInstitutions] = useState<InstitutionRecord[]>([]);
  const [parents, setParents] = useState<InstitutionRecord[]>([]);
  const [query, setQuery] = useState("");
  const [institutionType, setInstitutionType] = useState<InstitutionType | "">("");
  const [stateName, setStateName] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const canCreateInstitutions = user?.permissions.includes("platform:manage") ?? false;

  const load = useCallback(async () => {
    setIsLoading(true); setError(null);
    try { const result = await apiClient.institutions({ q: query || undefined, institution_type: institutionType || undefined, state: stateName || undefined, page, page_size: 12 }); setInstitutions(result.items); setPages(result.pages); setTotal(result.total); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to load institutions."); }
    finally { setIsLoading(false); }
  }, [institutionType, page, query, stateName]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!canCreateInstitutions) return;
    void apiClient.institutions({ active_only: true, page_size: 100 }).then((result) => setParents(result.items)).catch(() => setParents([]));
  }, [canCreateInstitutions]);
  if (!user) return null;

  const createInstitution = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const type = String(data.get("institution_type")) as InstitutionType;
    try { await apiClient.createInstitution({ name: String(data.get("name")), code: String(data.get("code")), institution_type: type, parent_id: type === "ncct" ? null : String(data.get("parent_id")) || null, state: String(data.get("state") ?? "") || null, district: String(data.get("district") ?? "") || null, contact_email: String(data.get("contact_email") ?? "") || null, contact_phone: String(data.get("contact_phone") ?? "") || null, profile_summary: String(data.get("profile_summary") ?? "") || null }); form.reset(); setNotice("Institution created."); await load(); const all = await apiClient.institutions({ active_only: true, page_size: 100 }); setParents(all.items); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to create the institution."); }
  };

  const updateInstitution = async (event: FormEvent<HTMLFormElement>, institution: InstitutionRecord) => {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    try { await apiClient.updateInstitution(institution.id, { name: String(data.get("name")), state: String(data.get("state") ?? "") || null, district: String(data.get("district") ?? "") || null, is_active: data.get("is_active") === "on" }); setNotice(`${institution.code} updated.`); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to update the institution."); }
  };

  return <AppShell user={user} onLogout={logout}>
    <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-sm font-semibold text-primary">Cooperative network</p><h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Institution hierarchy</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Maintain NCCT training institutes and their linked cooperative organisations.</p></div><Badge className="w-fit bg-sky-100 text-sky-800"><Network className="mr-1 h-4 w-4" aria-hidden="true" />{total} institutions in scope</Badge></div>
    {notice ? <p className="mt-5 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p> : null}
    <form className="mt-7 grid gap-3 border-y bg-card py-4 sm:grid-cols-2 lg:grid-cols-[1fr_220px_220px_auto]" onSubmit={(event) => { event.preventDefault(); if (page === 1) void load(); else setPage(1); }}><Input aria-label="Search institutions" placeholder="Name or code" value={query} onChange={(event) => setQuery(event.target.value)} /><select className={fieldClass} aria-label="Institution type filter" value={institutionType} onChange={(event) => setInstitutionType(event.target.value as InstitutionType | "")}><option value="">All types</option>{types.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select><Input aria-label="Institution state" placeholder="State" value={stateName} onChange={(event) => setStateName(event.target.value)} /><Button type="submit" variant="outline"><Search className="h-4 w-4" aria-hidden="true" />Search</Button></form>
    {canCreateInstitutions ? <details className="mt-5 rounded-md border bg-card p-5"><summary className="flex cursor-pointer items-center gap-2 font-semibold"><Plus className="h-5 w-5 text-primary" aria-hidden="true" />Add institution</summary><form className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={createInstitution}><Field label="Name"><Input name="name" required /></Field><Field label="Code"><Input name="code" required pattern="[A-Za-z0-9-]+" /></Field><Field label="Type"><select name="institution_type" className={fieldClass} required defaultValue="pacs">{types.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field><Field label="Parent institution"><select name="parent_id" className={fieldClass} defaultValue=""><option value="">None (NCCT root only)</option>{parents.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></Field><Field label="State"><Input name="state" /></Field><Field label="District"><Input name="district" /></Field><Field label="Contact email"><Input name="contact_email" type="email" /></Field><Field label="Contact phone"><Input name="contact_phone" /></Field><Field label="Profile summary" className="sm:col-span-2 lg:col-span-3"><textarea name="profile_summary" className="min-h-24 w-full rounded-md border bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary" /></Field><div className="sm:col-span-2 lg:col-span-3"><Button type="submit"><Plus className="h-4 w-4" aria-hidden="true" />Create institution</Button></div></form></details> : null}
    <div className="mt-6" aria-live="polite">{isLoading ? <LoadingState label="Loading institution hierarchy" /> : null}{error ? <ErrorState title="Institutions could not be loaded" description={error} onRetry={load} /> : null}{!isLoading && !error && institutions.length === 0 ? <EmptyState icon={Building2} title="No institutions found" description="Try changing the directory filters." /> : null}{!isLoading && !error && institutions.length ? <div className="space-y-3">{institutions.map((institution) => <article key={institution.id} className="rounded-md border bg-card p-5"><div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Badge>{typeLabel(institution.institution_type)}</Badge>{institution.is_demo ? <Badge className="bg-sky-100 text-sky-800">Demonstration data</Badge> : null}{!institution.is_active ? <Badge className="bg-red-100 text-red-800">Inactive</Badge> : null}</div><h2 className="mt-2 font-semibold">{institution.name}</h2><p className="mt-1 text-sm text-muted-foreground">{institution.code} · {[institution.district, institution.state].filter(Boolean).join(", ") || "Location not recorded"}</p>{institution.parent ? <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground"><span>{institution.parent.name}</span><ChevronRight className="h-3 w-3" aria-hidden="true" /><span>{institution.name}</span></p> : <p className="mt-2 text-xs text-muted-foreground">Root institution</p>}</div><div className="text-sm text-muted-foreground">{institution.child_count} direct child{institution.child_count === 1 ? "" : "ren"}</div></div>{institution.children.length ? <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">{institution.children.map((child) => <Badge key={child.id}>{child.code} · {typeLabel(child.institution_type)}</Badge>)}</div> : null}<details className="mt-4 border-t pt-3"><summary className="cursor-pointer text-sm font-medium text-primary">Edit institution profile</summary><form className="mt-4 grid gap-3 sm:grid-cols-3" onSubmit={(event) => void updateInstitution(event, institution)}><Field label="Name"><Input name="name" required defaultValue={institution.name} /></Field><Field label="State"><Input name="state" defaultValue={institution.state ?? ""} /></Field><Field label="District"><Input name="district" defaultValue={institution.district ?? ""} /></Field><label className="flex min-h-11 items-center gap-3 text-sm"><input name="is_active" type="checkbox" defaultChecked={institution.is_active} className="h-5 w-5 accent-primary" />Active institution</label><div className="sm:col-span-2"><Button type="submit" variant="outline"><Save className="h-4 w-4" aria-hidden="true" />Save changes</Button></div></form></details></article>)}</div> : null}</div>
    {pages > 1 ? <nav className="mt-6 flex items-center justify-between border-t pt-4" aria-label="Institution pages"><Button variant="outline" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="text-sm text-muted-foreground">Page {page} of {pages}</span><Button variant="outline" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>Next</Button></nav> : null}
  </AppShell>;
}

function Field({ label, className, children }: { label: string; className?: string; children: React.ReactNode }) { return <label className={className}><span className="mb-1.5 block text-sm font-medium">{label}</span>{children}</label>; }
