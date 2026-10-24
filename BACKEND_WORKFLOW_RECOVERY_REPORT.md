# Two-business workflow and recovery acceptance

Scope: backend-only verification at source 421dcfb6d22f9e0c68b00848b0a38b9428b91070. No hosting, deployment,
Stripe configuration, real email delivery or customer-data changes.

## Executed locally
- Baseline complete Python suite: 70 passed, 21 skipped.
- Added two-business acceptance and SQLite restored-API tests: 2 passed.
- Final complete Python suite: 72 passed, 21 skipped.
- Frontend regression runner: 24 passed.
- JavaScript syntax and new Python test compilation passed.
- The 21 skips are separate PostgreSQL/browser checks; they are not counted as passed.
- Installed test dependencies in an isolated local virtual environment. No app
  dependency files or runtime implementation changed.

## New acceptance coverage
Both distinct owners register separate synthetic businesses, obtain QR PNGs,
read their own public QR catalogs, acquire station-bound guest sessions, submit
consented inquiry requests and update their status. Tests check both directions:
foreign dashboards/customer lists are denied, cross-business request IDs cannot
be updated under either URL, private receipts reject another guest's ticket, and
public catalogs/receipts do not expose contact details. A guest capability cannot
be reused at the other business's QR station.

The SQLite recovery test backs up the actual disposable API database, changes
the original after the backup, restores the earlier snapshot to a new file and
points the API at that copy. The same isolation, QR, receipt and session assertions
pass after restore; idempotent retry and a further authenticated status change
also work. No real merchant database or credentials were used.

The PostgreSQL dump/restore drill now compares complete contents of all 21
application tables (including schema version metadata), rather than counts alone,
and checks that restored identity sequences cannot collide with existing IDs.
The new two-business workflow is included in the restricted-role PostgreSQL CI job.

## PostgreSQL and CI
Verified source: `06f91871bbe19034995e6c06f4da0808a6d4c71b` on `qr-overnight-build`.
All four CI jobs passed in https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/40072244351.

- Application Python suite: **72 passed, 21 skipped** (separate PG/browser suites).
- PostgreSQL 17 migration, constraints and actual dump/restore: **11 passed**.
- Restricted PostgreSQL API contracts, including the new two-business lifecycle:
  **59 passed, 2 skipped** (SQLite-only trigger and SQLite-only recovery cases).
- Founder lifecycle: passed separately on SQLite and PostgreSQL.
- Frontend regression checks: **24 passed**.
- Mobile browser workflow job: passed.
- Container build, readiness and account/request persistence after restart: passed.

The new SQLite restore acceptance and full-row/identity-sequence PostgreSQL restore
assertions passed. No application implementation fix was required. Local PostgreSQL
tools are unavailable; the actual dump/restore used the disposable PostgreSQL 17 CI
container. These results do not claim a hosted Supabase restore rehearsal.

## Verification boundaries
These are real API/database operations on synthetic local/CI data. Local account
registration does not prove Supabase confirmation or password-recovery email
delivery. The PostgreSQL restore target is disposable CI infrastructure; this does
not verify hosted Supabase backup entitlement, retention, credentials or recovery.
No provider acceptance test is represented as passed.
