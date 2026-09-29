# Progress

## 2026-09-27

### Completed

- Inspected the workspace and confirmed it was empty with no project-level `AGENTS.md`.
- Created the initial monorepo scaffold.
- Added frontend React, TypeScript, Vite and Tailwind configuration.
- Added shadcn/ui-style UI primitives and reusable app state components.
- Added responsive application shell for NCCT platform roles.
- Added backend FastAPI app with versioned health endpoints.
- Added SQLAlchemy, Alembic and PostgreSQL configuration foundations.
- Added Vitest and pytest test coverage for the initial shell and health endpoints.
- Added Docker Compose for PostgreSQL, backend and frontend services.
- Added environment-variable examples without real secrets.
- Added setup, architecture and product-requirements documentation.

### Deferred

- Authentication and role-based access control.
- Training program, nomination, attendance, assessment, certification, reporting and employer modules.
- Production deployment configuration.
- Real integrations and data migration.

### Verification

- `npm run lint` passed.
- `npm run typecheck` passed.
- `npm test` passed with 3 frontend tests.
- `npm run build` passed.
- `npm audit --omit=dev` reported 0 production vulnerabilities.
- `ruff check .` passed.
- `mypy app` passed.
- `pytest` passed with 2 backend tests.
- FastAPI started on `127.0.0.1:8000`.
- Vite started on `127.0.0.1:5173`.
- `GET /health` returned `{"status":"ok","service":"NCCT Cooperative Training Platform API"}`.
- `GET /api/v1/health` returned `{"status":"ok","service":"NCCT Cooperative Training Platform API"}`.
- Frontend root returned `HTTP 200`.

### Notes

- `npm install` reported dev-dependency audit findings, but `npm audit --omit=dev` found no production vulnerabilities.
- Backend pytest emitted a Starlette deprecation warning from FastAPI's current `TestClient` import path; tests passed.

## 2026-09-27 - Authentication And Authorization

### Completed

- Added PostgreSQL models and an Alembic migration for users, roles, user-role assignments,
  institutions, user profiles, sessions, consent records, password-reset tokens and audit logs.
- Added Argon2 password hashing and signed JWT access and refresh tokens.
- Added rotating, database-backed refresh sessions stored in an HttpOnly cookie.
- Added login, logout, refresh, current-user and password-reset API flows.
- Added active, suspended and pending-verification account-state enforcement.
- Added role and permission dependencies that enforce authorization in the backend.
- Added authentication audit events for successful, failed and blocked authentication activity.
- Added idempotent development seeds for all six platform roles.
- Added frontend session restoration, scheduled refresh, protected routes and role-gated routes.
- Added responsive sign-in, password-reset, forbidden, workspace and NCCT admin views.
- Upgraded to React Router 7 after the production dependency audit identified advisories in v6.
- Updated the product requirements, architecture, environment examples and setup instructions.

### Verification

- PostgreSQL 16 migration `20260927_01` applied successfully with transactional DDL.
- `alembic current` reported `20260927_01 (head)`.
- `alembic check` reported no new upgrade operations or schema drift.
- Development seed produced 6 roles, 6 users and 4 institutions.
- `ruff check .` passed.
- `mypy app` passed with 24 source files checked.
- `pytest` passed with 10 backend tests.
- `npm run lint` passed without warnings.
- `npm run typecheck` passed.
- `npm test` passed with 5 frontend tests.
- `npm run build` passed.
- `npm audit --omit=dev` reported 0 production vulnerabilities.
- Live development login and refresh requests both returned HTTP 200.
- The frontend login route returned HTTP 200 on `127.0.0.1:5173`.

### Deferred

- Production email delivery for password-reset links.
- External identity providers and multi-factor authentication.
- Training, nomination, attendance, assessment, certification, reporting and employer modules.

### Notes

- Password-reset tokens are returned in API responses only when `ENVIRONMENT=development`.
- The test suite still reports the existing FastAPI/Starlette `TestClient` deprecation warning.
- Docker was unavailable during verification, so migrations ran against a local PostgreSQL 16
  instance using the same repository database configuration.
- Fixed a browser-only sign-in failure caused by invoking an unbound native `fetch` function from
  the API client. The client now resolves the current browser fetch and invokes it with the global
  receiver, with a regression test covering the browser behavior.
- A real Chrome sign-in with the NCCT super administrator account reached the authenticated
  dashboard without network failures or JavaScript exceptions.

## 2026-09-27 - Main Interface And Role Dashboards

### Completed

- Added a responsive public landing page with a locally stored cooperative-training hero image.
- Added public registration for trainees, nominating institutions and employers/recruiters, with
  pending-verification accounts, consent records and registration audit events.
- Added a responsive application shell with desktop sidebar, mobile navigation, skip link, profile
  menu and notification panel.
- Added NCCT, institute administrator, trainer, trainee, nominating-institution and employer
  dashboards with seeded metrics, schedules, activity, notifications and quick actions.
- Added a protected dashboard API that chooses content on the server and filters quick actions by
  backend permissions.
- Changed frontend authorization to consume effective permissions supplied by the backend instead
  of embedding role checks in interface components.
- Added reusable dashboard loading, empty, error and permission-denied behavior.
- Added prepared workspace routes for quick actions without implementing deferred business modules.
- Added component and route tests for public pages, dashboard rendering, navigation focus behavior,
  notification/profile controls and permission denial.

### Verification

