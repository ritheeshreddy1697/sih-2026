# Architecture

## Repository Layout

```text
.
├── backend
│   ├── alembic
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── models
│   │   └── schemas
│   └── tests
├── docs
└── frontend
    └── src
        ├── auth
        ├── components
        ├── lib
        ├── pages
        └── test
```

## Frontend

The frontend is a React, TypeScript and Vite application. Tailwind CSS provides styling, with shadcn/ui-style primitives kept in `src/components/ui` so the design system can grow without binding early business modules to low-level styling details.

Current boundaries:

- `components/layout` contains application frame components.
- `components/states` contains reusable loading, empty and error states.
- `components/ui` contains low-level reusable interface primitives.
- `auth` contains session state and route-authorization boundaries.
- `pages` contains public, account, dashboard and protected workspace views.
- `lib/api` contains backend client code.
- `lib/navigation.ts` declares permission requirements for shared navigation destinations.

Access JWTs are kept in memory. The frontend restores and rotates sessions with an HttpOnly
refresh-token cookie, avoiding persistent browser storage for bearer tokens. The API returns the
authenticated user's effective permissions, which drive route and navigation visibility through the
shared authorization provider. Frontend route guards improve navigation but are not treated as a
security boundary.

## Backend

The backend is a FastAPI service with versioned API routing under `/api/v1`. SQLAlchemy and Alembic
provide PostgreSQL-backed identity, programme-management, institution-hierarchy and trainee-profile
persistence. Learning, assessments, operational attendance, digital certificate issuance,
employment exchange, career counselling and cross-module analytics are implemented.

Current boundaries:

- `app/api` contains routers and HTTP endpoints.
- `app/core` contains environment-driven settings.
- `app/db` contains database engine/session setup.
- `app/models` contains SQLAlchemy model foundations.
- `app/schemas` contains Pydantic response schemas.
- `app/services` contains authentication, programme, profile, learning, attendance, certificate,
  operations, employment, career-counselling and analytics orchestration, scoping rules and audit
  helpers.

## Authentication And Authorization

- Argon2 is used for password hashing.
- Signed access and refresh JWTs include issuer, audience, token type, session ID and unique token ID.
- Refresh tokens rotate and only a SHA-256 digest is stored in `sessions`.
- Every protected request validates both the JWT and its database session.
- Static role-to-permission mappings are enforced by FastAPI dependencies.
- Login, refresh, logout and password-reset events are written to `audit_logs`.
- Password-reset tokens are random, single-use, short-lived and stored only as hashes.

The initial migration creates `users`, `roles`, `user_roles`, `institutions`, `user_profiles`,
`sessions`, `consent_records`, `password_reset_tokens` and `audit_logs`.

The programme migration creates `programmes`, `programme_batches`,
`batch_trainer_assignments`, `programme_applications`, `programme_nominations` and
`application_documents`.

The profile migration extends `institutions` with self-referencing hierarchy and profile fields,
then creates `trainee_profiles`, education, employment, cooperative membership, trainee document,
programme enrolment, attendance, assessment and certificate tables.

The learning migration creates `courses`, course languages, ordered sections/modules/lessons,
localized lesson content, lesson progress, assignments/submissions, question banks/questions,
learner assessments and assessment attempts.

The attendance migration adds signed trainee-identity versions, registered kiosk devices,
programme/batch attendance sessions, idempotent check-ins and separately reviewed corrections.

The digital-certificate migration adds programme-scoped certificate policies and issued
certificates with immutable eligibility snapshots, PDF bytes, expiry/revocation state and indexed
unguessable verification tokens.

The career-counselling migration adds approved localized FAQs, per-user conversations and messages,
message feedback and human-support escalations.

## Programme Management

- Programme states follow `draft -> pending_approval -> approved -> published -> archived`, with
  rejection returning a record to the owning institute for revision and resubmission.
- Institute ownership is checked for every management and review operation. NCCT approval
  permission provides cross-institution visibility and lifecycle review.
- Published-catalogue queries filter trainee results by individual eligibility and filter
  nominating institutions by supported nomination categories.
