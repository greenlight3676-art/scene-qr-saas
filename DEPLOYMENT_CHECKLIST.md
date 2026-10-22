# SCENE — Pilot and commercial launch gates

## Pilot gate (invite-only, low volume)

- [ ] Host over HTTPS with a stable public hostname and **persistent database volume**.
- [ ] Use a new DB and environment `SCENE_DEMO=0`, `SCENE_SECURE_COOKIE=1`, `SCENE_PUBLIC_URL=https://...`.
- [ ] Restrict the pilot to a single app instance and single Uvicorn worker.
- [ ] Arrange database backups and test restoring one.
- [ ] Create a real owner business with verified sample offerings; never treat mock TRIO menu items as authentic.
- [ ] Create a QR station, scan printed signage from two different phones over cellular, verify the correct station.
- [ ] Invite a staff member with a single-use link and test their restricted account.
- [ ] Submit a service request from a guest phone, change status from staff phone, and verify the guest's receipt updates.
- [ ] Rotate a QR code and confirm the old printed URL stops loading.
- [ ] Confirm the venue knows requests do not make payments, reservations or kitchen orders.
- [ ] Ask the venue about privacy notices, signage, spam abuse, menu updates and staff training.

## Commercial SaaS launch gate (not built yet)

- [ ] Managed Postgres or Supabase, robust migrations, Row-Level Security with negative cross-tenant tests.
- [ ] Email verification, password recovery, staff role lifecycle, revoke users and audit logs.
- [ ] Stripe subscription plans, webhook signatures/idempotency, billing portal and entitlement checks.
- [ ] Guest request abuse prevention and better rate limits across workers, with monitoring and alerts.
- [ ] Stronger QR session abuse controls, consent/privacy requirements, and data deletion/export.
- [ ] Multi-location, platform admin, support, analytics, event retention and automatic backups.
- [ ] Dedicated staging/prod environments, CI/CD, security review and load tests.
- [ ] Explicit POS contracts/permissions before any order or payment integration.

## PostgreSQL transition gate

- [ ] Follow POSTGRES_MIGRATION.md; retain and restore-test the SQLite backup.
- [ ] Use a separate restricted runtime role and TLS; never runtime schema-owner credentials.
- [ ] Pass disposable PostgreSQL migration tests and full API/backend parity tests.
- [ ] Verify failed imports roll back, preserve source data, and reset sequences correctly.
- [ ] Implement/test RLS with tenant A/B and anonymous negative cases before commercial rollout.
- [ ] Reconcile PostgreSQL writes before reverting to a stale SQLite backup.


## Founder’s Test audit evidence — 2026-10-22

Commercial launch remains **FAIL**. See FOUNDER_TEST_REPORT.md for per-requirement
PASS/FAIL/BLOCKED findings. Source `1266d139` passed all four jobs in
https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39723075114,
including restricted PostgreSQL, ten Chromium workflows and a non-demo Docker
workflow with restart persistence. These automated synthetic checks do not
complete the HTTPS/physical-phone, managed auth, billing, complete tenant RLS,
hosted restore, monitoring or privacy-operation gates above.