- `ruff check .` passed.
- `mypy app` passed with 27 source files checked.
- `pytest` passed with 17 backend tests.
- `npm run lint` passed without warnings.
- `npm run typecheck` passed.
- `npm test` passed with 10 frontend tests.
- `npm run build` passed.
- A real Chrome login with `trainee@demo.ncct.gov.in` reached `/dashboard` and rendered `My learning`.
- Desktop captures at 1440 by 900 and mobile captures at 390 by 844 rendered without horizontal
  overflow on the public landing page and authenticated dashboard.
- Live keyboard focus moved through the skip link, mobile navigation, notifications, profile menu
  and dashboard quick actions; the mobile drawer Escape behavior is covered by a component test.
- FastAPI and Vite responded successfully on `localhost:8000` and `localhost:5173`.

### Deferred

- Training, nomination, attendance, assessment, certification, reporting and employer business
  modules; dashboard quick actions currently open prepared workspace states.
- Production email delivery, external identity providers and multi-factor authentication.

### Notes

- Dashboard content is seeded presentation data returned by the backend and is intentionally not
  persisted as domain records in this phase.
- The test suite retains the existing FastAPI/Starlette `TestClient` deprecation warning.

## 2026-09-27 - Training Programme Management

### Completed

- Added PostgreSQL models and Alembic revision `20260927_02` for programmes, batches, trainer
  assignments, trainee applications, institutional nominations and supporting documents.
- Added draft, pending-approval, approved, rejected, published and archived programme lifecycle
  transitions with backend authorization and audit events.
- Added online, offline and hybrid programme details covering eligibility categories, capacity,
  location, language, duration, dates and application deadlines.
- Added institution-owned batch creation and trainer assignment with programme-capacity and date
  validation.
- Added published programme search and filters, trainee eligibility filtering and NCCT
  cross-institution visibility.
- Added individual trainee applications, duplicate prevention, deadline checks, status tracking
  and authorized PDF/JPEG/PNG document upload and download.
- Added PACS, SHG and cooperative-institution nominations, including atomic UTF-8 CSV imports with
  header, row, email and duplicate validation.
- Added application and nomination review with under-review, approved, rejected and wait-listed
  decisions and shared approval-time capacity enforcement.
- Added responsive programme catalogue, editor, detail, lifecycle, batch/trainer, application,
  nomination, CSV and document interfaces.
- Updated dashboard quick actions and sidebar navigation to open the persisted programme workflow.
- Added a published VAMNICOM demonstration programme and assigned trainer to the idempotent
  development seed.

### Verification

- Alembic revision `20260927_02` applied successfully to local PostgreSQL.
- `alembic current` reported `20260927_02 (head)` and `alembic check` found no schema drift.
- `ruff check .` passed.
- `mypy app` passed with 31 source files checked.
- `pytest` passed with 20 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 13 frontend tests.
- `npm run build` completed successfully.
- Live trainee login and catalogue requests returned HTTP 200 with the seeded programme.
- Live institute-administrator catalogue and detail pages rendered at 1440 by 900 and 390 by 844
  without horizontal overflow.

### Notes

- Supporting file bytes are stored in PostgreSQL for this phase. An object-storage adapter can
  replace this persistence boundary later without changing application ownership rules.
- Bulk CSV uploads support up to 500 rows and 2 MB; supporting documents support up to 5 MB.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-27 - Centralized Profile Management

### Completed

- Added Alembic revision `20260927_03` and PostgreSQL models for the self-referencing institution
  hierarchy, trainee profiles, education, employment, cooperative memberships, validated profile
  documents, programme enrolments, attendance, assessments and certificates.
- Added NCCT, VAMNICOM, RICM, ICM, PACS, SHG, dairy-cooperative and other-cooperative institution
  types while retaining compatibility with existing training, nominating and employer records.
- Added trainee self-service for personal/contact details, preferences, skills, career interests,
  education, employment, memberships, documents and consent preferences.
- Added calculated profile-completion indicators and persisted completion percentages for
  administrator filtering.
- Added institution-scoped administrator search with name/email, institution, state, language,
  skill and completion filters plus server-side pagination.
- Added institution hierarchy creation, editing, search, filtering and pagination with cycle and
  scope validation.
- Added PDF/JPEG/PNG profile-document validation, protected download, approval/rejection decisions
  and validation notes.
- Added consolidated enrolled/completed programme, attendance, assessment and certificate history.
- Added append-only consent records and `profile.*` audit history for trainee changes,
  administrator profile views, private document downloads and validation decisions.
- Added backend privacy enforcement so trainees can resolve only their own profile and institute
  administrators can resolve only trainees in their institution subtree.
- Added responsive trainee self-service, administrator directory/detail and institution hierarchy
  interfaces with loading, empty, error and permission-denied behavior.
- Added idempotent fictional demonstration hierarchy and trainee history. Every seeded profile,
  institution, document, programme and certificate is explicitly labelled as demonstration data.
- Linked newly approved individual programme applications to persisted programme enrolments.

### Verification

- Alembic revision `20260927_03` applied successfully to local PostgreSQL.
- `alembic current` reported `20260927_03 (head)` and `alembic check` found no schema drift.
- The development seed completed and produced a 100% demonstration trainee profile with education,
  employment, membership, a verified document, one active enrolment and one completed programme.
