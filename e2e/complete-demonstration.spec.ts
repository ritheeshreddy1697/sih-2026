import { expect, test, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

const API_URL = `${process.env.E2E_API_URL ?? "http://localhost:8000"}/api/v1`;
const DEMO_PASSWORD = process.env.SEED_DEMO_PASSWORD ?? "DemoOnly!2026";

const accounts = {
  ncct: "superadmin@demo.ncct.gov.in",
  institute: "institute.admin@demo.ncct.gov.in",
  trainee: "trainee@demo.ncct.gov.in",
  employer: "recruiter@demo.ncct.gov.in",
};

type JsonRecord = Record<string, unknown>;

async function apiLogin(request: APIRequestContext, email: string) {
  const response = await request.post(`${API_URL}/auth/login`, {
    data: { email, password: DEMO_PASSWORD },
  });
  expect(response.ok(), `API login failed for ${email}: ${await response.text()}`).toBeTruthy();
  return (await response.json() as { access_token: string }).access_token;
}

async function apiCall<T>(
  request: APIRequestContext,
  token: string,
  method: "get" | "post" | "put" | "patch",
  path: string,
  data?: JsonRecord,
) {
  const response = await request[method](`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    ...(data === undefined ? {} : { data }),
  });
  expect(response.ok(), `${method.toUpperCase()} ${path} failed: ${await response.text()}`).toBeTruthy();
  return await response.json() as T;
}

async function signIn(context: BrowserContext, email: string) {
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  return page;
}

function dateInput(daysFromNow: number) {
  const value = new Date();
  value.setDate(value.getDate() + daysFromNow);
  return value.toISOString().slice(0, 10);
}

function localDateTimeInput(daysFromNow: number) {
  const value = new Date();
  value.setDate(value.getDate() + daysFromNow);
  value.setHours(12, 0, 0, 0);
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 16);
}

test("complete NCCT training-to-employment demonstration", async ({ browser, request }) => {
  const runId = Date.now().toString().slice(-9);
  const programmeTitle = `E2E Cooperative Leadership ${runId}`;
  const programmeCode = `E2E-${runId}`;
  const jobTitle = `Cooperative Field Officer ${runId}`;

  const [instituteToken, ncctToken, traineeToken, employerToken] = await Promise.all([
    apiLogin(request, accounts.institute),
    apiLogin(request, accounts.ncct),
    apiLogin(request, accounts.trainee),
    apiLogin(request, accounts.employer),
  ]);

  const instituteContext = await browser.newContext();
  const traineeContext = await browser.newContext();
  const employerContext = await browser.newContext();
  const ncctContext = await browser.newContext();
  const kioskContext = await browser.newContext();

  try {
    // 1. Institute creates a programme through the application UI.
    const institutePage = await signIn(instituteContext, accounts.institute);
    await institutePage.goto("/programmes/new");
    await institutePage.getByLabel("Title").fill(programmeTitle);
    await institutePage.getByLabel("Programme code").fill(programmeCode);
    await institutePage.getByLabel("Language").fill("English");
    await institutePage.getByLabel("Short summary").fill("Practical cooperative leadership for field teams.");
    await institutePage.getByLabel("Full description").fill("A complete demonstration programme covering member service, governance, and field operations.");
    await institutePage.getByLabel("Location").fill("Pune, Maharashtra");
    await institutePage.getByLabel("Capacity").fill("20");
    await institutePage.getByLabel("Duration in days").fill("3");
    await institutePage.getByLabel("Application deadline").fill(localDateTimeInput(2));
    await institutePage.getByLabel("Start date").fill(dateInput(3));
    await institutePage.getByLabel("End date").fill(dateInput(5));
    await institutePage.getByLabel("Eligibility criteria").fill("Open to registered cooperative-sector trainees.");
    await institutePage.getByRole("button", { name: "Save draft" }).click();
    await expect(institutePage).toHaveURL(/\/programmes\/[0-9a-f-]+$/);
    const programmeId = institutePage.url().split("/").at(-1)!;

    const batch = await apiCall<{ id: string }>(request, instituteToken, "post", `/programmes/${programmeId}/batches`, {
      name: "Demonstration batch",
      code: `B-${runId}`,
      capacity: 20,
      start_date: dateInput(3),
      end_date: dateInput(5),
      location: "Pune, Maharashtra",
    });
    await apiCall(request, instituteToken, "post", `/programmes/${programmeId}/submit`);
    await apiCall(request, ncctToken, "post", `/programmes/${programmeId}/approve`);
    await apiCall(request, instituteToken, "post", `/programmes/${programmeId}/publish`);

    // 2. A trainee applies in the UI and the institute approves the application in the UI.
    const traineePage = await signIn(traineeContext, accounts.trainee);
    await traineePage.goto(`/programmes/${programmeId}`);
    await expect(traineePage.getByRole("heading", { name: programmeTitle })).toBeVisible();
    await traineePage.getByLabel(/Why do you want to attend/).fill("I want to strengthen member services in my cooperative.");
    await traineePage.getByRole("button", { name: "Submit application" }).click();
    await expect(traineePage.getByRole("status").filter({ hasText: "application has been submitted" })).toBeVisible();

    await institutePage.goto(`/applications?programme_id=${programmeId}`);
    const applicationCard = institutePage.locator("article").filter({ hasText: programmeTitle });
    await expect(applicationCard).toContainText("Asha Patil");
    await applicationCard.getByRole("button", { name: "Approve" }).click();
    await expect(institutePage.getByRole("status").filter({ hasText: "approved" })).toBeVisible();

    // Supporting LMS content is authored via the same protected production API.
    const course = await apiCall<{ id: string }>(request, instituteToken, "post", "/learning/courses", {
      programme_id: programmeId,
      title: `Cooperative Leadership Essentials ${runId}`,
      summary: "A concise learning path for cooperative field leadership.",
      default_language_code: "en",
    });
    const sectionCourse = await apiCall<{ sections: Array<{ id: string }> }>(request, instituteToken, "post", `/learning/courses/${course.id}/sections`, {
      title: "Leadership foundations",
      position: 1,
    });
    const sectionId = sectionCourse.sections[0].id;
    const moduleCourse = await apiCall<{ sections: Array<{ modules: Array<{ id: string }> }> }>(request, instituteToken, "post", `/learning/sections/${sectionId}/modules`, {
      title: "Member-centred leadership",
      description: "Core principles for accountable cooperative service.",
      position: 1,
    });
    const moduleId = moduleCourse.sections[0].modules[0].id;
    const lessonCourse = await apiCall<{ sections: Array<{ modules: Array<{ lessons: Array<{ id: string }> }> }> }>(request, instituteToken, "post", `/learning/modules/${moduleId}/lessons`, {
      title: "Leading with member trust",
      lesson_type: "text",
      position: 1,
      is_required: true,
    });
    const lessonId = lessonCourse.sections[0].modules[0].lessons[0].id;
    const contentResponse = await request.put(`${API_URL}/learning/lessons/${lessonId}/content`, {
      headers: { Authorization: `Bearer ${instituteToken}` },
      multipart: {
        language_code: "en",
        title: "Leading with member trust",
        text_content: "Transparent decisions and clear communication build durable trust with cooperative members.",
      },
    });
    expect(contentResponse.ok(), await contentResponse.text()).toBeTruthy();
    const bank = await apiCall<{ id: string }>(request, instituteToken, "post", `/learning/courses/${course.id}/question-banks`, {
      title: "Leadership knowledge check",
      description: "Checks the core lesson outcome.",
    });
    await apiCall(request, instituteToken, "post", `/learning/question-banks/${bank.id}/questions`, {
      prompt: "What builds durable trust with cooperative members?",
      choices: ["Transparent decisions", "Hidden records", "Unclear communication"],
      correct_option_index: 0,
      explanation: "Transparency and clear communication support member trust.",
      points: 1,
      position: 1,
    });
    await apiCall(request, instituteToken, "post", `/learning/courses/${course.id}/assessments`, {
      question_bank_id: bank.id,
      title: "Post-training leadership assessment",
      instructions: "Choose the best answer.",
      assessment_type: "post_training",
      attempt_limit: 1,
      passing_score_percent: 60,
      is_published: true,
    });
    await apiCall(request, instituteToken, "patch", `/learning/courses/${course.id}`, { status: "published" });

    // 3. The trainee opens and completes a lesson.
    await traineePage.goto(`/learning/courses/${course.id}`);
    await expect(traineePage.getByRole("heading", { name: "Leading with member trust" })).toBeVisible();
    await expect(traineePage.getByText(/Transparent decisions and clear communication/)).toBeVisible();
    await traineePage.getByRole("button", { name: "Mark complete" }).click();
    await expect(traineePage.getByText("completed", { exact: true })).toBeVisible();

    // 4. The kiosk pairs with a rotating session QR and records the trainee QR attendance.
    const now = Date.now();
    const attendanceSession = await apiCall<{ id: string }>(request, instituteToken, "post", "/attendance/sessions", {
      programme_id: programmeId,
      batch_id: batch.id,
      title: "Leadership workshop attendance",
      starts_at: new Date(now - 60_000).toISOString(),
      ends_at: new Date(now + 10 * 60_000).toISOString(),
    });
    const device = await apiCall<{ device_token: string }>(request, instituteToken, "post", "/attendance/devices", {
      name: `E2E kiosk ${runId}`,
    });
    const sessionQr = await apiCall<{ payload: string }>(request, instituteToken, "get", `/attendance/sessions/${attendanceSession.id}/qr`);
    const traineeIdentity = await apiCall<{ qr_payload: string }>(request, traineeToken, "get", "/attendance/identity/me");

    const kioskPage = await kioskContext.newPage();
    await kioskPage.goto("/kiosk/attendance");
    await kioskPage.getByLabel("Device token").fill(device.device_token);
    await kioskPage.getByRole("button", { name: "Activate device" }).click();
    await expect(kioskPage.getByRole("status").filter({ hasText: "Device activated" })).toBeVisible();
    await kioskPage.getByLabel("QR text fallback").fill(sessionQr.payload);
    await kioskPage.getByRole("button", { name: "Process code" }).click();
    await expect(kioskPage.getByRole("status").filter({ hasText: "Session paired" })).toBeVisible();
    await kioskPage.getByLabel("QR text fallback").fill(traineeIdentity.qr_payload);
    await kioskPage.getByRole("button", { name: "Process code" }).click();
    await expect(kioskPage.getByRole("status").filter({ hasText: "Welcome, Asha Patil" })).toBeVisible();
    await expect(kioskPage.getByText("0 pending")).toBeVisible();

    // 5. The trainee passes the post-training assessment; grading remains server-controlled.
    await traineePage.getByRole("button", { name: "Begin" }).click();
    await traineePage.getByLabel("Transparent decisions").check();
    await traineePage.getByRole("button", { name: "Submit for grading" }).click();
    await expect(traineePage.getByText("Passed", { exact: true })).toBeVisible();
    await expect(
      traineePage.locator("form").filter({ hasText: "Passed" }).getByText("100%", { exact: true }),
    ).toBeVisible();

    await apiCall(request, instituteToken, "patch", `/attendance/sessions/${attendanceSession.id}`, {
      starts_at: new Date(now - 2 * 60_000).toISOString(),
      ends_at: new Date(now - 30_000).toISOString(),
    });

    // 6. The institute administrator configures eligibility and issues the certificate in the UI.
    await institutePage.goto("/certificates");
    await Promise.all([
      institutePage.waitForResponse((response) =>
        response.url().includes(`/api/v1/certificates/programmes/${programmeId}/policy`)
        && response.request().method() === "GET",
      ),
      institutePage.getByLabel("Programme").selectOption(programmeId),
    ]);
    await expect(institutePage.getByLabel("Programme")).toHaveValue(programmeId);
    await institutePage.getByLabel("Certificate title").fill("Certificate of Cooperative Leadership");
    await institutePage.getByLabel("Course completion (%)").fill("100");
    await institutePage.getByLabel("Attendance (%)").fill("100");
    await institutePage.getByLabel("Assessment score (%)").fill("60");
    await institutePage.getByRole("button", { name: "Save policy" }).click();
    await expect(institutePage.getByRole("status").filter({ hasText: "policy saved" })).toBeVisible();
    const candidateCard = institutePage.locator("article").filter({ hasText: "Asha Patil" });
    await expect(candidateCard).toContainText("Eligible");
    await candidateCard.getByRole("button", { name: "Issue certificate" }).click();
    await expect(institutePage.getByRole("status").filter({ hasText: "Certificate issued" })).toBeVisible();

    const certificates = await apiCall<Array<{ verification_url: string; certificate_number: string }>>(
      request,
      instituteToken,
      "get",
      `/certificates?programme_id=${programmeId}`,
    );
    const issuedCertificate = certificates.find((item) => item.verification_url.includes("/verify/certificate/"));
    expect(issuedCertificate).toBeTruthy();
    const verificationToken = issuedCertificate!.verification_url.split("/").at(-1)!;

    // 7. A verified employer verifies the certificate in its recruitment workspace.
    const employerPage = await signIn(employerContext, accounts.employer);
    await employerPage.goto("/employment");
    await employerPage.getByRole("tab", { name: "Verify certificate" }).click();
    await employerPage.getByLabel("Certificate verification token").fill(verificationToken);
    await employerPage.getByRole("button", { name: "Verify" }).click();
    await expect(employerPage.getByText("Asha Patil - Demonstration Trainee")).toBeVisible();
    await expect(employerPage.getByText(issuedCertificate!.certificate_number)).toBeVisible();

    const job = await apiCall<{ id: string }>(request, employerToken, "post", "/employment/employer/jobs", {
      title: jobTitle,
      description: "Support cooperative member services and transparent field operations across the district.",
      location: "Pune, Maharashtra",
      employment_type: "full_time",
      workplace_mode: "on_site",
      required_skills: ["Cooperative leadership"],
      preferred_skills: ["Member communication"],
      minimum_experience_years: 0,
      vacancies: 2,
      salary_minimum: 360000,
      salary_maximum: 480000,
      application_deadline: new Date(Date.now() + 7 * 86_400_000).toISOString(),
      required_programme_ids: [programmeId],
    });
    await apiCall(request, employerToken, "post", `/employment/employer/jobs/${job.id}/publish`);

    // 8. The trainee finds the persisted vacancy and applies through the UI.
    traineePage.once("dialog", (dialog) => dialog.accept("I can apply this verified training in member-facing field work."));
    await traineePage.goto(`/employment?job=${job.id}`);
    const jobCard = traineePage.locator("article").filter({ hasText: jobTitle });
    await expect(jobCard).toBeVisible();
    await jobCard.getByRole("button", { name: "Apply" }).click();
    await expect(traineePage.getByRole("status").filter({ hasText: "Application sent" })).toBeVisible();

    // 9. The employer shortlists the same trainee application.
    await employerPage.reload();
    await employerPage.getByRole("tab", { name: "Applications" }).click();
    const employerApplication = employerPage.locator("article").filter({ hasText: jobTitle });
    await expect(employerApplication).toContainText("Asha Patil");
    await employerApplication.getByLabel(/Update status for Asha Patil/).selectOption("shortlisted");
    await expect(employerPage.getByRole("status").filter({ hasText: "status updated" })).toBeVisible();
    await expect(employerApplication).toContainText("Shortlisted");

    // 10. NCCT views analytics recalculated from the completed persisted workflow.
    const analytics = await apiCall<{ metrics: Array<{ key: string; value: number }> }>(
      request,
      ncctToken,
      "get",
      `/analytics/dashboard?programme_id=${programmeId}`,
    );
    expect(analytics.metrics.find((item) => item.key === "registrations")?.value).toBe(1);
    expect(analytics.metrics.find((item) => item.key === "certificates_issued")?.value).toBe(1);
    expect(analytics.metrics.find((item) => item.key === "job_applications")?.value).toBeGreaterThanOrEqual(1);

    const ncctPage = await signIn(ncctContext, accounts.ncct);
    await ncctPage.goto("/analytics");
    await expect(ncctPage.getByRole("heading", { name: "Programme-wise performance" })).toBeVisible();
    await expect(ncctPage.getByRole("row", { name: new RegExp(programmeTitle) })).toContainText("100%");
  } finally {
    await Promise.all([
      instituteContext.close(),
      traineeContext.close(),
      employerContext.close(),
      ncctContext.close(),
      kioskContext.close(),
    ]);
  }
});