- Application and nomination approvals share programme capacity. Capacity is checked inside the
  review transaction, while duplicate applications and candidate emails are rejected.
- CSV nominations are parsed with structured headers, validated completely and inserted only when
  every row succeeds.
- PDF, JPEG and PNG documents up to 5 MB are stored with their metadata and binary content in
  PostgreSQL. Downloads repeat ownership or reviewer authorization checks.
- Domain actions append records to the shared `audit_logs` table.

## Dashboard Delivery

- `GET /api/v1/dashboard` requires an authenticated, active session.
- The backend selects role-relevant seeded dashboard content and removes quick actions that the
  caller is not permitted to use.
- The frontend renders a shared dashboard contract and does not branch on role names.
- Sidebar links declare permissions and are filtered through the same effective-permission set.
- Workspace routes remain placeholders until their business modules are implemented.
- The public landing page uses a locally stored generated bitmap under `frontend/public/images`.

## Profile Management

- `GET` and `PATCH /api/v1/profiles/me` always resolve the authenticated trainee; callers cannot
  supply a user identifier for self-service operations.
- Administrative trainee queries require `profiles:view_private` and constrain institute
  administrators to their institution plus descendants. NCCT platform administrators retain
  national visibility.
- Institution hierarchy writes validate parent existence, administrative scope and cycles.
- Profile completion is calculated from persisted profile sections and stored for indexed
  administrator filtering.
- PDF, JPEG and PNG trainee documents are limited to 5 MB, start in a pending state and require a
  separate document-validation permission for approval or rejection.
- Consent changes append historical `consent_records`; profile updates, administrative views,
  document downloads and validation decisions append `profile.*` audit events.
- The frontend exposes trainee self-service, an administrator trainee directory and institution
  hierarchy views through permission-gated routes. Backend checks remain the security boundary.

## Learning Management And Assessment

- A course belongs to one programme. Manager scope is inherited from the programme: NCCT has
  cross-institution access, institute administrators are restricted to their institution and
  trainers are restricted to programmes with an explicit batch assignment.
- Trainee reads and writes resolve the authenticated user's active or completed programme
  enrolment. Client-supplied enrolment identifiers are never accepted for progress, submissions or
  assessment attempts.
- Lesson content is localized by an extensible language code. Binary PDF/audio/video assets and
  assignment files are returned only after repeating course ownership or enrolment checks.
- Text, PDF and external lessons use explicit completion. Media progress is credited by the minimum
  of forward playback movement, reported elapsed time and server-observed elapsed time; 80 percent
  is required for completion.
- Resume state is derived from server-stored lesson progress. The frontend can report playback
  position but cannot submit completion state or viewed totals.
- Question-bank answers remain manager-only. Trainee attempts contain prompts and choices, while
  answer submissions reject extra score/pass fields and are graded from persisted correct answers.
- Attempt limits, passing thresholds, assignment maximum scores and trainer review scope are all
  enforced in the service layer and recorded through `learning.*` audit events.
- The responsive frontend exposes `/learning`, a course player and a permission-gated trainer
  authoring/review workspace. Route guards improve navigation only; backend checks remain decisive.

## Attendance And Kiosk Synchronization

- An attendance session belongs to one programme and one batch. NCCT can manage all sessions,
  institute administrators are constrained to their institution and trainers require an explicit
  assignment to the selected batch.
- Trainee QR identities are deterministic signed tokens tied to the authenticated trainee and a
  persisted identity version. Session QR tokens are signed, expire after 45 seconds and are used
  only to pair an already registered kiosk.
- Raw kiosk tokens are shown once, kept in kiosk IndexedDB and stored on the server only as SHA-256
  digests. Revocation is enforced on every pairing and synchronization request.
- The kiosk persists a scan before network transmission. Queue records contain a UUID idempotency
  key, paired session, signed trainee identity and client capture timestamp. The browser retries on
  the `online` event and removes only accepted or duplicate records.
- The backend independently validates institution, active session window, programme, batch,
  enrolment, account state and trainee identity. A unique idempotency key makes network replay
  deterministic, while a separate session-enrolment constraint prevents a second attendance row
  from a different scan.