- `ruff check .` passed.
- `mypy app` passed with 35 source files checked.
- `pytest` passed with 23 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 16 frontend tests.
- `npm run build` completed successfully.
- Live trainee login and `GET /api/v1/profiles/me` returned HTTP 200 from PostgreSQL-backed data.
- Headless Chrome rendered the trainee profile and administrator trainee directory at 1440 by 900,
  and the trainee profile and institution hierarchy at a 390-pixel mobile viewport, without
  horizontal overflow or visible error states.

### Notes

- Attendance, assessment and certificate entries are profile-history records in this phase; their
  operational authoring and issuance workflows remain deferred.
- Profile file bytes remain in PostgreSQL behind the same storage boundary as application documents.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-27 - Learning Management And Assessment

### Completed

- Added Alembic revision `20260927_04` and PostgreSQL models for courses, languages, ordered
  sections/modules/lessons, localized lesson assets, progress, assignments/submissions, question
  banks/questions, learner assessments and attempts.
- Connected courses to programmes and reused programme ownership plus batch trainer assignments for
  institute and trainer authorization.
- Added enrolment-gated learning access and protected binary downloads for lesson assets and
  assignment submissions.
- Added text, video, audio, PDF and external-resource lessons with English, Hindi and Telugu sample
  content and extensible language records.
- Added server-owned lesson start, completion and resume state. Media credit is bounded by forward
  playback, client elapsed time and server-observed elapsed time, with 80 percent required.
- Added assignment publishing, validated 10 MB PDF/Word/image submissions, trainer scoring,
  resubmission decisions and feedback.
- Added manager-only question banks and multiple-choice pre-training, practice and post-training
  assessments with hidden correct answers, attempt limits, passing thresholds and automatic grading.
- Rejected client-supplied progress, score and pass fields through narrow request schemas; grading
  and completion are calculated from persisted server state.
- Added responsive course catalogue, resume-aware lesson player, language switching, media/PDF/text
  rendering, assignment submission, assessments and a trainer authoring/review workspace.
- Added an idempotent fictional demonstration course with all five lesson types, three languages,
  seeded resume progress, a reviewed assignment and three assessment stages.
- Updated dashboard quick actions, shared permission navigation, README, product requirements and
  architecture documentation.

### Verification

- Alembic revision `20260927_04` applied transactionally to local PostgreSQL.
- `alembic current` reported `20260927_04 (head)` and `alembic check` found no schema drift.
- The live API accepted the fictional trainee login and returned one seeded course with three
  languages, 33 percent progress and a persisted resume lesson.
- `ruff check app tests` passed.
- `mypy app` passed with 39 source files checked.
- `pytest` passed with 28 backend tests, including enrolment isolation, server-owned progress,
  assessment scoring, tamper rejection, attempt limits and assignment file validation.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 18 frontend tests.
- `npm run build` completed successfully.
- Headless Chrome rendered the authenticated catalogue and course player at 1440 by 900 and 390 by
  844 with no horizontal overflow or visible error state.
- FastAPI and Vite responded successfully on `localhost:8000` and `localhost:5173`.

### Notes

- Learning and assignment file bytes remain in PostgreSQL behind protected service boundaries. An
  object-storage adapter can replace this persistence layer without changing authorization rules.
- Docker is unavailable on this machine; migration, seed and live verification used local
  PostgreSQL 16 and the repository's running FastAPI/Vite services.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-27 - Camera And Offline Attendance

### Completed

- Added Alembic revision `20260927_05` and PostgreSQL models for registered kiosk devices,
  programme/batch attendance sessions, idempotent check-ins and approval-based corrections.
- Added signed, versioned trainee QR identities and signed 45-second session QR tokens that refresh
  every 30 seconds in the trainer interface.
- Added backend permissions for trainee identity, attendance management, correction approval and
  reports, with NCCT, institute and assigned-batch trainer scope enforced in service queries.
- Added kiosk registration with one-time raw tokens, server-side SHA-256 token digests, institution
  binding, last-seen tracking and revocation.
- Added server validation for kiosk status, institution, session state and capture window,
  programme, batch, active trainee account, signed identity and active/completed enrolment.
- Added unique idempotency and session-enrolment constraints, including concurrent-conflict
  recovery, so network replay and repeated scans cannot create duplicate attendance rows.
- Stored client capture time separately from server receipt time, along with kiosk device and
  kiosk/manual source.
- Added reasoned manual-correction requests, requester/approver separation, institute/NCCT review
  and append-only attendance audit events.
- Added per-session reports with expected, present, absent and excused counts, attendance percentage,
  capture/receipt timestamps, device codes and correction actions.
- Added `/kiosk/attendance` with camera decoding through ZXing, USB-reader fallback, large controls,
  full-screen mode and clear success, duplicate, offline and rejection feedback.
- Added an IndexedDB queue that persists before transmission, retries on connectivity restoration,
  removes accepted/duplicate events and retains rejected events with their validation reason.
- Added `/attendance` for trainee identity and permission-driven trainer/administrator session,
  kiosk, report and correction workflows. Camera and QR code libraries are route-lazy-loaded.
- Added an active fictional attendance session to the idempotent development seed.
- Added Raspberry Pi, laptop and Android Chromium setup, HTTPS/camera guidance and an exact-once
  offline demonstration in `hardware/README.md`.

### Verification

- Alembic revision `20260927_05` applied transactionally to local PostgreSQL; `alembic current`
  reported head and `alembic check` reported no schema drift.
- The live fictional kiosk paired to the seeded session. Its first synchronized event returned
  `created`; replaying the identical idempotency key returned `duplicate`, the same check-in ID and
  no second attendance row.
