import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowRight, BookOpenCheck, Languages, Plus, Settings2, WifiOff } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ApiError, apiClient, type CourseListItem, type Programme } from "../lib/api/client";
import { offlineCoursePackages } from "../lib/pwa-db";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

export function LearningPage() {
  const { user, logout, can } = useAuth();
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isOfflineList, setIsOfflineList] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.courses();
      setCourses(result.items);
      setIsOfflineList(false);
    } catch (caught) {
      const saved = user ? await offlineCoursePackages(user.id).catch(() => []) : [];
      if (saved.length) {
        setCourses(saved.map((item) => item.course));
        setIsOfflineList(true);
      } else {
        setError(caught instanceof ApiError ? caught.message : "Unable to load learning courses.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!can("learning:manage")) return;
    void apiClient
      .programmes()
      .then((result) => setProgrammes(result.items))
      .catch(() => setProgrammes([]));
  }, [can]);

  if (!user) return null;

  const createCourse = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setFormError(null);
    const data = new FormData(event.currentTarget);
    try {
      await apiClient.createCourse({
        programme_id: String(data.get("programme_id")),
        title: String(data.get("title")),
        summary: String(data.get("summary")),
        default_language_code: String(data.get("default_language_code")),
      });
      event.currentTarget.reset();
      setShowCreate(false);
      await load();
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "Unable to create the course.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      <header className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-primary">Digital learning</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal sm:text-3xl">Courses</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {can("learning:manage")
              ? "Build learning journeys for the programmes assigned to you."
              : "Continue your enrolled courses, assignments and assessments."}
          </p>
        </div>
        {can("learning:manage") ? (
          <Button onClick={() => setShowCreate((current) => !current)} aria-expanded={showCreate}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            New course
          </Button>
        ) : null}
      </header>

      {showCreate ? (
        <form className="mt-6 border-b pb-6" onSubmit={(event) => void createCourse(event)}>
          <h2 className="text-base font-semibold">Connect a course to a programme</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium">
              Programme
              <select className={`${fieldClass} mt-2`} name="programme_id" required>
                <option value="">Select a programme</option>
                {programmes.map((programme) => (
                  <option key={programme.id} value={programme.id}>
                    {programme.code} · {programme.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium">
              Course title
              <Input className="mt-2" name="title" minLength={3} required />
            </label>
            <label className="text-sm font-medium md:col-span-2">
              Summary
              <textarea className={`${fieldClass} mt-2 min-h-24`} name="summary" minLength={10} required />
            </label>
            <label className="text-sm font-medium">
              Default language code
              <Input className="mt-2" name="default_language_code" defaultValue="en" minLength={2} required />
            </label>
          </div>
          {formError ? <p className="mt-3 text-sm text-destructive" role="alert">{formError}</p> : null}
          <div className="mt-4 flex gap-3">
            <Button type="submit" disabled={isSaving}>{isSaving ? "Creating…" : "Create course"}</Button>
            <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
          </div>
        </form>
      ) : null}

      <div className="mt-6" aria-live="polite">
        {isOfflineList ? <p className="mb-4 flex min-h-11 items-center gap-2 rounded-md border border-amber-300 bg-amber-100 px-4 py-2 text-sm font-medium text-amber-950" role="status"><WifiOff className="h-4 w-4" aria-hidden="true" />Showing lessons downloaded on this device.</p> : null}
        {isLoading ? <LoadingState label="Loading courses" /> : null}
        {error ? <ErrorState title="Courses could not be loaded" description={error} onRetry={load} /> : null}
        {!isLoading && !error && courses.length === 0 ? (
          <EmptyState
            title="No courses available"
            description={can("learning:manage") ? "Create a course for an assigned programme." : "Your enrolled courses will appear here."}
          />
        ) : null}
        {!isLoading && !error && courses.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {courses.map((course) => (
              <article key={course.id} className="rounded-lg border bg-card p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase text-muted-foreground">{course.programme_code}</p>
                    <h2 className="mt-1 text-lg font-semibold">{course.title}</h2>
                  </div>
                  <Badge className={course.status === "published" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}>
                    {course.status}
                  </Badge>
                </div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{course.summary}</p>
                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
                  <span className="flex items-center gap-2"><BookOpenCheck className="h-4 w-4 text-primary" aria-hidden="true" />{course.lesson_count} lessons</span>
                  <span className="flex items-center gap-2"><Languages className="h-4 w-4 text-primary" aria-hidden="true" />{course.languages.map((item) => item.name).join(", ")}</span>
                </div>
                {!course.can_manage ? (
                  <div className="mt-5">
                    <div className="flex items-center justify-between text-xs">
                      <span>{course.completed_lesson_count} of {course.lesson_count} lessons complete</span>
                      <span className="font-semibold">{course.progress_percent}%</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-label={`${course.title} progress`} aria-valuenow={course.progress_percent} aria-valuemin={0} aria-valuemax={100}>
                      <div className="h-full bg-primary" style={{ width: `${course.progress_percent}%` }} />
                    </div>
                  </div>
                ) : null}
                <div className="mt-5 flex flex-wrap justify-end gap-2 border-t pt-4">
                  {course.can_manage ? (
                    <Button asChild variant="outline">
                      <Link to={`/learning/courses/${course.id}/manage`}><Settings2 className="h-4 w-4" aria-hidden="true" />Manage</Link>
                    </Button>
                  ) : null}
                  <Button asChild>
                    <Link to={`/learning/courses/${course.id}${course.resume_lesson_id ? `?lesson=${course.resume_lesson_id}` : ""}`}>
                      {course.progress_percent ? "Resume course" : "Start course"}
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