- Offline captures may synchronize after a session ends only when their capture timestamps fall in
  the configured session window plus the short closing grace period. Server receipt time remains
  separate from client capture time.
- Manual corrections never rewrite audit history directly. Trainers submit a reasoned request;
  institute or NCCT administrators approve or reject it, and requesters cannot approve their own
  change.
- `/attendance` exposes trainee identity, session/device management, rotating codes, corrections
  and reports. `/kiosk/attendance` is a device-authenticated, full-screen camera surface that does
  not rely on a user access token.
- Optional face verification is a separate online path. A trainee first grants versioned consent
  and completes a single-use head-turn challenge. The provider returns an embedding and liveness
  score; camera frames are released after the request and are not represented in the database.
- `biometric_enrollments` stores only AES-GCM ciphertext, nonce, key version and provider/model
  metadata. The associated-data binding includes trainee, provider, model and key version, so a
  ciphertext cannot be silently moved to another identity or model.
- A kiosk must present an active device token, active session and exact trainee identity code before
  it can obtain a verification challenge. The provider compares the capture only with that claimed
  trainee's decrypted template. There is no endpoint for one-to-many image search.
- `biometric_challenges` are short-lived and single-use. `biometric_verifications` persist only
  confidence, liveness, threshold, outcome, review and check-in references; they contain no image
  or embedding. High-confidence results create idempotent `biometric` check-ins. Scores in the
  uncertainty band create no attendance until an institute/NCCT administrator records an in-person
  review; approved reviews use the `biometric_manual` source.
- `FaceVerificationProvider` isolates capture analysis and matching. The included local provider is
  explicitly demonstration-only and production configuration rejects enabling it. QR attendance
  remains available and retains its existing offline queue.

## Digital Certification

- A certificate policy belongs to one programme and defines minimum required lesson completion,
  operational attendance and best submitted post-training assessment score. A zero threshold can
  deliberately disable a criterion; policies may be paused and may set a validity period.
- The issuance request accepts only an enrolment ID. The service reloads the programme, trainee,
  required lessons, completed attendance sessions and graded post-training attempts from
  PostgreSQL, then recalculates eligibility inside the backend.
- Only NCCT or an institute administrator for the programme's owning institution can configure a
  policy, inspect candidates, issue or revoke. Trainers and trainees cannot issue certificates.
- Issuance creates a random certificate number and a `secrets.token_urlsafe(32)` public
  verification token. The backend renders the PDF with ReportLab and embeds a QR code containing
  the configured public frontend verification URL.
- Certificate state is derived on every read: revocation takes precedence, followed by expiry,
  otherwise valid. Revocation requires a reason and appends a `certificate.revoked` audit event.
- Public verification is unauthenticated but returns only minimal display fields. It never exposes
  email, internal IDs, eligibility scores, the verification token or revocation reason.
- `/certificates` is permission-driven: trainees receive their private skill wallet, while NCCT and
  institute administrators receive policy and issuance controls. `/verify/certificate/:token` is
  the public verification surface.

## Training Operations And Logistics

- Venues, classrooms, timetable sessions, hostel buildings, rooms, beds, allocations, participant
  logistics, training materials, distributions and issues form a separate operations domain tied
  to existing institutions, programmes, batches and enrolments.
- Every administrator read and mutation resolves an owning institution on the server. Institute
  administrators must match that institution; NCCT platform administrators may select any active
  institution.
- Timetable creation locks the trainer, venue and optional classroom before testing interval
  overlap. A whole-venue booking conflicts with every classroom in that venue; separate classrooms
  may host parallel sessions when trainers differ.
- Bed allocation locks both bed and enrolment before testing inclusive date overlap. This prevents
  concurrent requests from assigning one bed twice or assigning one trainee to two beds.
- Trainee operations are assembled only from enrolments whose `trainee_id` matches the authenticated
  user. The self endpoint accepts no user ID and excludes cancelled timetable and bed records.
- Participant logistics belong one-to-one with an enrolment. Material distributions require the
  same programme, enforce stock and permit one distribution record per material and enrolment.