- The frontend IndexedDB test queues while disconnected, synchronizes after reconnect and proves a
  second synchronization pass does not call the API again.
- `ruff check app tests` passed.
- `mypy app` passed with 43 source files checked.
- `pytest` passed with 31 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 22 frontend tests.
- `npm run build` completed successfully with separate lazy attendance and kiosk bundles.
- `npm audit --omit=dev` reported 0 production vulnerabilities.
- Live FastAPI health and Vite kiosk routes returned HTTP 200.
- Headless Chrome rendered the public kiosk and authenticated attendance workspace at 1440 by 900
  and a true 390 by 844 mobile viewport. Both mobile documents measured 390 pixels wide with no
  horizontal overflow or visible error state.

### Notes

- Browser camera access requires HTTPS except on `localhost`. The documented insecure-origin flag
  is for controlled local Raspberry Pi development only and must not be used on public networks.
- Kiosk device tokens and queued attendance stay in that browser's IndexedDB. Access JWTs remain
  memory-only and refresh tokens remain HttpOnly cookies.
- Rejected offline items remain queued with the server's reason for operator review; they are never
  silently discarded.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-28 - Digital Certification And Verification

### Completed

- Added Alembic revision `20260928_06` and PostgreSQL models for programme certificate policies and
  issued digital certificates with eligibility snapshots, PDF bytes, expiry and revocation data.
- Added institute/NCCT certificate-management and trainee wallet permissions without granting
  issuance to trainers.
- Added configurable course-completion, operational-attendance and post-training-score thresholds,
  optional validity periods and active/paused policies.
- Added backend-only eligibility calculation from persisted required lessons, completed attendance
  sessions and submitted post-training attempts. Issuance accepts only an enrolment ID and rejects
  browser-supplied certificate facts.
- Added administrator-controlled issuance with unique random certificate numbers and 256-bit
  URL-safe verification tokens.
- Added backend PDF generation with an embedded QR code pointing to the public verification page.
- Added valid, revoked and expired state calculation, reasoned revocation and append-only
  `certificate.*` policy, issuance and revocation audit events.
- Added a minimal public verification API and responsive page that omit email, internal IDs,
  eligibility scores, verification tokens and revocation reasons.
- Added a private trainee digital skill wallet with authenticated PDF downloads, native sharing,
  copied verification links and clear expired/revoked states.
- Added a responsive certificate administration workspace for policy configuration, live candidate
  metrics, issuance, downloads, revocation and audit history.
- Added an idempotent fictional certificate policy to the development seed; no certificate is
  issued without satisfying the real eligibility rules.
- Added backend and frontend tests covering ineligible issuance rejection, payload tampering,
  role/institution restrictions, PDF generation, wallet access, public minimal disclosure and
  revoked-certificate invalidation.

### Verification

- Alembic revision `20260928_06` applied transactionally to local PostgreSQL; `alembic current`
  reported head and `alembic check` found no schema drift.
- The idempotent development seed completed against the migrated PostgreSQL database.
- `ruff check app tests` passed.
- `mypy app` passed with 47 source files checked.
- `pytest` passed with 34 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 24 frontend tests.
- `npm run build` completed successfully.
- Headless Chrome rendered the public verification route at a true 390 by 844 mobile viewport;
  viewport, document and body widths all measured 390 pixels after correcting the compact header.

### Notes

- The verification token is a random public bearer identifier, not an authentication credential.
  Public responses remain deliberately minimal even when a certificate is invalid.
- Generated PDF bytes are stored in PostgreSQL behind authenticated downloads. The embedded QR
  resolves live state, so a previously downloaded revoked or expired PDF verifies as invalid.
- Docker is unavailable on this machine; migration and seed verification used local PostgreSQL 16.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-28 - Training Operations And Logistics

### Completed

- Added Alembic revision `20260928_07` and PostgreSQL models for venues, classrooms, timetable
  sessions, hostel buildings/rooms/beds, dated bed allocations, participant logistics, material
  inventory/distribution and operations issues.
- Added `operations:manage` for NCCT and institute administrators and `operations:self` for
  trainees. Trainers do not receive general logistics-management access.
- Enforced own-institution administration in backend service queries while retaining explicit
  NCCT cross-institution selection.
- Added transactional trainer, classroom and whole-venue overlap checks for timetable creation and
  editing. Separate classrooms in one venue can run in parallel when trainers differ.
- Added transactional bed and enrolment overlap checks, plus reserved, checked-in, checked-out and
  cancelled accommodation states.
- Added meal and dietary preferences, arrival/departure transport, emergency contacts, programme
  material stock and one-time participant distribution.
- Added maintenance and participant issue reporting with priority, status, mandatory resolution
  notes and `operations.*` audit events.
- Added a consolidated administrator API workspace and a trainee self endpoint that derives all
  data from the authenticated user's enrolments and accepts no trainee identifier.
- Added responsive calendar/list scheduling, venue/classroom forms, hostel and bed controls,
  participant logistics, materials and issue management at `/operations`.
- Added a trainee view for assigned timetable, accommodation, meals, journeys, emergency contact,
  distributed materials and self-service issue reporting.
- Added idempotent, explicitly fictional seed data demonstrating the complete operations flow.
- Added backend tests for institution scope, NCCT access, trainee privacy, timetable conflicts, bed
  conflicts, check-in/out, logistics, materials and issue impersonation prevention.
- Added frontend component tests for the trainee self view and administrator calendar/list and
  hostel navigation.

