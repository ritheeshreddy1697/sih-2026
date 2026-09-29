# NCCT Cooperative Training Platform

Monorepo for an NCCT cooperative training platform serving NCCT administrators, VAMNICOM/RICM/ICM administrators, trainers, trainees, nominating institutions and employers.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS and shadcn/ui-style primitives
- Backend: FastAPI, SQLAlchemy, Alembic and PostgreSQL
- Tests: Vitest, pytest and Playwright
- Local services: Docker Compose
- Authentication: Argon2 password hashing, JWT access/refresh tokens and server-side RBAC

## Prerequisites

- Node.js 20+
- npm 10+
- Python 3.11+
- Docker Desktop or compatible Docker runtime
- Google Chrome for the Playwright demonstration

## Exact Local Setup

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up -d db
npm ci
npx playwright install chrome
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
cd ..
```

The commands start only PostgreSQL in Docker, install locked frontend/test dependencies, apply all
migrations and load the idempotent fictional demonstration seed. The values in the example files
are local-development values only.

## Run Locally Without Docker

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal:

```bash
npm run dev
```

Open http://localhost:5173.

Public entry points:

- Landing page: http://localhost:5173/
- Sign in: http://localhost:5173/login
- Registration: http://localhost:5173/register

After sign-in, each seeded role opens its server-selected dashboard at
http://localhost:5173/dashboard.

Programme management:

- Catalogue and institute pipeline: http://localhost:5173/programmes
- Application tracking and review: http://localhost:5173/applications
- Nomination tracking and review: http://localhost:5173/nominations

Learning management:

- Course catalogue and trainer workspace: http://localhost:5173/learning
- Trainees can resume the seeded multilingual demonstration course from the catalogue.
- Trainers and institute administrators can open a course's `Manage` action to author content,
  assignments, question banks and assessments.

Attendance:

- Trainer, institute and NCCT workspace: http://localhost:5173/attendance
- Trainee attendance identity: http://localhost:5173/attendance
- Full-screen camera kiosk: http://localhost:5173/kiosk/attendance
- Raspberry Pi, laptop and Android setup: [hardware/README.md](hardware/README.md)
- The seed creates an active fictional attendance session for the demonstration programme. Register
  a kiosk in the attendance workspace to receive its one-time local device token.
- Trainees may explicitly enrol the optional demonstration face verifier from `/attendance`. It is
  online-only, performs one-to-one matching after an identity claim and never replaces the QR
  fallback. It is not approved for real biometric decisions.

Digital certificates:

- Administrator issuance and trainee skill wallet: http://localhost:5173/certificates
- Public verification links use `http://localhost:5173/verify/certificate/<token>` by default.
- Institute and NCCT administrators can configure thresholds, inspect server-calculated eligibility,
  issue PDF certificates and revoke them with a reason.
- Trainees can download certificates and share the public verification link from their wallet.
- The seed configures a fictional policy for the demonstration programme. It does not bypass
  eligibility or issue a certificate automatically.

Training operations:

- Administrator operations workspace and trainee self-service: http://localhost:5173/operations
- Institute administrators manage only their own timetable, venues, hostels and participant
  logistics. NCCT super administrators can select another active institution.
- The seed includes a fictional scheduled class, venue/classroom, hostel reservation, meal and
  transport details, emergency contact, material distribution and maintenance issue.

Employment exchange:

- Role-specific employment workspace: http://localhost:5173/employment
- The employer demo account represents a verified fictional company and can publish jobs, search
  certificate-backed candidates and manage hiring stages.
- The trainee demo account has a fictional digital certificate, verified employment skills,
  employment profile, resume and a fully explained job recommendation.
- Candidate contact details remain masked until the trainee enables data sharing and applies to
  that employer. Seeded data sharing is disabled by default.

Career counselling:

- Trainee workspace: http://localhost:5173/career-counsellor
- English, Hindi and Telugu guidance retrieves approved FAQs and current programme/job records.
- With the default empty `GEMINI_API_KEY`, the backend uses the local FAQ provider. To use a
  Gemini-compatible endpoint, set `CAREER_AI_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL` and
  `GEMINI_BASE_URL` in `backend/.env` (or the root `.env` for Docker Compose), then restart the
  backend.