- Trainees may report participant issues only against their own enrolment. Institute and NCCT
  administrators manage issue status and must provide resolution notes before resolving or closing.
- Mutations append `operations.*` records to the shared audit log. Frontend permission checks shape
  navigation only; backend ownership and resource checks remain authoritative.

## Employment Exchange

- Employer registration reuses pending user and institution records and creates a one-to-one
  employer profile. NCCT verification activates or suspends both the account and institution.
- Jobs belong to the verified employer profile. Every edit, lifecycle transition, candidate query
  and application update resolves that ownership in the backend.
- Verified employment skills link a trainee, a digital certificate and a skill name. Search and
  matching discard links whose certificate is revoked or expired.
- Job applications link certificates selected by the backend at submission time. Required course
  eligibility is recalculated from valid digital certificates before the row is created.
- Candidate discovery requires placement visibility, open-to-work status, an active account and at
  least one valid certificate. Contact and resume access additionally require data-sharing consent
  plus a non-withdrawn application to the requesting employer.
- Recommendations are deterministic and explainable: skills contribute 40 points, required courses
  25, location 20 and career interests 15. Responses include component scores, reasons and gaps.
- Application transitions are allow-listed from applied through shortlist, interview, offer and
  hire/rejection. Trainees may withdraw only before a terminal outcome.
- Employment mutations append `employment.*` events to the shared audit log. Frontend permissions
  shape the workspace, while API dependencies and ownership checks remain authoritative.

## Multilingual Career Counselling

- `/api/v1/career` is authenticated and trainee-only for conversations, messages, feedback and
  support escalation. Conversation ownership is checked for every message-level operation.
- Retrieval is server-owned. Programme answers use only eligible, published, open-capacity records;
  job answers use only live jobs from verified employers and include the existing deterministic
  skill/course/location/interest match explanation. Approved FAQs are filtered by language.
- Programme and job answers are rendered from typed database sources instead of free-form model
  output. This prevents an AI provider from presenting invented listings or eligibility rules as
  platform facts.
- `CareerAIProvider` is the provider boundary. `GeminiCompatibleProvider` is configured only in the
  backend through environment variables; when no key exists or the provider fails, `LocalFaqProvider`
  returns approved English, Hindi or Telugu guidance.
- Provider prompts receive only retrieved sources and recent conversation turns. External links and
  unknown source citations are removed from provider output; platform source metadata is attached
  independently by the backend.
- Messages, selected source records, feedback and support status are persisted in PostgreSQL.
  Per-user database-backed rate limiting survives process restarts and returns HTTP 429 with a retry
  interval.
- The frontend route `/career-counsellor` uses the effective `career:counselling` permission,
  supports keyboard-operable language and feedback controls, and links references to actual
  programme and employment records. Frontend guards remain a navigation aid, not a security boundary.

## Analytics

- `/api/v1/analytics` requires the `analytics:view` permission. NCCT super administrators receive
  national scope; institute administrators receive their institution plus descendants through the
  existing hierarchy scope function. User-supplied institution filters are checked against that
  scope before programme data is queried.
- Analytics is calculated on request from authoritative programme applications, nominations,
  enrolments, attendance sessions/check-ins, published-course lesson progress, submitted pre/post
  attempts, digital certificates and employment applications. There is no mutable reporting table
  or browser-supplied aggregate to become stale.
- Date filters select programmes by `Programme.start_date`; all counts and outcomes then describe
  the same programme cohort. Demographic filters use the trainee profile. Nominations that cannot
  resolve to a trainee remain in unfiltered registration counts and are excluded when a demographic
  filter is active.
- Registration counts combine individual applications and institutional nominations. Attendance
  is present check-ins divided by expected enrolment/session pairs. Course completion requires every
  required lesson in a published course. Assessment improvement averages each enrolment's best
  post-training score minus its best pre-training score. Dropout is withdrawn enrolments divided by
  enrolments. Employment outcomes are distinct job applications from trainees in the cohort.
- One service calculation path supplies headline metrics, institution/programme performance,
  geography, metric drill-downs and CSV export. This keeps the displayed figure, detail rows and
  downloaded summaries aligned. CSV exports append `analytics.exported` audit records.