### Verification

- Alembic revision `20260928_07` applied transactionally to local PostgreSQL and `alembic check`
  found no schema drift.
- The idempotent development seed completed against the migrated database.
- `ruff check app tests alembic/versions/20260928_07_training_operations.py` passed.
- `mypy app` passed with 51 source files checked.
- `pytest` passed with 38 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 26 frontend tests.
- `npm run build` completed successfully.
- Live trainee login and `GET /api/v1/operations/me` returned two enrolments plus the seeded
  timetable, reserved bed, meal preference and material distribution from PostgreSQL.
- Headless Chrome rendered the authenticated trainee operations page at 1440 by 900 and 390 by
  844. The final mobile view used stacked timetable summaries, measured exactly 390 pixels wide
  and had no document overflow or visible error state.

### Notes

- Resource conflict checks use row locks plus interval validation. PostgreSQL remains the intended
  runtime for concurrent booking guarantees; SQLite is used only for isolated endpoint tests.
- The full historical `ruff check .` still reports one pre-existing long line in attendance
  migration `20260927_05`; application code, tests and this phase's migration pass lint.
- Docker is unavailable on this machine; migration and seed verification used local PostgreSQL 16.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-28 - Employment Exchange

### Completed

- Added Alembic revision `20260928_08` and PostgreSQL models for verified employer profiles,
  trainee employment profiles and resumes, certificate-backed skills, job postings, programme
  requirements, saved jobs, candidate shortlists, job applications and attached certificates.
- Extended employer self-registration with company details while retaining pending-verification
  account and institution states. NCCT verification activates approved recruiters and suspends
  rejected registrations.
- Added verified-employer company profile management and employer-owned job creation, editing,
  publishing and closing with backend ownership checks and audit events.
- Added candidate search by valid verified skill, certified course, certificate number and
  location. Revoked and expired certificates are excluded at read time.
- Added candidate shortlisting and allow-listed application stages for shortlist, interview,
  interview completion, offer, hire and rejection.
- Added trainee employment profiles, validated 5 MB PDF/DOC/DOCX resumes, published-job search,
  saving, certificate-gated applications, status tracking and withdrawal.
- Added a deterministic 100-point match breakdown for verified skills (40), required certified
  courses (25), preferred location (20) and career interests (15), with visible reasons and gaps.
- Enforced contact privacy in the backend: placement visibility controls discovery, while contact
  and resume access require data-sharing consent plus an active application to that employer.
- Prevented browser certificate claims by attaching only current valid certificates selected by
  the backend and rechecking every required programme before accepting an application.
- Added the responsive `/employment` workspace for NCCT verification, employer recruitment and
  trainee job discovery, including loading, empty, error states and keyboard-operable tabs.
- Added an explicitly fictional verified employer, trainee employment profile and resume, valid
  digital certificate, verified skills and published demonstration job to the idempotent seed.
- Added backend and frontend tests for registration verification, job permissions and ownership,
  consent masking, resume protection, matching explanations, saving, applying, interview status,
  withdrawal and keyboard navigation.

### Verification

- Alembic revision `20260928_08` applied transactionally to local PostgreSQL and the development
  seed completed successfully.
- `alembic current` reported `20260928_08 (head)` and `alembic check` found no schema drift.
- `ruff check app tests alembic/versions/20260928_08_employment_exchange.py` passed.
- `mypy app` passed.
- `pytest` passed with 42 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 28 frontend tests.
- `npm run build` completed successfully with the employment workspace in a lazy-loaded bundle.
- Live FastAPI health and Vite employment routes returned HTTP 200.
- Live trainee and recruiter logins returned HTTP 200. PostgreSQL-backed workspaces returned one
  100-point explained trainee recommendation with three verified skills and one published job for
  the verified fictional employer.

### Notes

- Resume bytes remain in PostgreSQL behind authenticated, consent-aware service checks. The storage
  boundary can move to object storage without changing employer ownership or privacy rules.
- The local computer-use browser surface was unavailable for this phase; responsive layout and
  keyboard tab behavior were verified through component rendering and the existing responsive app
  shell rather than a new browser screenshot.
- Docker is unavailable on this machine; migration and seed verification used local PostgreSQL 16.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-28 - Multilingual Career Counselling

### Completed

- Added Alembic revision `20260928_09` and PostgreSQL models for approved localized FAQs, per-user
  conversations and messages, message feedback and human-support escalations.
- Added trainee-only `career:counselling` authorization and NCCT-only `career:support` queue access,
  with conversation ownership enforced in backend queries.
- Added deterministic retrieval from approved FAQs, eligible published programmes and live jobs
  from verified employers. Programme and job answers are rendered by backend code from typed rows,
  preventing free-form providers from inventing listings or eligibility rules.
- Kept cooperative entrepreneurship and scheme guidance on approved local FAQ copy so an external
  provider cannot introduce an unapproved scheme or benefit.
- Added exact platform references and routes for every retrieved FAQ, programme and job, including
  focused employment links at `/employment?job=<id>`.
- Added a provider-independent `CareerAIProvider`, Gemini-compatible backend implementation and
  safe local FAQ provider selected automatically when `GEMINI_API_KEY` is empty or provider calls
  fail. No AI credential is exposed through frontend configuration.
- Added English, Hindi and Telugu approved demonstration FAQ content for programmes, employment,
  resumes, interviews, cooperative entrepreneurship and navigation.