- Provider keys are backend-only. Do not add them to `frontend/.env` or any `VITE_*` variable.
- Every authenticated workspace page also includes a compact assistant. It sends the current route,
  selected language and recent conversation turns to the same backend-only Gemini configuration,
  while keeping the richer sourced career workflow available to trainees on the dedicated page.

Analytics:

- NCCT and institute administrator dashboard: http://localhost:5173/analytics
- Results are calculated from persisted programme, attendance, learning, certificate and employment
  records. Date filters select cohorts by programme start date.
- Institute administrators see only their institution hierarchy. Headline metrics open paginated
  detail tables, and institution, programme and geography summaries can be exported as CSV.
- Fictional seeded data is labelled in the dashboard and CSV summaries.

## Run With Docker Compose

```bash
docker compose up --build
```

The backend container runs migrations and the idempotent development seed before starting.

Frontend: http://localhost:5173

Backend health: http://localhost:8000/health

API health: http://localhost:8000/api/v1/health

API documentation: http://localhost:8000/docs

## Demonstration Seed

The baseline demonstration seed is repeatable and does not duplicate its own records:

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed
```

For the development Compose stack:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed
```

Never run the demonstration seed against production.

## Demo Accounts

All seeded accounts use the development-only password `DemoOnly!2026`.

| Role | Email |
| --- | --- |
| NCCT super administrator | `superadmin@demo.ncct.gov.in` |
| Institute administrator | `institute.admin@demo.ncct.gov.in` |
| Trainer | `trainer@demo.ncct.gov.in` |
| Trainee | `trainee@demo.ncct.gov.in` |
| Nominating institution | `nominator@demo.ncct.gov.in` |
| Employer / recruiter | `recruiter@demo.ncct.gov.in` |

These accounts are for local development only. Change `SEED_DEMO_PASSWORD` before seeding a
shared non-production environment, and never run the development seed in production.

The seed also creates a fictional institution hierarchy and a complete trainee profile for
`trainee@demo.ncct.gov.in`. Seeded names, documents, programmes and certificates are explicitly
labelled as demonstration data and are not valid operational records.

The same trainee account is enrolled in `Cooperative Governance Learning Journey (Demonstration)`,
which includes English, Hindi and Telugu content; text, video, audio, PDF and external-resource
lessons; resumable progress; a reviewed assignment; and pre-training, quiz and post-training
assessments. All course content and results are fictional development data.

The trainer account is assigned to the same programme batch and can manage the seeded
`Demonstration kiosk check-in` attendance session. The trainee account's signed QR is available at
`/attendance`. Kiosk registrations and tokens are local development records only.

## Authentication

- Access tokens are short-lived JWTs and are sent in the `Authorization` header.
- Rotating refresh tokens are stored in an HttpOnly cookie and hashed in the database.
- Logout, password reset and account suspension revoke database-backed sessions.
- FastAPI dependencies enforce roles and permissions on protected endpoints.
- Password-reset requests return a token only in the development environment. A mail delivery
  integration is required before production deployment.
- Trainees can request and cancel account/data deletion from their profile. NCCT administrators
  complete approved requests after the configured cooling period; direct identifiers and private
  uploads are erased while de-identified statutory/audit evidence is retained.

The implemented security controls and production gaps are documented in
[docs/security.md](docs/security.md).

## Quality Checks

Frontend:

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm audit
```

Backend:

```bash
cd backend
source .venv/bin/activate
ruff check .
mypy app
pytest
python -m pip_audit --local
```

Complete role-to-role browser demonstration (requires PostgreSQL at the configured URL):

```bash
npm run test:e2e
```

This serial scenario creates a programme, approves a trainee, completes learning and QR attendance,
passes an assessment, issues and verifies a certificate, applies and shortlists for a job, and
checks the resulting NCCT analytics.

## Production Deployment

Production uses a separate multi-stage build, one-shot migration service, file-mounted secrets,
non-root/read-only application containers, same-origin Nginx API proxy and private database network.
Follow [docs/deployment.md](docs/deployment.md) for exact preparation, deployment, health-check,
backup, restore and rollback commands.

## Environment

Use `.env.example` and `backend/.env.example` for local configuration. Use
`deploy/production.env.example` only as a public production template; real PostgreSQL, JWT,
biometric-encryption and AI credentials belong in ignored secret files or a managed secret store,
never in source control or frontend `VITE_*` variables. Production keeps biometrics disabled while
the demonstration provider is configured.