- `/analytics` is a lazy-loaded, permission-gated React route with native filter controls,
  focusable metric cards, semantic tables, text-labelled CSS bar charts and horizontally scrollable
  wide tables for narrow viewports. Seed participation is reported by the API and labelled in the UI.

## Local Infrastructure

Docker Compose defines PostgreSQL, backend and frontend services. The database service includes a health check; application services use local bind mounts for fast iteration.

## Security And Production Topology

- `RequestSecurityMiddleware` assigns or validates a request ID, rejects oversized declared bodies,
  rate-limits authentication and API paths, prevents JSON caching and adds API security headers.
  Production Nginx repeats edge rate limits and enforces the maximum request body before parsing.
- Production settings fail closed for placeholder JWT/database values, insecure refresh cookies,
  enabled API docs, wildcard hosts/CORS, non-PostgreSQL storage and non-HTTPS public origins.
- CORS uses an explicit method/header allow-list, including the kiosk-only `X-Kiosk-Token`.
  Browser refresh credentials remain Secure, HttpOnly and SameSite=Lax.
- Shared upload validation checks endpoint allow-lists, byte limits, normalized filenames, file
  signatures and bounded DOCX structure before persistence.
- Account deletion is an auditable state machine with password confirmation, cooling period,
  cancellation and NCCT completion. Completion pseudonymizes retained evidence and erases private
  profile, consent, upload, resume, conversation and session data.
- The production Compose topology exposes only Nginx on loopback by default. Alembic completes in a
  one-shot service before the non-root read-only FastAPI service starts; PostgreSQL and backend stay
  on the Docker network. Secrets are read from mounted files.
- See `docs/security.md` for the control inventory and residual risks, and `docs/deployment.md` for
  deployment, backup and recovery operations.

## End-To-End Integration

- Root Playwright configuration launches migrated/seeded FastAPI and Vite services and uses an
  installed Chrome channel with isolated contexts for institute, trainee, employer, NCCT and kiosk
  actors.
- The serial demonstration carries one persisted programme through institute creation, trainee
  application/approval, lesson completion, rotating-QR attendance, server grading, certificate
  issuance/verification, job application/shortlisting and recalculated analytics.
- Supporting authoring records are created through protected APIs; each role-defining action is
  exercised through its actual browser interface. Unique programme/job codes make repeated runs
  safe against duplicate constraints.

## API Versioning

Health endpoints are available at:

- `/health`
- `/api/v1/health`

Future modules should be added under `/api/v1/<module>` and grouped by domain.

Authentication endpoints are grouped under `/api/v1/auth`.
The role dashboard endpoint is available at `/api/v1/dashboard`.
Programme, batch, application, nomination and document endpoints are grouped under
`/api/v1/programmes`.
Trainee profile, institution hierarchy and profile-document endpoints are grouped under
`/api/v1/profiles`.
Course, lesson, progress, assignment and assessment endpoints are grouped under
`/api/v1/learning`.
Attendance session, identity, kiosk, synchronization, correction, biometric enrolment/verification
and report endpoints are grouped under `/api/v1/attendance`.
Certificate policy, candidate, issuance, wallet, download, revocation and public verification
endpoints are grouped under `/api/v1/certificates`.
Timetable, venue, hostel, participant-logistics, material and issue endpoints are grouped under
`/api/v1/operations`.
Employer verification, jobs, candidate search, applications and trainee employment-profile
endpoints are grouped under `/api/v1/employment`.
Career conversations, grounded messages, feedback and human-support escalation are grouped under
`/api/v1/career`.
Analytics options, dashboard projections, metric drill-downs and CSV export are grouped under
`/api/v1/analytics`.

## Testing Strategy

- Frontend component and client behavior uses Vitest with React Testing Library.
- Backend endpoint behavior uses pytest with FastAPI TestClient.
- Type-checking and linting are required before feature work is considered complete.
- Responsive checks use desktop and 390-pixel browser captures, including horizontal-overflow
  assertions. Keyboard behavior is covered by component tests and live focus-order inspection.