- Added persisted recent-history prompts, provider-output link/citation sanitization, explicit
  unavailable responses, 2,000-character validation and per-user database-backed rate limiting.
- Added helpful/not-helpful message feedback, idempotent human-support escalation, support
  resolution endpoints and `career.*` audit events.
- Added the responsive, permission-gated `/career-counsellor` workspace with multilingual controls,
  conversation history, source links, feedback controls, large touch targets and support handoff.
- Added backend tests with a mocked provider covering grounded FAQ, programme and job responses,
  history, feedback, escalation, authorization, validation and HTTP 429 limits. Added frontend
  component tests for the complete conversation flow and language switching.

### Verification

- Alembic revision `20260928_09` applied transactionally to local PostgreSQL and the idempotent
  development seed completed successfully.
- `alembic current` reported `20260928_09 (head)`.
- `ruff check app tests alembic/versions/20260928_09_career_counselling.py` passed.
- `mypy app` passed with 61 source files checked.
- `pytest` passed with 44 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 30 frontend tests.
- `npm run build` completed successfully with a separate lazy career-counsellor bundle.
- Live FastAPI health and Vite `/career-counsellor` requests returned HTTP 200.
- A live Telugu request from the fictional seeded trainee returned the approved Telugu resume FAQ
  through `local-faq` with FAQ source records and no configured Gemini key.

### Notes

- `GEMINI_API_KEY` is intentionally blank in both environment examples. The default `auto` mode
  never calls an external provider without a key.
- Rate limiting is stored against persisted user messages, so changing browser sessions does not
  reset the one-minute allowance.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-28 - Training Analytics

### Completed

- Added backend-owned `analytics:view` authorization for NCCT super administrators and institute
  administrators. Institute requests are restricted to their institution plus descendants, and
  explicit out-of-scope institution filters return HTTP 403.
- Added shared persisted calculations for registrations, approved participants, attendance,
  required-course completion, pre/post assessment improvement, dropouts, digital certificates,
  job applications, interviews and placements.
- Defined the reporting cohort consistently: date filters select programmes by start date, then all
  metrics use enrolments and outcomes connected to those programmes. Every metric definition is
  included in the API response and displayed in the UI.
- Added institution, state, programme, start-date range, gender and participant-category filters.
  Unresolved nominations remain in unfiltered registration totals but cannot satisfy demographic
  filters without a matching trainee profile.
- Added institution-wise, programme-wise and geographic summaries, with the same calculation path
  used for headline values, tables, drill-downs and exports.
- Added paginated detail endpoints for all ten metrics and scoped CSV export for institution,
  programme and geography views. CSV export writes an `analytics.exported` audit event.
- Added the lazy-loaded, permission-gated `/analytics` workspace with large native filter controls,
  focusable metric cards, semantic summary/detail tables, accessible text-labelled bar charts,
  loading/empty/error states and responsive horizontal table scrolling.
- Added explicit demonstration-data indicators from persisted `is_demo` institution and trainee
  flags; no random or frontend-generated production values are used.
- Added backend calculation and authorization tests plus frontend rendering, focus, filter,
  drill-down, chart-label and route-permission tests.
- No database migration was added because analytics is a read projection of existing authoritative
  records; Alembic confirmed the schema remains at revision `20260928_09` with no drift.

### Verification

- `alembic current` reported `20260928_09 (head)` and `alembic check` reported no new upgrade
  operations.
- `ruff check app tests` passed.
- `mypy app` passed with 64 source files checked.
- `pytest` passed with 46 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 32 frontend tests.
- `npm run build` completed successfully with a separate lazy analytics bundle.
- Running FastAPI and Vite services returned HTTP 200 for health and `/analytics`.
- A live institute-admin request returned only the VAMNICOM demonstration hierarchy, ten metrics,
  one institution summary, two programme summaries and an explicit seeded-data flag.
- Headless Chrome rendered the authenticated dashboard at 1440 by 900 and 390 by 844. The mobile
  document measured exactly 390 pixels wide, visible controls were at least 44 pixels high, all
  three charts had accessible labels and neither viewport showed an analytics error or horizontal
  page overflow.

### Notes

- Assessment improvement uses only enrolments with at least one submitted pre-training and one
  submitted post-training attempt, selecting the best score of each type before averaging the
  difference.
- Certificate issuance counts all issued records, including certificates later revoked or expired;
  this is an issuance-volume metric rather than current certificate validity.
- The existing FastAPI/Starlette `TestClient` deprecation warning remains; all tests pass.

## 2026-09-28 - Progressive Web App, Offline Learning and Accessibility

### Completed

- Added an installable PWA manifest, 192px and 512px install icons, theme metadata and a
  production service worker with a versioned offline application shell.
- Kept private data out of Cache Storage: the service worker bypasses every `/api/` request,
  authorized request and non-GET request. Only the public shell and static build assets are cached.
- Added explicit per-lesson offline downloads backed by user-keyed IndexedDB records. Offline
  packages contain only downloaded course lessons and their platform-hosted file blobs; signing out
  removes the private offline-learning database.
- Added an offline learning catalogue fallback and course-player fallback so downloaded lessons can
  be reopened while the current authenticated app session is offline.
- Added an IndexedDB progress queue for start, heartbeat and completion events, automatic reconnect
  synchronization, visible pending counts and retained server rejection details.
- Added Alembic revision `20260928_10` and PostgreSQL-backed progress-event idempotency. The batch
  sync endpoint orders captured events, rejects key reuse, prevents position regression, bounds
  credited media time and returns stable applied, duplicate or rejected results.
