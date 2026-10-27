# Scene QR backend operations runbook

Development deliverables are not deployment authorization. Record owner approval
with destination/scope in config/APPROVALS.md before production writes, sending,
spending or deployment. No recurring task is configured by this repository.

## Staging and credentials

1. Preserve the running SQLite beta and original backups. Use a private staging
   app and a separate database. Verify project reference cwehqnziwabvnzviaqlf,
   FORGE, us-east-1; do not reuse any other merchant's Supabase project.
2. Supply a migration schema-owner URL separately from a restricted runtime URL.
   Runtime must not own objects or inherit privileged roles. Enforce TLS
   sslmode=verify-full with the host trust chain. Never log URLs/passwords or
   put environment files in Git. Use a modern Supabase publishable key for the
   server Auth transport; no service-role key is needed by the application.
3. Verify available hosted backup/recovery features and run a restore into an
   isolated target before approving migrations. Apply v4 only after reviewing
   POSTGRES_MIGRATION.md and the backup/import rehearsal evidence.
4. As migration administrator, provision table grants then run reviewed
   database_security.py hardening. Run PostgreSQL tests with restricted runtime
   credentials on disposable fixtures; never use hosted business data as a test.
5. Configure managed confirmation-required email/password Auth, SMTP sender,
   exact Site URL/redirects and code-based signup/recovery templates. Production
   startup and managed signup/login fail closed if the public Auth settings show
   email auto-confirmation or email login disabled. Test real delivery with
   explicitly approved staging accounts. No custom CAPTCHA widget is installed;
   if enabling provider CAPTCHA, wire the provider token to the signup API.
6. Begin with SCENE_BILLING_MODE=test and matching Stripe TEST credentials,
   reviewed prices/API version/webhook secrets. Live mode is implemented behind
   an explicit SCENE_BILLING_MODE=live operator setting and requires matching live
   credentials, prices and webhook endpoint. Do not activate it without completed
   provider acceptance. This release leaves the deployed mode/config unchanged.
   Reconcile subscriptions through webhooks, never success URLs. The Sites proxy
   must preserve Stripe-Signature, exact body bytes and Idempotency-Key.
7. SCENE_ENV=production enforces guest sessions, subscriptions, trusted hosts,
   HTTPS, no demo, secure cookies, PostgreSQL and managed Auth. Staging can use
   these same security gates with test billing. The existing SQLite image smoke
   test intentionally exercises pilot mode, not a hosted production deployment.

## Backup and restore

- SQLite: use `python backup.py SOURCE PRIVATE_NEW_BACKUP`. The backup API reads
  a consistent snapshot including WAL, refuses overwrite, creates mode 0600 and
  checks integrity/foreign keys. Open/restore a copy and verify counts before
  relying on it. Do not copy only the active SQLite file while writers run.
- PostgreSQL: use approved hosted backup/PITR facilities and verify entitlement,
  retention, encryption, recovery point and recovery time requirements. Keep a
  separately protected logical dump where policy requires it. `pg_dump` produces
  a consistent snapshot; a custom archive must be tested using `pg_restore` into
  a new isolated database. Match supported client/server versions and record
  archive checksums, counts, constraints, schema version and restore commands.
- Do not pass password-bearing URLs as shell arguments. Prefer a permission-0600
  service/password file or the host secret environment. Do not print secrets.
- The CI restore drill dumps an isolated synthetic schema, creates a random
  scene_test_restore_* database, restores with pg_restore and compares all
  application counts. Its cleanup removes only that test-created database.
  This proves the procedure on CI; it does not prove hosted backup entitlement,
  PITR, private backup retention or production recovery times.
- Before cutover, stop SQLite writers, create/restore-test the backup, import
  into an empty PostgreSQL target and compare counts/IDs. Preserve QR tokens,
  request snapshots and audit records. Source is opened read-only. Any failure
  rolls back; diagnose it without modifying the retained source.
- Before PostgreSQL takes writes, rollback can clear SCENE_DATABASE_URL and use
  the retained SQLite file. After new writes, that SQLite is stale: stop writes,
  recover/reconcile all accepted data before rollback. No destructive down
  migration or unreviewed reverse import is a production recovery strategy.

## Monitoring and failure handling

- `/healthz` is process liveness. `/readyz` checks DB access and current PG schema;
  return 503 removes the instance from traffic. Startup rejects stale schemas,
  missing RLS, owner runtime roles and unsafe production settings.
- Collect structured scene.http logs and request IDs in a private destination.
  The app logs route templates, HTTP status, duration and exception type without
  paths/query strings, tokens, passwords or request payloads. Disable raw access
  logs at ingress too where URLs contain QR/verification tokens. Configure
  latency/error/429/5xx, DB availability and backup-age alerts separately.
- Restrict proxy forwarding to trusted ingress IPs; rate limiting uses ASGI peer
  IP after Uvicorn's trusted-proxy processing. Configure request/body/time limits
  at ingress and database connection capacity. The backend caps bodies at 64 KiB.
- Provider Auth outages fail private access closed. Sessions expire absolutely;
  users re-login after provider token expiry. Password recovery revokes local
  sessions first, so a failed provider write requires a new recovery attempt.
- Stripe failures return non-2xx and leave no dedupe marker; Stripe may retry.
  Replayed accepted events return 200 without repeating effects. Subscription
  reads reconcile canonical state; inspect unknown/unbound customer events.
  Verify lifecycle behavior against a real test account before rollout.
- Invitation creation queues mail. Sending remains disabled by default. Once a
  verified sender/credentials and SCENE_MAIL_SEND=1 are explicitly configured,
  each new invitation is sent after its transaction commits. Owners can retry one
  ready queued invitation from Business setup; the same provider idempotency key
  is reused. No recurring worker is installed. Provider acceptance is not inbox
  delivery: owner-only delivery checks read the provider's latest event without
  exposing email contents. Inspect retries,
  bounded attempts/review state, sender DNS and provider bounce/complaint logs.
- Customer structured redaction does not erase free-text notes/backups. Adopt an
  approved privacy/retention policy and perform verified tenant-scoped reviews.

References checked 2026-10-22:
https://www.postgresql.org/docs/current/app-pgdump.html and
https://www.postgresql.org/docs/current/app-pgrestore.html (backup/restore CLI),
and the provider references in BACKEND_COMPLETION_REPORT.md.
