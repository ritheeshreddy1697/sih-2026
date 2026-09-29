import { type FormEvent, useCallback, useEffect, useState } from "react";
import { BellRing, Check, Search, Send } from "lucide-react";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  ApiError,
  apiClient,
  type NotificationTargetType,
} from "../lib/api/client";

type TargetOption = { id: string; name: string; detail: string };

export function NotificationComposePage() {
  const { user, logout, can } = useAuth();
  const isSuperAdmin = can("platform:manage");
  const [targetType, setTargetType] = useState<NotificationTargetType>(
    isSuperAdmin ? "institutions" : "trainees",
  );
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<TargetOption[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadTargets = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (targetType === "institutions") {
        const result = await apiClient.institutions({ q: query || undefined, page_size: 100 });
        setOptions(result.items.map((item) => ({
          id: item.id,
          name: item.name,
          detail: `${item.code} · ${item.institution_type.replace(/_/g, " ")}`,
        })));
      } else if (targetType === "trainers") {
        const result = await apiClient.trainersDirectory({ q: query || undefined, page_size: 100 });
        setOptions(result.items.map((item) => ({
          id: item.user_id,
          name: item.full_name,
          detail: `${item.email} · ${item.institution?.name ?? "No institution"}`,
        })));
      } else {
        const result = await apiClient.trainees({ q: query || undefined, page_size: 100 });
        setOptions(result.items.map((item) => ({
          id: item.user_id,
          name: item.full_name,
          detail: `${item.email} · ${item.institution?.name ?? "No institution"}`,
        })));
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load notification targets.");
    } finally {
      setIsLoading(false);
    }
  }, [query, targetType]);

  useEffect(() => {
    void loadTargets();
  }, [loadTargets]);

  if (!user) return null;

  const chooseTargetType = (value: NotificationTargetType) => {
    setTargetType(value);
    setSelected(new Set());
    setQuery("");
    setNotice(null);
  };

  const toggleTarget = (id: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllShown = () => {
    setSelected((current) => {
      const next = new Set(current);
      options.forEach((option) => next.add(option.id));
      return next;
    });
  };

  const sendNotification = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setIsSending(true);
    setError(null);
    setNotice(null);
    try {
      const result = await apiClient.sendNotification({
        target_type: targetType,
        target_ids: [...selected],
        title: String(data.get("title")),
        description: String(data.get("description")),
      });
      setNotice(`Notification sent to ${result.sent_count} recipient${result.sent_count === 1 ? "" : "s"}.`);
      setSelected(new Set());
      form.reset();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to send the notification.");
    } finally {
      setIsSending(false);
    }
  };

  const targetLabel = targetType === "institutions" ? "institutions" : targetType;

  return (
    <AppShell user={user} onLogout={logout}>
      <header className="border-b pb-6">
        <p className="text-sm font-semibold text-primary">Administrative communication</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Send notification</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          {isSuperAdmin
            ? "Send an announcement to the active administrators of selected institutions."
            : "Send an announcement to selected trainers or trainees in your institution scope."}
        </p>
      </header>

      {!isSuperAdmin ? (
        <div className="mt-6 flex w-fit gap-1 rounded-md border p-1" role="tablist" aria-label="Recipient type">
          {(["trainees", "trainers"] as const).map((value) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={targetType === value}
              className={`min-h-10 px-4 text-sm font-medium capitalize ${targetType === value ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}
              onClick={() => chooseTargetType(value)}
            >
              {value}
            </button>
          ))}
        </div>
      ) : null}

      {notice ? <p className="mt-5 border-l-4 border-emerald-600 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" role="status">{notice}</p> : null}
      {error ? <div className="mt-5"><ErrorState title="Notification could not be completed" description={error} onRetry={loadTargets} /></div> : null}

      <form className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]" onSubmit={sendNotification}>
        <section aria-labelledby="recipients-heading">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 id="recipients-heading" className="text-lg font-semibold capitalize">Choose {targetLabel}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{selected.size} selected</p>
            </div>
            <Button type="button" variant="outline" size="sm" disabled={!options.length} onClick={selectAllShown}>
              <Check className="h-4 w-4" aria-hidden="true" />Select all shown
            </Button>
          </div>
          <label className="relative mt-4 block">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <Input className="pl-9" aria-label={`Search ${targetLabel}`} placeholder={targetType === "institutions" ? "Search institutions by name or code" : `Search ${targetLabel} by name or ID`} value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <div className="mt-4" aria-live="polite">
            {isLoading ? <LoadingState label={`Loading ${targetLabel}`} /> : null}
            {!isLoading && !error && !options.length ? <EmptyState icon={BellRing} title={`No ${targetLabel} found`} description="Try changing the search text." /> : null}
            {!isLoading && options.length ? (
              <div className="max-h-[480px] divide-y overflow-y-auto rounded-md border bg-card">
                {options.map((option) => (
                  <label key={option.id} className="flex min-h-16 cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/60">
                    <input type="checkbox" className="mt-1 h-5 w-5 accent-primary" checked={selected.has(option.id)} onChange={() => toggleTarget(option.id)} />
                    <span className="min-w-0"><span className="block truncate text-sm font-medium">{option.name}</span><span className="mt-1 block truncate text-xs text-muted-foreground">{option.detail}</span></span>
                  </label>
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <section aria-labelledby="message-heading">
          <h2 id="message-heading" className="text-lg font-semibold">Message</h2>
          <div className="mt-4 space-y-4 rounded-md border bg-card p-5">
            <label><span className="mb-1.5 block text-sm font-medium">Title</span><Input name="title" required minLength={3} maxLength={160} /></label>
            <label><span className="mb-1.5 block text-sm font-medium">Notification message</span><textarea name="description" required minLength={3} maxLength={1000} className="min-h-40 w-full rounded-md border bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary" /></label>
            <Button className="w-full" type="submit" disabled={!selected.size || isSending}>
              <Send className="h-4 w-4" aria-hidden="true" />{isSending ? "Sending..." : `Send to ${selected.size || 0}`}
            </Button>
          </div>
        </section>
      </form>
    </AppShell>
  );
}