- Added online/offline status, manual synchronization, install/update actions and reduced-data mode
  to the responsive application shell. Reduced-data mode suppresses the landing image and prevents
  media/PDF loading until the user requests it.
- Added an extensible typed language registry and interface translations for English, Hindi and
  Telugu, with language controls on public, authentication and signed-in surfaces.
- Added global high-visibility focus outlines, semantic mobile navigation, labelled controls,
  accessible login error associations, native form validation and at least 44px visible mobile
  touch targets in the tested public and sign-in flows.
- Split business routes into lazy chunks, reducing the initial production JavaScript bundle from
  about 521 kB to 271 kB before compression; large camera dependencies remain isolated to the kiosk
  route.
- Added frontend tests for private offline-data isolation, exact-once queue removal, rejected-event
  retention, manifest/service-worker privacy rules, localization and keyboard-accessible app
  preferences. Added backend tests for ordered, monotonic, idempotent synchronization and enrolment
  enforcement.

### Verification

- Alembic revision `20260928_10` applied transactionally to local PostgreSQL. `alembic current`
  reported `20260928_10 (head)` and `alembic check` reported no new upgrade operations.
- `ruff check app tests alembic/versions/20260928_10_pwa_offline_progress.py` passed.
- `mypy app` passed with 64 source files checked.
- `pytest` passed with 48 backend tests.
- `npm run lint` and `npm run typecheck` passed.
- `npm test` passed with 39 frontend tests.
- `npm run build` completed with a 270.68 kB initial JavaScript bundle and lazy business-module
  chunks.
- The running FastAPI health endpoint, production manifest and service worker returned successfully.
- Headless Chrome at an exact 390 by 844 emulated viewport reported a 390px document and scroll
  width, active service-worker control, a valid manifest link, 44px visible touch targets and a 3px
  keyboard focus outline. English labels and autocomplete metadata were verified on the sign-in
  form, and Hindi plus reduced-data rendering were exercised.
- The production server was stopped after an online load; Chrome then reloaded `/login` from the
  service worker with the complete application shell, proving offline-shell operation.
- The reconnect test queued one progress event while no sync ran, synchronized it once after the
  simulated connection returned and confirmed a second sync made no request. Backend retry tests
  also confirmed viewed time remained unchanged when all event keys were replayed.

### Notes

- A fresh offline launch does not restore a signed-in identity from persistent browser storage.
  This intentionally prevents a later user of a shared device from opening another trainee's
  private downloads. Downloaded lessons remain usable while the authenticated app session stays
  open; sign-out erases them.
- External-resource URLs are not copied into private offline storage. Text lessons and files served
  by the authorized lesson-asset endpoint can be downloaded explicitly.
- Service-worker registration is production-only to avoid stale assets during Vite development.
- The existing FastAPI/Starlette `TestClient` deprecation warning and Node test-runner localStorage
  warning remain; all tests pass.

## 2026-09-28 - Security Hardening, Integration And Deployment Preparation

### Completed

- Added production fail-closed configuration for JWT/database secrets, Secure refresh cookies,
  disabled API docs, explicit HTTPS CORS origins, trusted hosts and HTTPS public URLs. PostgreSQL,
  JWT and optional Gemini values support file-mounted secrets.
- Added request IDs, bounded declared request sizes, authentication/API rate limiting, JSON
  `no-store`, security headers and generic request-validation/500 responses that do not reflect
  submitted passwords or internal exception details.
- Hardened authentication with required JWT claims, a restricted algorithm allow-list, generic
  inactive/invalid login responses, hashed unknown login identifiers, reset-wide session/token
  revocation and stronger password validation. Backend authorization denials now append audit data.
- Centralized upload validation with safe filenames, byte limits, MIME allow-lists, actual file
  signatures and bounded DOCX archive inspection. Applied it to profile/programme documents,
  learning assets/submissions and employment resumes; hardened CSV uploads and CSV exports.
- Added Alembic revision `20260928_11`, persisted account-deletion requests, password-confirmed
  request/cancel APIs, NCCT review/completion APIs, cooling periods, session revocation, private-data
  erasure, identity pseudonymization and retained de-identified statutory/audit evidence.
- Added trainee deletion controls and explicit kiosk privacy copy confirming QR scanning performs no
  biometric identification and stores/uploads no camera frames.
- Added production backend/frontend multi-stage images, non-root/read-only containers, one-shot
  migrations, private service networking, file secrets, same-origin Nginx proxying, edge rate
  limits, CSP/HSTS and immutable static-asset caching. Production binds to loopback by default and
  has an opt-in Gemini secret override.
- Added a serial Playwright demonstration with isolated institute, trainee, employer, NCCT and kiosk
  browser contexts. It completes programme creation, application approval, lesson completion, QR
  attendance, assessment grading, certificate issuance/verification, job application/shortlist and
  analytics verification using persisted records.
- Fixed integration defects exposed by Playwright: concurrent PWA progress synchronization, missing
  kiosk-token CORS preflight support, stale certificate programme requests and the analytics
  programme filter's explicit label association.
- Added production environment documentation, security/privacy controls, backup/restore guidance,
  rollback and health-check procedures, a repeatable seed command and final deployment instructions.

### Verification

- `ruff check app tests alembic` passed, including every migration.
- `mypy app` passed with 67 source files checked.
- `pytest -q` passed with 55 backend tests; the known FastAPI/Starlette TestClient deprecation
  warning remains.
