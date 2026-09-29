import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  Download,
  ExternalLink,
  FileText,
  Headphones,
  Languages,
  LoaderCircle,
  PlayCircle,
  Send,
  WifiOff,
} from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  ApiError,
  apiClient,
  type AssessmentAttempt,
  type CourseDetail,
  type CourseLesson,
  type LessonProgress,
  type LearningProgressSyncResponse,
} from "../lib/api/client";
import { useI18n } from "../i18n/i18n-provider";
import {
  downloadedLessonAsset,
  offlineCoursePackage,
  saveDownloadedLessonAsset,
  saveOfflineCourseLesson,
} from "../lib/pwa-db";
import { cn } from "../lib/utils";
import { usePwa } from "../pwa/pwa-provider";
import { cacheCurrentPageAssets } from "../pwa/register-service-worker";

const lessonIcons = {
  video: PlayCircle,
  audio: Headphones,
  pdf: FileText,
  text: FileText,
  external_resource: ExternalLink,
};

function updateLessonProgress(course: CourseDetail, lessonId: string, progress: LessonProgress) {
  return {
    ...course,
    sections: course.sections.map((section) => ({
      ...section,
      modules: section.modules.map((module) => ({
        ...module,
        lessons: module.lessons.map((lesson) =>
          lesson.id === lessonId ? { ...lesson, progress } : lesson,
        ),
      })),
    })),
  };
}

