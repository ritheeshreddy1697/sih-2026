# Security And Privacy Controls

This document records the controls implemented for the demonstration platform and the controls an
operator must add before processing real NCCT data. It is not a substitute for an organizational
security assessment, privacy impact assessment or applicable Indian legal review.

## Authentication And Sessions

- Passwords are hashed with Argon2 through `pwdlib`; plaintext passwords are never persisted or
  logged. Registration and reset passwords require at least 12 characters with upper-case,
  lower-case, numeric and symbol characters.
- Access tokens are short-lived JWTs with required issuer, audience, subject, session, issued-at,
  not-before, expiry and token-type claims. Only configured HMAC algorithms are accepted.
- Refresh tokens rotate on every use, are stored only in a Secure, HttpOnly, SameSite=Lax cookie,
  and are represented in PostgreSQL only by a SHA-256 digest. Logout, reset, suspension and data
  deletion revoke sessions.
- Login and password-reset lookup failures use generic responses. Unknown login identifiers are
  represented in audit data by a short SHA-256-derived value rather than the submitted email.
- Multi-factor authentication, government identity federation and breached-password screening are
  not implemented and remain production recommendations.

## Authorization

- FastAPI permission dependencies are the authorization boundary. Frontend route and control
  visibility consumes server-issued effective permissions and is only a usability layer.
- Services repeat resource ownership checks for institution, programme, batch, enrolment,
  conversation, employer and trainee records. Institute administrators are limited to their own
  hierarchy; NCCT super administrators have national scope.
- Permission denials and security-sensitive state changes append audit records with actor, event,
  success, request metadata and constrained event details.

## Input, Database And Browser Safety

- Pydantic schemas enforce types, lengths, ranges, enum allow-lists and cross-field rules. The
  reverse proxy and application reject oversized requests, and domain endpoints apply smaller
  file- and row-specific limits.
- SQLAlchemy builds parameterized statements. No API path constructs SQL by concatenating user
  values.
- React escapes rendered strings. The application does not use `dangerouslySetInnerHTML`.
- Production Nginx sends a restrictive Content Security Policy, HSTS, frame denial, MIME sniffing
  protection, referrer policy, permissions policy and cross-origin opener/resource policies.
- CORS permits explicit HTTPS origins, methods and headers only. The kiosk's `X-Kiosk-Token` is
  explicitly allow-listed; wildcard origins and production HTTP origins fail configuration.
- CSV exports prefix spreadsheet formula-leading values. Download filenames are normalized and
  emitted with RFC 5987 `filename*` disposition values.

## Uploads

- Endpoint allow-lists cover PDF, JPEG, PNG, DOC, DOCX, MP4, WebM, MP3, WAV and OGG only where the
  relevant feature needs them.
- Declared MIME type is checked against file signatures. DOCX files must contain the expected ZIP
  structure and stay within entry-count and decompressed-size limits.
- Files have endpoint-specific byte limits and are returned only after repeating ownership checks.
- Production deployment still requires malware scanning or content-disarm-and-reconstruction
  before files are made available to other users. Object storage with encryption, retention and
  quarantine policies is recommended instead of long-term database byte storage.

## Rate Limiting And Abuse Controls

- The application applies fixed-window per-client limits to authentication and general API paths.
- Production Nginx adds independent login/reset and API request limits before traffic reaches
  FastAPI. Career chat also uses a persisted per-user limiter.
- The in-process limiter is defense in depth, not a distributed quota. Multi-host deployments
  should enforce limits at the managed gateway or use a shared Redis-backed limiter.

## Consent And Personal Data

- Registration records acceptance of terms/privacy. Trainees can independently control placement
  visibility, communications and employer data sharing; each change appends a consent record.
- Employer contact and resume access requires active placement/data-sharing consent and the
  appropriate application relationship.
- QR mode performs no biometric processing: its camera frames remain in the browser's decoder and
  are not uploaded. Optional face mode is visibly separate and cannot run until an authenticated
  trainee grants purpose-specific, versioned consent and creates a protected template.
- Face mode performs one-to-one verification only after an active, enrolled trainee supplies their
  exact attendance identity code. It has no unknown-person identification, one-to-many search,
  continuous capture or surveillance API. Face verification is online-only; QR remains available
  without biometric consent and continues to work through the offline queue.
- Enrolment and verification accept exactly three signature-checked JPEG/PNG frames, each at most 2
  MB. Frames exist only for request processing and are never written to an application table,
  response, audit event or browser store. Container temporary storage is a `tmpfs`; operators must
  also prevent request-body capture at proxies and observability tools.
- Stored embeddings are encrypted with AES-256-GCM using a separate backend-only secret, random
  nonce, key version and identity/provider/model-bound associated data. Access is confined to the
  biometric service; APIs never return the plaintext embedding or ciphertext. Key rotation needs a
  reviewed re-encryption or re-enrolment procedure.
- Liveness, confidence and thresholds are computed on the backend. Only results at or above the
  automatic threshold create attendance. Uncertain results create a manual-review record with no
  check-in; rejection and failed liveness never mark presence. Challenges are short-lived,
  single-use and bound to trainee, session and kiosk.
- Trainees can delete their own template, while institute administrators are institution-scoped and
  NCCT administrators have national scope. Deletion removes the ciphertext, consumes outstanding
  challenges and appends consent-withdrawal and audit records. Account deletion also removes the
  template.
- The bundled demo provider uses a coarse visual template and frame-motion check. It is not face
  detection, certified face recognition or robust presentation-attack detection; a moving photo or
  replayed video may defeat it, and accuracy/fairness are not established. Production settings
  reject enabling this provider. Real deployment requires a privacy impact and lawful-basis review,
  explicit retention policy, certified liveness/PAD provider, demographic performance testing,
  accessibility alternative, incident response and vendor/data-residency review.
- The service worker never caches API responses. Private downloaded lessons and pending progress
  are user-keyed in IndexedDB and removed on sign-out.

## Account And Data Deletion

- An authenticated user requests deletion by confirming the current password, giving an optional
  reason and acknowledging statutory-retention obligations. A configurable cooling period defaults
  to 30 days; the user may cancel while pending.
- NCCT administrators can list pending requests and complete one with a resolution note. Completion
  revokes sessions, removes profile/contact/documents/resumes/chat/consent data, pseudonymizes the
  login identity and suspends the account.
- De-identified training, attendance, assessment, certification and append-only audit records are
  retained where operational or statutory evidence may be required. Operators must set and review
  the actual legal retention schedule before launch.
- Automatic scheduled completion and a dedicated administrator queue UI are not included. The API
  supports an approved operational runbook or future background job.

## Errors, Logs And Secrets

- Validation responses remove submitted values and Pydantic context, preventing passwords or
  uploads from being reflected. Unexpected failures return a generic message plus request ID while
  the traceback remains server-side.
- JSON responses are `no-store`. Audit records must never receive passwords, tokens, file bytes or
  provider keys. Production log shipping should redact authorization, cookie and kiosk-token
  headers at the collector.
- Production startup fails when JWT/database placeholders, insecure cookies, public API docs,
  wildcard hosts, wildcard CORS or non-HTTPS public URLs are configured.
- PostgreSQL, JWT and optional AI credentials are mounted from Docker secrets. Secret files must be
  mode `0600`, backed by a managed secret store in hosted environments and rotated through a tested
  runbook. Never place a provider key in a `VITE_*` variable.

## Release Gate

Before production, run the commands in `README.md`, exercise the Playwright demonstration, review
dependency audit output, test a database restore, confirm TLS and security headers at the public
hostname, and commission an independent penetration test and privacy review.