- Alembic applied `20260928_11` transactionally to PostgreSQL. `alembic current` reported
  `20260928_11 (head)` and `alembic check` reported no schema drift.
- The development seed completed successfully twice, confirming repeatable baseline seeding.
- `npm run lint`, `npm run typecheck`, all 39 Vitest tests and `npm run build` passed.
- The complete real-Chrome Playwright scenario passed: 1 test in 10.5 seconds.
- `npm audit --audit-level=moderate` reported 0 vulnerabilities. `pip-audit --local` reported no
  known vulnerabilities, and `pip check` reported no broken requirements.
- The backend production wheel built successfully. All three Compose YAML files parsed successfully.
- The final native runtime check returned `200 OK` from `http://localhost:5173`, reported the API
  ready at `http://127.0.0.1:8000/api/v1/health/ready` and authenticated the seeded trainee through
  the live login endpoint with HTTP 200.
- Docker is not installed on this workstation, so production container image build/start and
  `docker compose config` could not be executed here; native production-equivalent builds and live
  PostgreSQL integration were verified instead.

### Remaining Before Real-Data Production

- Add production email delivery, multi-factor authentication or approved identity federation and a
  breached-password control.
- Add malware scanning/content disarm, encrypted object storage and lifecycle/quarantine policies
  for user uploads.
- Move abuse limits to a shared gateway/Redis for multi-host scale and add centralized monitoring,
  alerting and immutable audit export.
- Add an account-deletion operations queue/scheduled worker and finalize the legally approved NCCT
  retention schedule.
- Provision provider-specific CI/CD, managed PostgreSQL high availability/PITR, external secret
  management and verified Docker image/SBOM/signing workflows.
- Complete independent penetration testing, accessibility conformance testing, privacy impact/legal
  review and a documented disaster-recovery exercise before processing real personal data.

## 2026-09-28 - Optional Consent-Based Face Verification

### Completed

- Added Alembic revision `20260928_12` and PostgreSQL models for encrypted biometric templates,
  single-use enrolment/attendance challenges and persisted verification/manual-review outcomes. No
  database column stores a face image or video.
- Added a replaceable `FaceVerificationProvider` protocol and a clearly labelled local demonstration
  provider. The demo derives a coarse visual template, requires movement across a three-frame
  head-turn challenge and is explicitly blocked from production enablement.
- Added AES-256-GCM template protection with a separate backend-only secret, random nonce, key
  version and trainee/provider/model-bound associated data. Embeddings and ciphertext are never
  exposed through an API, response or audit event.
- Added explicit versioned biometric consent, authenticated webcam enrolment, server-owned liveness
  and confidence calculations, configurable automatic/manual thresholds and physical template
  deletion by the trainee or an institution-scoped/NCCT administrator.
- Added strict one-to-one kiosk verification. A registered kiosk must be paired to an active session
  and an enrolled trainee must claim an exact identity code before any frames are accepted. There is
  no unknown-person or roster-wide face search.
- Added high-confidence biometric check-ins, low-confidence rejection and an uncertainty band that
  creates no attendance until a separate institute/NCCT administrator completes an in-person
  review. Automatic and manually reviewed sources remain distinguishable in reports.
- Added biometric consent, enrolment, challenge, rejection, verification, manual-review and deletion
  audit events, sensitive-path throttling, three-file/image-signature/size checks and short-lived
  challenge replay protection.
- Added responsive trainee enrolment/deletion controls, kiosk face controls with large targets and
  clear outcomes, administrator review/deletion controls and unchanged QR camera/text/offline
  fallback paths.
- Updated the product requirements, architecture, security, deployment, environment, root README
  and Raspberry Pi/laptop instructions with limitations, retention, backup and privacy safeguards.

### Verification

- Alembic applied `20260928_12` transactionally to PostgreSQL; `alembic current` reports
  `20260928_12 (head)` and `alembic check` reports no model/schema drift.
- `ruff check app tests alembic` passed and strict `mypy app` passed for 70 source files.
- All 61 backend tests passed. New coverage proves static-frame spoof rejection, explicit consent,
  encrypted storage, high-confidence success, exact-once replay, low-confidence rejection,
  uncertain-match manual review, unknown-person rejection, role restrictions and both deletion
  paths.
- `npm run lint`, `npm run typecheck`, all 41 Vitest tests and the Vite production build passed.
  Frontend tests cover retained QR fallback, claimed-identity face flow and denied webcam permission.
- The original ten-step real-Chrome Playwright demonstration passed in 10.7 seconds, confirming the
  established QR attendance and cross-module workflow did not regress.
- The development seed remained repeatable, all Compose YAML parsed, the backend wheel built,
  `pip check` found no broken requirements and `pip-audit --local` found no known vulnerabilities.

### Limitations And Production Gate

- Face verification is online-only. QR attendance remains the privacy-preserving and offline-capable
  fallback for every trainee.
- The demo provider is not certified face recognition or presentation-attack detection. A moving
  photograph or replayed video may satisfy its motion check; demographic accuracy and fairness are
  not established. It must never be used for real attendance decisions.
- Production keeps `BIOMETRIC_ENABLED=false` with the demo provider. Real enablement requires a
  reviewed provider adapter, lawful-basis/privacy impact assessment, demographic and spoof testing,
  accessibility alternative, approved retention/deletion and backup-reconciliation procedures,
  incident response, managed keys and an independent security review.
