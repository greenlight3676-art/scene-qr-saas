# Backend acceptance tasks — Stripe excluded

Reviewed 2026-10-24. Synced latest branch `9d892ee` before starting. No hosting,
deployment, initial migration, Stripe operation, production import or email send
is included in this work. A completed preparation is distinct from live acceptance.

## 1. Restricted database connection

Completed: read-only hosted SQL confirms schema v4 and `scene_runtime` has NOLOGIN,
NOSUPERUSER, NOCREATEDB, NOCREATEROLE and NOBYPASSRLS. This is the prepared privilege
role, not a working login. The existing connection validator rejects privileged
runtime roles, missing RLS/version metadata and remote URLs without verify-full.

Completed: `backend_preflight.py` provides offline checks by default and an explicit
read-only network check. It neither imports server.py nor initializes a database.
Using the existing private process environment:

```bash
python backend_preflight.py --check database --online
```

Blocked: no restricted runtime URL/password, private credential destination or
verified pooler connection details are supplied. Do not enable a login and place
its password in SQL/chat/Git logs. In a private administration session, provision
a dedicated unprivileged LOGIN inheriting `scene_runtime`, or set LOGIN/password
on the existing role after recovery prerequisites are met. Save it directly to
the owner's chosen private secret destination. Never use the postgres owner for
runtime. Obtain the exact connection details from the project's Connect panel.
Then run the read-only check above. No role or password was changed in this run.
Direct DNS checks for both the project database and Auth hosts also failed in
this sandbox. Run actual credentialed checks from a permitted private environment
with working network access; connected admin metadata access is a separate path.

## 2. Auth configuration and email templates

Completed: local signup/verification/recovery/revocation/invite API contracts were
rerun with synthetic provider responses. Modern publishable-key availability was
confirmed through the connected Supabase tool; values were withheld. No secret
service-role key is required. The key is not configured in this process.

Completed: reviewed OTP-only drafts are in `supabase/templates/confirmation.html`
and `supabase/templates/recovery.html`. These use `{{ .Token }}`, no user metadata,
and explicitly require the initiating browser, matching the existing backend.
They are local drafts, not remotely applied or sent.

Blocked: actual staging HTTPS origin, exact redirect allowlist, verified SMTP
sender/private credentials, provider configuration access and an authorized test
recipient. Available Supabase tools do not expose Auth-settings updates. Do not
guess an origin or enable email auto-confirmation. Configure Site URL, exact
redirects, email/password enabled and confirmation required privately. Apply the
drafts to the matching provider templates, then run:

```bash
python backend_preflight.py --check auth --online
```

This checks public provider policy only. It does not establish delivery or create
an identity. No request to signup, recover, invite or send was made to a provider.

## 3. Real delivery and session acceptance

Prepared: confirm sender SPF/DKIM and DMARC policy with the sender owner; use one
explicitly approved staging mailbox. Run signup → inbox code → verification →
owner onboarding → login; then addressed staff invite → verified join → role
checks → removal. Run password recovery and verify old sessions lose access,
including a simulated provider failure and a fresh successful recovery attempt.
Record only outcomes, timestamps and opaque test identifiers; omit codes,
passwords, tokens and message bodies. Check wrong-email/code, replay, expiry,
foreign tenant and CSRF denial. Do not record inbox delivery from an API acceptance.

Blocked: recipient/origin/SMTP and runtime connection above. An existing deployed
staging origin may be used only if supplied; creating hosting remains excluded.
Outbox sending remains explicitly disabled unless scoped sending authorization is
recorded. No background worker or recurring job was started.

## 4. Backup and restore

Verified: FORGE organization reports plan `free`. Supabase's current backup docs
describe daily backups for paid plans and recommend manual off-site exports for
Free. This does not prove any backup exists for this project. No plan upgrade,
PITR purchase or paid branch was initiated.

Verified independently: the latest branch already contains passing SQLite restored
API acceptance and an actual PostgreSQL 17 disposable dump/restore drill comparing
full table contents and identity sequences. See BACKEND_WORKFLOW_RECOVERY_REPORT.md.
Local backup and restored API tests were rerun. They are not a hosted restore.

Blocked: hosted dump credentials, approved private backup location/retention, a
separate approved restore target, and existing matching pg_dump/pg_restore tools.
Neither PostgreSQL client is installed here; no installation was attempted.
Use a direct/session-mode connection for the export; never transaction pooling
for pg_dump. Keep the existing hosted project untouched during restore testing.
Export the application schema/data plus separately reviewed roles/grants/RLS and
Auth recovery requirements. Protect the archive and record its checksum privately.
Restore to an isolated target; compare complete data, constraints, policies, roles,
sequences and version, then exercise the two-business workflow under the restricted
role. Provider-managed Auth and Storage recovery need separate verification.
Do not represent an SQL metadata export as a restorable database backup.

## Verification and completion status

`python backend_preflight.py` ran and exited **2**, correctly reporting missing
database/Auth/mail configuration. Exit 0 means only the selected read-only checks
passed; `not_run`/`blocked` returns 2. Even configured mail never reports delivery.
Seven new tests verify offline behavior, explicit read-only checks, safe failures,
secret redaction and the distinction between configuration and acceptance.

Owner input requested: staging origin, approved test mailbox and existing private
credential-store/file location (names/paths only, no passwords in chat). Those
answers remain required before dependent tasks can complete. Stripe is excluded
from both the checklist and the preflight tool.

Sources reviewed:
- https://supabase.com/docs/guides/platform/backups — backup plan coverage and
  Free-plan export recommendation, accessed 2026-10-24.
- https://supabase.com/docs/guides/platform/migrating-to-supabase/postgres —
  direct/session-mode dump connection guidance, accessed 2026-10-24.
- https://supabase.com/docs/guides/auth/auth-email-templates — OTP template
  variables and template configuration, accessed during the preceding review.

Published preparation source: `aefe340633302e9506ce209901053c3eb0769bd7`.
All four CI jobs passed in
https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/40073097092:
79 application Python tests passed, 21 intentional PostgreSQL/browser skips;
11 disposable PostgreSQL migration/security/restore checks passed; 59 restricted
PostgreSQL API checks passed, two SQLite-only checks skipped; 24 frontend tests
passed; 10 browser workflows passed; container build/readiness/restart passed.
No final failures. These results do not remove the live acceptance blockers above.
The final evidence update changes documentation only.