export function CoursePlayerPage() {
  const { courseId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, logout, can } = useAuth();
  const { t } = useI18n();
  const {
    isOnline,
    isReducedData,
    queueProgress,
    refreshOfflineState,
  } = usePwa();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(searchParams.get("lesson"));
  const [language, setLanguage] = useState("en");
  const [assetUrl, setAssetUrl] = useState<string | null>(null);
  const [assetBlob, setAssetBlob] = useState<Blob | null>(null);
  const [isAssetLoading, setIsAssetLoading] = useState(false);
  const [isLessonDownloaded, setIsLessonDownloaded] = useState(false);
  const [isOfflineCopy, setIsOfflineCopy] = useState(false);
  const [allowRemoteMedia, setAllowRemoteMedia] = useState(false);
  const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const lastReportPosition = useRef(0);

  const load = useCallback(async () => {
    if (!courseId) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.course(courseId);
      setCourse(result);
      setIsOfflineCopy(false);
      setLanguage(result.default_language_code);
      const lessons = result.sections.flatMap((section) => section.modules.flatMap((module) => module.lessons));
      const requested = searchParams.get("lesson");
      const initial = lessons.find((lesson) => lesson.id === requested)?.id ?? result.resume_lesson_id ?? lessons[0]?.id ?? null;
      setSelectedLessonId(initial);
    } catch (caught) {
      const saved = user ? await offlineCoursePackage(user.id, courseId).catch(() => null) : null;
      if (saved) {
        setCourse(saved.course);
        setIsOfflineCopy(true);
        setLanguage(saved.course.default_language_code);
        const requested = searchParams.get("lesson");
        const lessons = saved.course.sections.flatMap((section) =>
          section.modules.flatMap((module) => module.lessons),
        );
        setSelectedLessonId(
          lessons.find((item) => item.id === requested)?.id ?? lessons[0]?.id ?? null,
        );
        setNotice(t("learning.offlineCopy"));
      } else {
        setError(caught instanceof ApiError ? caught.message : "Unable to load this course.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [courseId, searchParams, t, user]);

  useEffect(() => {
    void load();
  }, [load]);

  const lessons = useMemo(
    () => course?.sections.flatMap((section) => section.modules.flatMap((module) => module.lessons)) ?? [],
    [course],
  );
  const lesson = lessons.find((item) => item.id === selectedLessonId) ?? null;
  const content = lesson?.contents.find((item) => item.language_code === language)
    ?? lesson?.contents.find((item) => item.language_code === course?.default_language_code)
    ?? lesson?.contents[0]
    ?? null;

  const applySynchronizedProgress = useCallback(
    (response: LearningProgressSyncResponse | null) => {
      if (!response) return;
      setCourse((current) => {
        if (!current) return current;
        return response.items.reduce(
          (updated, item) =>
            item.progress ? updateLessonProgress(updated, item.lesson_id, item.progress) : updated,
          current,
        );
      });
    },
    [],
  );

  useEffect(() => {
    if (!selectedLessonId || !can("learning:access")) return;
    lastReportPosition.current = 0;
    void queueProgress({
      lesson_id: selectedLessonId,
      action: "start",
      captured_at: new Date().toISOString(),
    }).then((response) => applySynchronizedProgress(response)).catch(() => undefined);
  }, [applySynchronizedProgress, can, queueProgress, selectedLessonId]);

  useEffect(() => {
    let objectUrl: string | null = null;
    setAssetUrl(null);
    if (assetBlob) {
      objectUrl = URL.createObjectURL(assetBlob);
      setAssetUrl(objectUrl);
    }
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [assetBlob]);

  useEffect(() => {
    let active = true;
    setAssetBlob(null);
    setIsLessonDownloaded(false);
    setAllowRemoteMedia(false);
    if (!content || !lesson || !course || !user) return;
    void Promise.all([
      downloadedLessonAsset(user.id, content.id),
      offlineCoursePackage(user.id, course.id),
    ]).then(async ([downloaded, savedCourse]) => {
      if (!active) return;
      setIsLessonDownloaded(
        Boolean(downloaded) ||
          (!content.has_asset && Boolean(savedCourse?.lesson_ids.includes(lesson.id))),
      );
      if (downloaded) {
        setAssetBlob(downloaded.blob);
        return;
      }
      if (content.has_asset && isOnline && !isReducedData) {
        setIsAssetLoading(true);
        try {
          const blob = await apiClient.lessonAsset(content.id);
          if (active) setAssetBlob(blob);
        } catch {
          if (active) setNotice("The lesson file could not be opened.");
        } finally {
          if (active) setIsAssetLoading(false);
        }
      }
    }).catch(() => undefined);
    return () => {
      active = false;
    };
  }, [content, course, isOnline, isReducedData, lesson, user]);

  if (!user) return null;

  const remoteMediaAllowed = isOnline && (!isReducedData || allowRemoteMedia);
  const mediaSource = assetUrl ?? (remoteMediaAllowed ? content?.external_url ?? undefined : undefined);
  const canDownloadLesson = lesson?.lesson_type === "text" || Boolean(content?.has_asset);

  const selectLesson = (item: CourseLesson) => {
    setSelectedLessonId(item.id);
    setSearchParams({ lesson: item.id });
    setNotice(null);
  };

  const completeLesson = async () => {
    if (!lesson || !course) return;
    setIsWorking(true);
    setNotice(null);
    try {
      const response = await queueProgress({
        lesson_id: lesson.id,
        action: "complete",
        captured_at: new Date().toISOString(),
      });
      applySynchronizedProgress(response);
      const rejected = response?.items.find(
        (item) => item.lesson_id === lesson.id && item.result === "rejected",
      );
      setNotice(
        rejected?.detail ??
          (response ? "Lesson marked complete." : t("learning.progressQueued")),
      );
    } catch (caught) {
      setNotice(
        !isOnline
          ? t("learning.progressQueued")
          : caught instanceof ApiError
            ? caught.message
            : "Unable to complete the lesson.",
      );
    } finally {
      setIsWorking(false);
    }
  };

  const mediaTimeUpdate = (event: React.SyntheticEvent<HTMLMediaElement>) => {
    if (!lesson) return;
    const current = event.currentTarget.currentTime;
    const elapsed = current - lastReportPosition.current;
    if (elapsed < 10 || elapsed > 30) return;
    lastReportPosition.current = current;
    void queueProgress({
      lesson_id: lesson.id,
      action: "heartbeat",
      captured_at: new Date().toISOString(),
      position_seconds: Math.max(0, Math.floor(current)),
      elapsed_seconds: Math.min(30, Math.max(1, Math.floor(elapsed))),
    }).then((response) => applySynchronizedProgress(response)).catch(() => undefined);
  };

  const mediaLoaded = (event: React.SyntheticEvent<HTMLMediaElement>) => {
    if (lesson?.progress.last_position_seconds) {
      event.currentTarget.currentTime = lesson.progress.last_position_seconds;
      lastReportPosition.current = lesson.progress.last_position_seconds;
    }
  };

  const loadLessonAsset = async () => {
    if (!content || !isOnline) return;
    if (!content.has_asset) {
      setAllowRemoteMedia(true);
      return;
    }
    setIsAssetLoading(true);
    setNotice(null);
    try {
      setAssetBlob(await apiClient.lessonAsset(content.id));
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "The lesson file could not be opened.");
    } finally {
      setIsAssetLoading(false);
    }
  };

  const downloadLesson = async () => {
    if (!content || !lesson || !course || !user) return;
    setIsAssetLoading(true);
    setNotice(null);
    try {
      let blob = assetBlob;
      if (content.has_asset && !blob) {
        if (!isOnline) throw new Error(t("learning.offlineUnavailable"));
        blob = await apiClient.lessonAsset(content.id);
        setAssetBlob(blob);
      }
      if (content.has_asset && blob) {
        await saveDownloadedLessonAsset({
          user_id: user.id,
          course_id: course.id,
          lesson_id: lesson.id,
          content_id: content.id,
          language_code: content.language_code,
          title: content.title,
          filename: content.filename,
          content_type: content.content_type,
          size_bytes: blob.size,
          blob,
        });
      }
      await saveOfflineCourseLesson(user.id, course, lesson.id);
      cacheCurrentPageAssets();
      setIsLessonDownloaded(true);
      await refreshOfflineState();
      setNotice(t("learning.downloaded"));
    } catch (caught) {
      setNotice(caught instanceof Error ? caught.message : "Unable to save this lesson offline.");
    } finally {
      setIsAssetLoading(false);
    }
  };

  const submitAssignment = async (event: FormEvent<HTMLFormElement>, assignmentId: string) => {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("submission") as HTMLInputElement;
    if (!input.files?.[0]) return;
    setIsWorking(true);
    setNotice(null);
    try {
      await apiClient.submitAssignment(assignmentId, input.files[0]);
      setNotice("Assignment submitted for trainer review.");
      event.currentTarget.reset();
      await load();
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "Unable to submit the assignment.");
    } finally {
      setIsWorking(false);
    }
  };

  const beginAssessment = async (assessmentId: string) => {
    setIsWorking(true);
    setNotice(null);
    try {
      setAttempt(await apiClient.startAssessment(assessmentId));
      setAnswers({});
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "Unable to start the assessment.");
    } finally {
      setIsWorking(false);
    }
  };

  const submitAssessment = async (event: FormEvent) => {
    event.preventDefault();
    if (!attempt) return;
    setIsWorking(true);
    setNotice(null);
    try {
      const submitted = await apiClient.submitAssessment(
        attempt.id,
        attempt.questions.map((question) => ({
          question_id: question.id,
          option_index: answers[question.id],
        })),
      );
      setAttempt(submitted);
      setNotice("Assessment graded. Your result is shown below.");
      await load();
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "Unable to submit the assessment.");
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      {isLoading ? <LoadingState label="Loading course" /> : null}
      {error ? <ErrorState title="Course could not be loaded" description={error} onRetry={load} /> : null}
      {!isLoading && !error && course ? (
        <div>
          <header className="border-b pb-5">
            <Button asChild variant="ghost" size="sm"><Link to="/learning"><ArrowLeft className="h-4 w-4" aria-hidden="true" />Courses</Link></Button>
            <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase text-muted-foreground">{course.programme_code} · {course.programme_title}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold tracking-normal">{course.title}</h1>{isOfflineCopy ? <Badge className="bg-amber-100 text-amber-950"><WifiOff className="mr-1 h-3.5 w-3.5" aria-hidden="true" />Offline copy</Badge> : null}</div>
              </div>
              <div className="min-w-52">
                <div className="flex justify-between text-xs"><span>Course progress</span><strong>{course.progress_percent}%</strong></div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={course.progress_percent} aria-valuemin={0} aria-valuemax={100} aria-label="Course progress">
                  <div className="h-full bg-primary" style={{ width: `${course.progress_percent}%` }} />
                </div>
              </div>
            </div>
          </header>

          {notice ? <p className="mt-4 rounded-md border border-primary/30 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" role="status">{notice}</p> : null}

          <div className="mt-6 grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
            <aside className="border-r-0 xl:border-r xl:pr-6" aria-label="Course curriculum">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold">Course content</h2>
                <label className="flex items-center gap-2 text-xs font-medium">
                  <Languages className="h-4 w-4 text-primary" aria-hidden="true" />
                  <span className="sr-only">Lesson language</span>
                  <select className="h-10 rounded-md border bg-card px-2" value={language} onChange={(event) => setLanguage(event.target.value)}>
                    {course.languages.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
                  </select>
                </label>
              </div>
              <div className="mt-4 space-y-5">
                {course.sections.map((section) => (
                  <section key={section.id}>
                    <h3 className="text-xs font-semibold uppercase text-muted-foreground">{section.title}</h3>
                    {section.modules.map((module) => (
                      <div key={module.id} className="mt-3">
                        <p className="text-sm font-medium">{module.title}</p>
                        <div className="mt-2 space-y-1">
                          {module.lessons.map((item) => {
                            const Icon = lessonIcons[item.lesson_type];
                            const complete = item.progress.status === "completed";
                            return (
                              <button key={item.id} type="button" onClick={() => selectLesson(item)} className={cn("flex min-h-12 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", selectedLessonId === item.id ? "bg-primary text-primary-foreground" : "hover:bg-muted")}>
                                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                                <span className="min-w-0 flex-1">{item.title}</span>
                                {complete ? <CheckCircle2 className="h-4 w-4 shrink-0" aria-label="Completed" /> : <Circle className="h-4 w-4 shrink-0" aria-label="Not completed" />}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </section>
                ))}
              </div>
            </aside>

            <main className="min-w-0">
              {lesson && content ? (
                <article>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <Badge className="capitalize">{lesson.lesson_type.replace("_", " ")}</Badge>
                      <h2 className="mt-3 text-xl font-semibold">{content.title}</h2>
                    </div>
                    <Badge className={lesson.progress.status === "completed" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"}>{lesson.progress.status.replace("_", " ")}</Badge>
                  </div>
                  <div className="mt-5 min-h-64 border-y py-6">
                    {lesson.lesson_type === "text" ? <p className="max-w-3xl whitespace-pre-wrap text-base leading-8">{content.text_content}</p> : null}
                    {lesson.lesson_type === "video" && mediaSource ? <video className="aspect-video w-full bg-black" controls src={mediaSource} onTimeUpdate={mediaTimeUpdate} onLoadedMetadata={mediaLoaded} /> : null}
                    {lesson.lesson_type === "audio" && mediaSource ? <audio className="w-full" controls src={mediaSource} onTimeUpdate={mediaTimeUpdate} onLoadedMetadata={mediaLoaded} /> : null}
                    {["video", "audio"].includes(lesson.lesson_type) && !mediaSource ? <div className="flex min-h-64 flex-col items-center justify-center gap-4 bg-muted px-5 text-center"><WifiOff className="h-8 w-8 text-muted-foreground" aria-hidden="true" /><p className="max-w-md text-sm text-muted-foreground">{isOnline ? t("pwa.reducedDataHint") : t("learning.offlineUnavailable")}</p>{isOnline ? <Button type="button" variant="outline" disabled={isAssetLoading} onClick={() => void loadLessonAsset()}>{isAssetLoading ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <PlayCircle className="h-4 w-4" aria-hidden="true" />}{t("learning.loadMedia")}</Button> : null}</div> : null}
                    {lesson.lesson_type === "pdf" && assetUrl ? <iframe className="h-[65vh] w-full border" src={assetUrl} title={content.title} /> : null}
                    {lesson.lesson_type === "pdf" && !assetUrl && isAssetLoading ? <LoadingState label="Opening PDF" /> : null}
                    {lesson.lesson_type === "pdf" && !assetUrl && !isAssetLoading ? <div className="flex min-h-64 flex-col items-center justify-center gap-4 bg-muted px-5 text-center"><FileText className="h-8 w-8 text-muted-foreground" aria-hidden="true" /><p className="text-sm text-muted-foreground">{isOnline ? t("pwa.reducedDataHint") : t("learning.offlineUnavailable")}</p>{isOnline ? <Button type="button" variant="outline" onClick={() => void loadLessonAsset()}>{t("learning.loadMedia")}</Button> : null}</div> : null}
                    {lesson.lesson_type === "external_resource" && isOnline ? <Button asChild><a href={content.external_url ?? "#"} target="_blank" rel="noreferrer">Open learning resource<ExternalLink className="h-4 w-4" aria-hidden="true" /></a></Button> : null}
                    {lesson.lesson_type === "external_resource" && !isOnline ? <p className="rounded-md bg-muted p-4 text-sm text-muted-foreground">{t("learning.offlineUnavailable")}</p> : null}
                  </div>
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-muted-foreground">{lesson.is_required ? "Required lesson" : "Optional lesson"}{lesson.duration_seconds ? ` · ${Math.ceil(lesson.duration_seconds / 60)} min` : ""}</p>
                    <div className="flex flex-wrap gap-2">
                      {isLessonDownloaded ? <Badge className="min-h-10 bg-emerald-100 px-3 text-emerald-900"><Download className="mr-1 h-4 w-4" aria-hidden="true" />{t("learning.downloaded")}</Badge> : can("learning:access") && canDownloadLesson ? <Button type="button" variant="outline" disabled={isAssetLoading} onClick={() => void downloadLesson()}>{isAssetLoading ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Download className="h-4 w-4" aria-hidden="true" />}{isAssetLoading ? t("learning.downloading") : t("learning.download")}</Button> : null}
                      {can("learning:access") && !["video", "audio"].includes(lesson.lesson_type) && lesson.progress.status !== "completed" ? <Button disabled={isWorking} onClick={() => void completeLesson()}><CheckCircle2 className="h-4 w-4" aria-hidden="true" />Mark complete</Button> : null}
                    </div>
                  </div>
                </article>
              ) : <EmptyState title="No lesson selected" description="Choose a lesson from the course content." />}
            </main>
          </div>

          {can("learning:access") ? (
            <div className="mt-10 grid gap-8 border-t pt-8 lg:grid-cols-2">
              <section aria-labelledby="assignments-heading">
                <h2 id="assignments-heading" className="text-lg font-semibold">Assignments</h2>
                <div className="mt-4 space-y-4">
                  {course.assignments.length ? course.assignments.map((assignment) => (
                    <article key={assignment.id} className="rounded-lg border bg-card p-5">
                      <h3 className="font-semibold">{assignment.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{assignment.instructions}</p>
                      {assignment.latest_submission ? (
                        <div className="mt-4 border-l-4 border-l-primary bg-muted p-3 text-sm">
                          <p className="font-medium">Submission {assignment.latest_submission.submission_number} · {assignment.latest_submission.status.replace("_", " ")}</p>
                          {assignment.latest_submission.score !== null ? <p className="mt-1">Score: {assignment.latest_submission.score} / {assignment.max_score}</p> : null}
                          {assignment.latest_submission.trainer_feedback ? <p className="mt-2 text-muted-foreground">Trainer feedback: {assignment.latest_submission.trainer_feedback}</p> : null}
                        </div>
                      ) : null}
                      <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(event) => void submitAssignment(event, assignment.id)}>
                        <label className="min-w-0 flex-1 text-sm font-medium">Upload response<input className="mt-2 block min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm" type="file" name="submission" accept={assignment.allowed_content_types.join(",")} required /></label>
                        <Button type="submit" disabled={isWorking}><Send className="h-4 w-4" aria-hidden="true" />Submit</Button>
                      </form>
                    </article>
                  )) : <EmptyState title="No assignments" description="This course has no published assignments." />}
                </div>
              </section>

              <section aria-labelledby="assessments-heading">
                <h2 id="assessments-heading" className="text-lg font-semibold">Assessments</h2>
                <div className="mt-4 space-y-4">
                  {attempt ? (
                    <form className="rounded-lg border bg-card p-5" onSubmit={(event) => void submitAssessment(event)}>
                      <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-medium uppercase text-primary">Attempt {attempt.attempt_number}</p><h3 className="mt-1 font-semibold">{attempt.assessment_title}</h3></div>{attempt.status === "submitted" ? <Badge className={attempt.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}>{attempt.passed ? "Passed" : "Not passed"}</Badge> : null}</div>
                      {attempt.status === "in_progress" ? (
                        <div className="mt-5 space-y-6">
                          {attempt.questions.map((question, questionIndex) => (
                            <fieldset key={question.id}><legend className="text-sm font-semibold">{questionIndex + 1}. {question.prompt}</legend><div className="mt-3 space-y-2">{question.choices.map((choice, optionIndex) => <label key={choice} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm hover:bg-muted"><input type="radio" name={question.id} checked={answers[question.id] === optionIndex} onChange={() => setAnswers((current) => ({ ...current, [question.id]: optionIndex }))} required />{choice}</label>)}</div></fieldset>
                          ))}
                          <Button type="submit" disabled={isWorking || Object.keys(answers).length !== attempt.questions.length}>Submit for grading</Button>
                        </div>
                      ) : (
                        <div className="mt-5"><p className="text-3xl font-semibold">{attempt.score_percent}%</p><p className="mt-1 text-sm text-muted-foreground">{attempt.points_earned} of {attempt.points_available} points</p>{attempt.trainer_feedback ? <p className="mt-4 border-l-4 border-l-primary bg-muted p-3 text-sm">Trainer feedback: {attempt.trainer_feedback}</p> : null}<Button className="mt-4" type="button" variant="outline" onClick={() => setAttempt(null)}>Back to assessments</Button></div>
                      )}
                    </form>
                  ) : course.assessments.length ? course.assessments.map((assessment) => (
                    <article key={assessment.id} className="rounded-lg border bg-card p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium uppercase text-primary">{assessment.assessment_type.replace("_", " ")}</p><h3 className="mt-1 font-semibold">{assessment.title}</h3></div>{assessment.passed ? <Badge className="bg-emerald-100 text-emerald-800">Passed</Badge> : null}</div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{assessment.instructions}</p>
                      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-4"><p className="text-xs text-muted-foreground">Pass mark {assessment.passing_score_percent}% · {assessment.attempts_remaining} attempts left{assessment.best_score_percent !== null ? ` · Best ${assessment.best_score_percent}%` : ""}</p><Button size="sm" disabled={isWorking || assessment.attempts_remaining === 0} onClick={() => void beginAssessment(assessment.id)}>Begin</Button></div>
                    </article>
                  )) : <EmptyState title="No assessments" description="This course has no published assessments." />}
                </div>
              </section>
            </div>
          ) : null}
        </div>
      ) : null}
    </AppShell>
  );
}
