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
The expanded CI run is pending publication/execution. Its actual outcome will be
recorded here after completion. Local PostgreSQL tools are unavailable; the dump/
restore check uses the existing disposable PostgreSQL 17 CI container.

## Verification boundaries
These are real API/database operations on synthetic local/CI data. Local account
registration does not prove Supabase confirmation or password-recovery email
delivery. The PostgreSQL restore target is disposable CI infrastructure; this does
not verify hosted Supabase backup entitlement, retention, credentials or recovery.
No provider acceptance test is represented as passed.
