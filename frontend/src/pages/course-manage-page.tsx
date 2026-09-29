import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  FileQuestion,
  FolderPlus,
  Languages,
  Plus,
  Send,
  Upload,
  UsersRound,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

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
  type AssessmentAttempt,
  type AssessmentType,
  type AssignmentSubmission,
  type CourseDetail,
  type LessonType,
  type QuestionBank,
} from "../lib/api/client";

const fieldClass =
  "min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

export function CourseManagePage() {
  const { courseId } = useParams();
  const { user, logout } = useAuth();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [banks, setBanks] = useState<QuestionBank[]>([]);
  const [submissions, setSubmissions] = useState<Record<string, AssignmentSubmission[]>>({});
  const [attempts, setAttempts] = useState<Record<string, AssessmentAttempt[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedLessonId, setSelectedLessonId] = useState("");

  const load = useCallback(async () => {
    if (!courseId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [courseResult, bankResult] = await Promise.all([
        apiClient.course(courseId),
        apiClient.questionBanks(courseId),
      ]);
      setCourse(courseResult);
      setBanks(bankResult);
      const firstLesson = courseResult.sections.flatMap((section) =>
        section.modules.flatMap((module) => module.lessons),
      )[0];
      setSelectedLessonId((current) => current || firstLesson?.id || "");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load course management.");
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    void load();
  }, [load]);

  const lessons = useMemo(
    () => course?.sections.flatMap((section) =>
      section.modules.flatMap((module) => module.lessons),
    ) ?? [],
    [course],
  );
  const modules = useMemo(
    () => course?.sections.flatMap((section) => section.modules) ?? [],
    [course],
  );
  const selectedLesson = lessons.find((item) => item.id === selectedLessonId);

  if (!user) return null;

  const perform = async (action: () => Promise<unknown>, success: string, form?: HTMLFormElement) => {
    setIsWorking(true);
    setNotice(null);
    try {
      await action();
      form?.reset();
      setNotice(success);
      await load();
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "The change could not be saved.");
    } finally {
      setIsWorking(false);
    }
  };

  const formData = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    return { form: event.currentTarget, data: new FormData(event.currentTarget) };
  };

  const loadSubmissions = async (assignmentId: string) => {
    try {
      const result = await apiClient.assignmentSubmissions(assignmentId);
      setSubmissions((current) => ({ ...current, [assignmentId]: result }));
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "Unable to load submissions.");
    }
  };

  const loadAttempts = async (assessmentId: string) => {
    try {
      const result = await apiClient.assessmentAttempts(assessmentId);
      setAttempts((current) => ({ ...current, [assessmentId]: result }));
    } catch (caught) {
      setNotice(caught instanceof ApiError ? caught.message : "Unable to load attempts.");
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      {isLoading ? <LoadingState label="Loading course workspace" /> : null}
      {error ? <ErrorState title="Course workspace could not be loaded" description={error} onRetry={load} /> : null}
      {!isLoading && !error && course ? (
        <div className="space-y-9">
          <header className="border-b pb-6">
            <Button asChild variant="ghost" size="sm"><Link to="/learning"><ArrowLeft className="h-4 w-4" aria-hidden="true" />Courses</Link></Button>
            <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs font-medium uppercase text-muted-foreground">{course.programme_code} · Content management</p>
                <h1 className="mt-1 text-2xl font-semibold tracking-normal">{course.title}</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{course.summary}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={course.status === "published" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}>{course.status}</Badge>
                {course.status === "draft" ? <Button disabled={isWorking} onClick={() => void perform(() => apiClient.updateCourse(course.id, { status: "published" }), "Course published.")}><CheckCircle2 className="h-4 w-4" aria-hidden="true" />Publish</Button> : null}
                {course.status === "published" ? <Button variant="outline" disabled={isWorking} onClick={() => void perform(() => apiClient.updateCourse(course.id, { status: "archived" }), "Course archived.")}><Archive className="h-4 w-4" aria-hidden="true" />Archive</Button> : null}
              </div>
            </div>
          </header>

          {notice ? <p className="rounded-md border border-primary/30 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" role="status">{notice}</p> : null}

          <section aria-labelledby="languages-heading">
            <div className="flex items-center gap-3"><Languages className="h-5 w-5 text-primary" aria-hidden="true" /><div><h2 id="languages-heading" className="text-lg font-semibold">Languages</h2><p className="text-sm text-muted-foreground">Add language codes before uploading localized lesson content.</p></div></div>
            <div className="mt-4 flex flex-wrap gap-2">{course.languages.map((item) => <Badge key={item.id}>{item.name} · {item.code}</Badge>)}</div>
            <form className="mt-4 grid gap-3 sm:grid-cols-[140px_1fr_auto]" onSubmit={(event) => { const { form, data } = formData(event); void perform(() => apiClient.addCourseLanguage(course.id, String(data.get("code")), String(data.get("name"))), "Language added.", form); }}>
              <label className="text-sm font-medium">Code<Input className="mt-2" name="code" placeholder="hi" pattern="[a-z]{2,3}(-[A-Z]{2})?" required /></label>
              <label className="text-sm font-medium">Language name<Input className="mt-2" name="name" placeholder="Hindi" minLength={2} required /></label>
              <Button className="self-end" type="submit" disabled={isWorking}><Plus className="h-4 w-4" aria-hidden="true" />Add</Button>
            </form>
          </section>

          <section className="border-y py-8" aria-labelledby="curriculum-heading">
            <div className="flex items-center gap-3"><BookOpenCheck className="h-5 w-5 text-primary" aria-hidden="true" /><div><h2 id="curriculum-heading" className="text-lg font-semibold">Curriculum</h2><p className="text-sm text-muted-foreground">Build sections, modules and lessons in display order.</p></div></div>
            <form className="mt-5 grid gap-3 sm:grid-cols-[1fr_120px_auto]" onSubmit={(event) => { const { form, data } = formData(event); void perform(() => apiClient.addCourseSection(course.id, String(data.get("title")), Number(data.get("position"))), "Section added.", form); }}>
              <label className="text-sm font-medium">New section<Input className="mt-2" name="title" minLength={2} required /></label>
              <label className="text-sm font-medium">Position<Input className="mt-2" name="position" type="number" min={1} defaultValue={course.sections.length + 1} required /></label>
              <Button className="self-end" type="submit" variant="outline" disabled={isWorking}><FolderPlus className="h-4 w-4" aria-hidden="true" />Add section</Button>
            </form>
            <div className="mt-6 space-y-6">
              {course.sections.map((section) => (
                <div key={section.id} className="border-l-4 border-l-primary pl-4">
                  <h3 className="font-semibold">{section.position}. {section.title}</h3>
                  <form className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_100px_auto]" onSubmit={(event) => { const { form, data } = formData(event); void perform(() => apiClient.addCourseModule(section.id, { title: String(data.get("title")), description: String(data.get("description")) || undefined, position: Number(data.get("position")) }), "Module added.", form); }}>
                    <label className="text-sm font-medium">Module title<Input className="mt-2" name="title" minLength={2} required /></label>
                    <label className="text-sm font-medium">Description<Input className="mt-2" name="description" /></label>
                    <label className="text-sm font-medium">Position<Input className="mt-2" name="position" type="number" min={1} defaultValue={section.modules.length + 1} required /></label>
                    <Button className="self-end" type="submit" variant="outline" disabled={isWorking}>Add module</Button>
                  </form>
                  <div className="mt-4 space-y-4">
                    {section.modules.map((module) => (
                      <div key={module.id} className="ml-0 border-t pt-4 sm:ml-4">
                        <p className="text-sm font-semibold">{module.position}. {module.title}</p>
                        {module.description ? <p className="mt-1 text-xs text-muted-foreground">{module.description}</p> : null}
                        <ul className="mt-3 grid gap-2 sm:grid-cols-2">{module.lessons.map((lesson) => <li key={lesson.id} className="flex min-h-11 items-center justify-between gap-2 rounded-md bg-muted px-3 py-2 text-sm"><span>{lesson.position}. {lesson.title}</span><Badge className="capitalize">{lesson.lesson_type.replace("_", " ")}</Badge></li>)}</ul>
                        <form className="mt-3 grid gap-3 md:grid-cols-[1fr_170px_90px_120px_auto]" onSubmit={(event) => { const { form, data } = formData(event); const type = String(data.get("lesson_type")) as LessonType; const duration = Number(data.get("duration_seconds")); void perform(() => apiClient.addCourseLesson(module.id, { title: String(data.get("title")), lesson_type: type, position: Number(data.get("position")), duration_seconds: duration || undefined, is_required: data.get("is_required") === "on" }), "Lesson added.", form); }}>
                          <label className="text-sm font-medium">Lesson title<Input className="mt-2" name="title" minLength={2} required /></label>
                          <label className="text-sm font-medium">Type<select className={`${fieldClass} mt-2`} name="lesson_type" required>{(["text", "video", "audio", "pdf", "external_resource"] as LessonType[]).map((type) => <option key={type} value={type}>{type.replace("_", " ")}</option>)}</select></label>
                          <label className="text-sm font-medium">Position<Input className="mt-2" name="position" type="number" min={1} defaultValue={module.lessons.length + 1} required /></label>
                          <label className="text-sm font-medium">Duration (sec)<Input className="mt-2" name="duration_seconds" type="number" min={1} /></label>
                          <div className="self-end"><label className="mb-2 flex items-center gap-2 text-xs"><input name="is_required" type="checkbox" defaultChecked />Required</label><Button type="submit" variant="outline" disabled={isWorking}>Add lesson</Button></div>
                        </form>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section aria-labelledby="content-heading">
            <div className="flex items-center gap-3"><Upload className="h-5 w-5 text-primary" aria-hidden="true" /><div><h2 id="content-heading" className="text-lg font-semibold">Localized lesson content</h2><p className="text-sm text-muted-foreground">Text uses written content, external lessons use a URL, and PDF lessons require a file.</p></div></div>
            {lessons.length ? (
              <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={(event) => { const { form, data } = formData(event); const file = (form.elements.namedItem("file") as HTMLInputElement).files?.[0]; void perform(() => apiClient.putLessonContent(String(data.get("lesson_id")), { language_code: String(data.get("language_code")), title: String(data.get("title")), text_content: String(data.get("text_content")) || undefined, external_url: String(data.get("external_url")) || undefined, file }), "Lesson content saved.", form); }}>
                <label className="text-sm font-medium">Lesson<select className={`${fieldClass} mt-2`} name="lesson_id" value={selectedLessonId} onChange={(event) => setSelectedLessonId(event.target.value)} required>{lessons.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
                <label className="text-sm font-medium">Language<select className={`${fieldClass} mt-2`} name="language_code" required>{course.languages.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>
                <label className="text-sm font-medium md:col-span-2">Localized title<Input className="mt-2" name="title" minLength={2} required /></label>
                {selectedLesson?.lesson_type === "text" ? <label className="text-sm font-medium md:col-span-2">Lesson text<textarea className={`${fieldClass} mt-2 min-h-32`} name="text_content" required /></label> : null}
                {["video", "audio", "external_resource"].includes(selectedLesson?.lesson_type ?? "") ? <label className="text-sm font-medium md:col-span-2">External resource URL<Input className="mt-2" name="external_url" type="url" required={selectedLesson?.lesson_type === "external_resource"} /></label> : null}
                {["video", "audio", "pdf"].includes(selectedLesson?.lesson_type ?? "") ? <label className="text-sm font-medium md:col-span-2">Lesson file<input className="mt-2 block min-h-11 w-full rounded-md border bg-card px-3 py-2 text-sm" name="file" type="file" accept={selectedLesson?.lesson_type === "pdf" ? "application/pdf" : selectedLesson?.lesson_type === "video" ? "video/mp4,video/webm" : "audio/mpeg,audio/wav,audio/ogg"} required={selectedLesson?.lesson_type === "pdf"} /></label> : null}
                <Button className="w-fit" type="submit" disabled={isWorking}>Save content</Button>
              </form>
            ) : <EmptyState title="No lessons yet" description="Add a lesson before uploading content." />}
          </section>

          <section className="border-y py-8" aria-labelledby="assignment-heading">
            <div className="flex items-center gap-3"><Send className="h-5 w-5 text-primary" aria-hidden="true" /><div><h2 id="assignment-heading" className="text-lg font-semibold">Assignments and review</h2><p className="text-sm text-muted-foreground">Published assignments accept validated PDF or Word files up to 10 MB.</p></div></div>
            <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={(event) => { const { form, data } = formData(event); void perform(() => apiClient.createAssignment(course.id, { module_id: String(data.get("module_id")) || undefined, title: String(data.get("title")), instructions: String(data.get("instructions")), max_score: Number(data.get("max_score")), allowed_content_types: ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"], is_published: data.get("is_published") === "on" }), "Assignment created.", form); }}>
              <label className="text-sm font-medium">Title<Input className="mt-2" name="title" minLength={3} required /></label>
              <label className="text-sm font-medium">Module<select className={`${fieldClass} mt-2`} name="module_id"><option value="">Whole course</option>{modules.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
              <label className="text-sm font-medium md:col-span-2">Instructions<textarea className={`${fieldClass} mt-2 min-h-24`} name="instructions" minLength={10} required /></label>
              <label className="text-sm font-medium">Maximum score<Input className="mt-2" name="max_score" type="number" min={1} defaultValue={100} required /></label>
              <label className="flex items-center gap-2 self-end pb-3 text-sm font-medium"><input name="is_published" type="checkbox" defaultChecked />Publish now</label>
              <Button className="w-fit" type="submit" disabled={isWorking}>Create assignment</Button>
            </form>
            <div className="mt-7 space-y-5">
              {course.assignments.map((assignment) => (
                <article key={assignment.id} className="rounded-lg border bg-card p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{assignment.title}</h3><p className="mt-1 text-sm text-muted-foreground">Maximum {assignment.max_score} points</p></div><Button size="sm" variant="outline" onClick={() => void loadSubmissions(assignment.id)}><UsersRound className="h-4 w-4" aria-hidden="true" />Load submissions</Button></div>
                  {submissions[assignment.id]?.length === 0 ? <p className="mt-4 text-sm text-muted-foreground">No submissions yet.</p> : null}
                  <div className="mt-4 space-y-4">{submissions[assignment.id]?.map((submission) => <form key={submission.id} className="grid gap-3 border-t pt-4 md:grid-cols-[1fr_120px_180px_auto]" onSubmit={(event) => { const { data } = formData(event); void perform(() => apiClient.reviewAssignment(submission.id, { score: data.get("score") ? Number(data.get("score")) : undefined, trainer_feedback: String(data.get("trainer_feedback")), status: String(data.get("status")) as "reviewed" | "resubmission_requested" }), "Assignment feedback saved.").then(() => loadSubmissions(assignment.id)); }}><div><p className="text-sm font-medium">{submission.trainee_name}</p><p className="text-xs text-muted-foreground">{submission.filename} · Submission {submission.submission_number}</p></div><label className="text-sm font-medium">Score<Input className="mt-2" name="score" type="number" min={0} max={assignment.max_score} defaultValue={submission.score ?? ""} /></label><label className="text-sm font-medium">Decision<select className={`${fieldClass} mt-2`} name="status" defaultValue={submission.status === "submitted" ? "reviewed" : submission.status}><option value="reviewed">Reviewed</option><option value="resubmission_requested">Request resubmission</option></select></label><div><label className="text-sm font-medium">Feedback<Input className="mt-2" name="trainer_feedback" defaultValue={submission.trainer_feedback ?? ""} minLength={2} required /></label><Button className="mt-2" size="sm" type="submit">Save review</Button></div></form>)}</div>
                </article>
              ))}
            </div>
          </section>

          <section aria-labelledby="question-heading">
            <div className="flex items-center gap-3"><FileQuestion className="h-5 w-5 text-primary" aria-hidden="true" /><div><h2 id="question-heading" className="text-lg font-semibold">Question banks</h2><p className="text-sm text-muted-foreground">Correct answers stay in the trainer view and are never returned in trainee attempts.</p></div></div>
            <form className="mt-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={(event) => { const { form, data } = formData(event); void perform(() => apiClient.createQuestionBank(course.id, { title: String(data.get("title")), description: String(data.get("description")) || undefined }), "Question bank created.", form); }}>
              <label className="text-sm font-medium">Bank title<Input className="mt-2" name="title" minLength={3} required /></label><label className="text-sm font-medium">Description<Input className="mt-2" name="description" /></label><Button className="self-end" type="submit" variant="outline">Create bank</Button>
            </form>
            {banks.length ? <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={(event) => { const { form, data } = formData(event); const choices = [0, 1, 2, 3].map((index) => String(data.get(`choice_${index}`))).filter(Boolean); void perform(() => apiClient.addQuestion(String(data.get("bank_id")), { prompt: String(data.get("prompt")), choices, correct_option_index: Number(data.get("correct_option_index")), explanation: String(data.get("explanation")) || undefined, points: Number(data.get("points")), position: Number(data.get("position")) }), "Question added.", form); }}>
              <label className="text-sm font-medium">Question bank<select className={`${fieldClass} mt-2`} name="bank_id" required>{banks.map((bank) => <option key={bank.id} value={bank.id}>{bank.title} ({bank.questions.length})</option>)}</select></label><label className="text-sm font-medium">Position<Input className="mt-2" name="position" type="number" min={1} defaultValue={1} required /></label><label className="text-sm font-medium md:col-span-2">Question prompt<textarea className={`${fieldClass} mt-2 min-h-20`} name="prompt" minLength={3} required /></label>{[0, 1, 2, 3].map((index) => <label key={index} className="text-sm font-medium">Choice {index + 1}<Input className="mt-2" name={`choice_${index}`} required={index < 2} /></label>)}<label className="text-sm font-medium">Correct choice<select className={`${fieldClass} mt-2`} name="correct_option_index"><option value="0">Choice 1</option><option value="1">Choice 2</option><option value="2">Choice 3</option><option value="3">Choice 4</option></select></label><label className="text-sm font-medium">Points<Input className="mt-2" name="points" type="number" min={0.5} step={0.5} defaultValue={1} required /></label><label className="text-sm font-medium md:col-span-2">Answer explanation<Input className="mt-2" name="explanation" /></label><Button className="w-fit" type="submit">Add question</Button>
            </form> : <EmptyState title="No question banks" description="Create a bank before adding multiple-choice questions." />}
          </section>

          <section className="border-t pt-8" aria-labelledby="assessment-heading">
            <h2 id="assessment-heading" className="text-lg font-semibold">Assessments and trainer feedback</h2>
            <p className="mt-1 text-sm text-muted-foreground">Configure pre-training, practice and post-training checks with server-side grading.</p>
            {banks.length ? <form className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3" onSubmit={(event) => { const { form, data } = formData(event); void perform(() => apiClient.createAssessment(course.id, { question_bank_id: String(data.get("question_bank_id")), title: String(data.get("title")), instructions: String(data.get("instructions")) || undefined, assessment_type: String(data.get("assessment_type")) as AssessmentType, attempt_limit: Number(data.get("attempt_limit")), passing_score_percent: Number(data.get("passing_score_percent")), is_published: data.get("is_published") === "on" }), "Assessment created.", form); }}>
              <label className="text-sm font-medium">Assessment title<Input className="mt-2" name="title" minLength={3} required /></label><label className="text-sm font-medium">Question bank<select className={`${fieldClass} mt-2`} name="question_bank_id">{banks.map((bank) => <option key={bank.id} value={bank.id}>{bank.title}</option>)}</select></label><label className="text-sm font-medium">Type<select className={`${fieldClass} mt-2`} name="assessment_type"><option value="pre_training">Pre-training</option><option value="quiz">Quiz</option><option value="post_training">Post-training</option></select></label><label className="text-sm font-medium lg:col-span-3">Instructions<Input className="mt-2" name="instructions" /></label><label className="text-sm font-medium">Attempt limit<Input className="mt-2" name="attempt_limit" type="number" min={1} max={20} defaultValue={2} required /></label><label className="text-sm font-medium">Passing score (%)<Input className="mt-2" name="passing_score_percent" type="number" min={0} max={100} defaultValue={60} required /></label><label className="flex items-center gap-2 self-end pb-3 text-sm font-medium"><input name="is_published" type="checkbox" defaultChecked />Publish now</label><Button className="w-fit" type="submit">Create assessment</Button>
            </form> : null}
            <div className="mt-7 space-y-5">{course.assessments.map((assessment) => <article key={assessment.id} className="rounded-lg border bg-card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium uppercase text-primary">{assessment.assessment_type.replace("_", " ")}</p><h3 className="mt-1 font-semibold">{assessment.title}</h3><p className="mt-1 text-sm text-muted-foreground">Pass {assessment.passing_score_percent}% · {assessment.attempt_limit} attempts</p></div><Button size="sm" variant="outline" onClick={() => void loadAttempts(assessment.id)}><UsersRound className="h-4 w-4" aria-hidden="true" />Load attempts</Button></div>{attempts[assessment.id]?.length === 0 ? <p className="mt-4 text-sm text-muted-foreground">No attempts yet.</p> : null}<div className="mt-4 space-y-4">{attempts[assessment.id]?.map((attempt) => <form key={attempt.id} className="grid gap-3 border-t pt-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={(event) => { const { data } = formData(event); void perform(() => apiClient.addAssessmentFeedback(attempt.id, String(data.get("feedback"))), "Assessment feedback saved.").then(() => loadAttempts(assessment.id)); }}><div><p className="text-sm font-medium">Attempt {attempt.attempt_number} · {attempt.status.replace("_", " ")}</p><p className="text-xs text-muted-foreground">Score {attempt.score_percent ?? "Pending"}% · {attempt.passed === null ? "Pending" : attempt.passed ? "Passed" : "Not passed"}</p></div><label className="text-sm font-medium">Trainer feedback<Input className="mt-2" name="feedback" defaultValue={attempt.trainer_feedback ?? ""} minLength={2} required /></label><Button className="self-end" type="submit" size="sm" disabled={attempt.status !== "submitted"}>Save feedback</Button></form>)}</div></article>)}</div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
