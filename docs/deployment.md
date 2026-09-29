# Production Deployment

The supplied production Compose stack is a hardened single-host reference. It runs PostgreSQL on a
private Docker network, applies Alembic in a one-shot service, runs FastAPI as a non-root read-only
container and serves the built PWA through Nginx. Use a managed PostgreSQL service and managed
ingress for a higher-availability deployment.

## Security Assumptions

- Terminate TLS 1.2 or newer at a trusted load balancer or host reverse proxy. Port `8080` binds to
  `127.0.0.1` by default and must not be exposed directly to the internet.
- The edge proxy must replace, not append blindly to, client-supplied forwarding headers and retain
  the security headers emitted by the frontend container.
- DNS, certificates, firewall rules, log retention, alerting and secret rotation are operator-owned.
- Do not run `app.db.seed` in production. The seed is fictional demonstration data only.

## Prepare Configuration

From the repository root:

```bash
cp deploy/production.env.example deploy/production.env
install -d -m 700 deploy/secrets backups
POSTGRES_PASSWORD="$(openssl rand -hex 24)"
printf '%s' "$POSTGRES_PASSWORD" > deploy/secrets/postgres_password
printf 'postgresql+psycopg://ncct:%s@db:5432/ncct_training' "$POSTGRES_PASSWORD" > deploy/secrets/database_url
openssl rand -hex 64 > deploy/secrets/jwt_secret_key
openssl rand -hex 64 > deploy/secrets/biometric_encryption_key
unset POSTGRES_PASSWORD
chmod 600 deploy/secrets/*
```

Edit only the public values in `deploy/production.env`: replace `training.example.gov.in`, confirm
the database name/user and choose the loopback port. The four generated secret files are ignored
by source control.

`BIOMETRIC_ENABLED=false` is the production default because the repository includes only the
clearly labelled demonstration face provider. Do not change it to `true` with
`FACE_VERIFICATION_PROVIDER=demo`; startup intentionally fails. A production provider adapter must
implement the documented `FaceVerificationProvider` boundary and pass privacy, presentation-attack,
accuracy, accessibility and security review before enablement. Keep its credentials backend-only,
and rotate the separate biometric encryption key under a tested re-encryption or re-enrolment plan.

For the local FAQ career provider, keep `CAREER_AI_PROVIDER=local`. To opt into a Gemini-compatible
provider, write its key to `deploy/secrets/gemini_api_key`, set `CAREER_AI_PROVIDER=gemini`, and add
the override file to every Compose command:

```bash
chmod 600 deploy/secrets/gemini_api_key
docker compose --env-file deploy/production.env -f docker-compose.prod.yml -f docker-compose.gemini.yml config --quiet
```

## Validate And Deploy

Without the optional provider override:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml config --quiet
docker compose --env-file deploy/production.env -f docker-compose.prod.yml build --pull
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d
docker compose --env-file deploy/production.env -f docker-compose.prod.yml ps
curl --fail --silent --show-error http://127.0.0.1:8080/health
curl --fail --silent --show-error http://127.0.0.1:8080/api/v1/health/ready
```

The `migrate` service must finish successfully before the backend starts. Treat a migration failure
as a stopped deployment; inspect it with:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs migrate
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs backend frontend
```

Verify the public HTTPS URL, certificate chain, HSTS, CSP, CORS preflight, sign-in, refresh/logout,
kiosk pairing, file download authorization and public certificate verification before routing real
traffic.

## Repeatable Demonstration Environment

The development seed is idempotent and can be rerun without duplicating its baseline records:

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

Never use these commands against a production database. The seed does not delete additional test
records created by Playwright or users.

## Backup And Recovery

Use encrypted automated backups with an off-host copy. For a self-hosted database, take a custom
format logical backup as a minimum baseline:

```bash
BACKUP="backups/ncct-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose --env-file deploy/production.env -f docker-compose.prod.yml exec -T db \
  pg_dump --username=ncct --dbname=ncct_training --format=custom > "$BACKUP"
shasum -a 256 "$BACKUP" > "$BACKUP.sha256"
```

For production recovery objectives, enable provider snapshots and PostgreSQL WAL archiving for
point-in-time recovery. Define RPO/RTO, retention, encryption keys and responsible operators.
Database backups may contain encrypted biometric templates and biometric audit history. Treat them
as sensitive personal-data backups, encrypt them again at the backup layer, keep the biometric key
in a separate secret system, restrict restore access and align backup expiry with the approved
biometric retention/deletion policy. Restoring an older backup must not silently reactivate consent
or deleted templates; run the deletion reconciliation procedure before serving traffic.

Restore only into an isolated staging database first. The following command replaces matching
objects and is destructive to the target database:

```bash
cat backups/approved-restore.dump | docker compose --env-file deploy/production.env \
  -f docker-compose.prod.yml exec -T db pg_restore --username=ncct --dbname=ncct_training \
  --clean --if-exists --no-owner --no-privileges
```

After restore, run `alembic current`, readiness checks and a sampled sign-in/programme/certificate
verification before declaring recovery complete. Perform and record restore drills at least
quarterly.

## Rollback And Operations

- Tag both application images with an immutable release identifier. Keep the prior image available.
- Back up before schema changes. Alembic downgrades are not an automatic production rollback;
  restore or run a reviewed forward fix when a migration has transformed data.
- Export application logs to a restricted sink and alert on readiness failures, repeated 401/403,
  rate limits, unexpected 5xx, migration failures and abnormal audit events. Correlate using
  `X-Request-ID`.
- Run only one migration job at a time. For multi-replica deployments, move rate limiting to the
  shared edge and use managed object storage plus malware scanning for user files.
- Review pending account-deletion requests daily until a scheduled worker and administrator queue
  are added. Preserve only records covered by the approved retention schedule.
