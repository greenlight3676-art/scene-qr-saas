# Task 1 transition plan and current limits

SQLite stays the default. PostgreSQL is opt-in and experimental until the live
backend tests, API parity tests, restore drill and two-device checks pass.
No source data is automatically exported, overwritten or deleted.

1. Install `requirements-dev.txt` and (only for PostgreSQL)
   `requirements-postgres.txt`. Use PostgreSQL 16+ and a dedicated empty database.
2. Use a schema-owner migration role through `SCENE_MIGRATION_DATABASE_URL` in
   secure environment settings. Run `python3 migrate.py up` explicitly. Startup
   only checks the schema version; it does not apply migrations.
3. Create a separate LOGIN runtime role without SUPERUSER, CREATEDB, CREATEROLE,
   or schema ownership. Grant CONNECT on the dedicated database, USAGE on public,
   SELECT/INSERT/UPDATE/DELETE on the nine application tables, SELECT on
   scene_migrations, and USAGE/SELECT on their identity sequences. Revoke CREATE
   on public from PUBLIC and the runtime role. Do not expose database access to
   browsers. Use TLS (`sslmode=verify-full` and the host CA) for remote databases.
4. Stop all SQLite writers. Make a consistent backup with SQLite's backup API
   (or `.backup`), store it privately, and test opening/restoring it. Do not copy
   a live WAL database file alone. Keep the original SQLite file untouched.
5. Run `python3 migrate.py import --sqlite /private/consistent-backup.db`.
   The source opens read-only. The target must be empty; import preserves IDs,
   password hashes, sessions, receipts and QR tokens, checks row counts and
   resets sequences. Any failure rolls back the transaction. Cross-business
   legacy references fail import rather than being silently repaired.
6. Set `SCENE_DATABASE_URL` to the restricted runtime URL and `SCENE_DEMO=0`.
   Clear SCENE_DATABASE_URL to return to SQLite. SCENE_DB still identifies the
   retained SQLite database. Keep one worker/instance during this transition.
7. Before allowing traffic, run API workflow/security parity checks, inspect
   counts privately, scan existing QR codes and test guest receipt/staff updates.
   Run `SCENE_TEST_POSTGRES_URL=... python3 -m pytest -q tests/test_postgres.py`
   against a disposable test database with schema-creation privileges.

Rollback before cutover: clear SCENE_DATABASE_URL and restart against the retained
SQLite backup. After PostgreSQL accepts writes, the old SQLite file is stale:
stop writes and reconcile/restore from an approved PostgreSQL backup before
switching. No reverse importer is supplied; never silently discard new requests.
`migrations/001_down.sql` is destructive and only for empty development schemas;
it is not a production rollback procedure. Test uses transaction rollback.

The server retains membership/role checks and tenant-scoped queries. Composite
foreign keys enforce matching tenants for station/product request references and
scans. The runtime role must be restricted separately as above. PostgreSQL RLS is
implemented as backend-only policies with transaction-local tenant scope on requests
and SELECT-only receipt capabilities. Other tables still have backend-wide policies
and server-side tenant checks. Broader tenant RLS and live security/restore checks
remain required before commercial rollout. Global transaction advisory locking deliberately
preserves SQLite queue/idempotency/invite serialization across connections; it
limits throughput and is not Task 3 realtime or distributed scaling.

Remaining validation: full API suite on PostgreSQL (including concurrent requests,
invite reuse, tenant A/B roles and guest privacy), import failure/recovery fixtures,
restricted-role permission tests, RLS negative tests, live backup recovery and
real phone/browser layout verification. No POS, payment or reservation integration
was added. Submissions remain requests for staff.

## Version 2 hardening preparation (supersedes the earlier no-RLS statement)

Review `PHASE_1_2_REPORT.md` before cutover. `python3 migrate.py up` now adds nullable
structured-request fields and advances the version from 1 to 2, in one transaction.
Before startup, use the schema owner to run:

```bash
python3 database_security.py --runtime-role YOUR_DEDICATED_BACKEND_ROLE
```

It uses `SCENE_MIGRATION_DATABASE_URL`; never put that URL in source or a browser.
Run only on an approved destination with a verified backup. The command grants no
new table privileges. Provision the existing restricted-role grants first.
All ten tables get backend-only RLS policies; requests additionally enforce tenant
context and SELECT-only receipt lookup. Existing unknown policies cause rollback.
Other tables remain tenant-checked by the server, with backend-wide DB policies.
PostgreSQL startup fails until RLS and version 2 are present. Do not apply this to
an unidentified Supabase project. Verify the disposable PostgreSQL suite and API
parity before a hosted migration. All 8 database and 24 PostgreSQL API checks passed
on source 4c18454 in GitHub CI; no hosted migration or restore drill was performed.

## Version 3 security preparation — 2026-10-22

Version 3 is additive: `sessions.managed_token`, `auth_identities` and
`audit_events`. The Python migration sequence is transactional and repeatable;
version 1 and 2 data is retained. The importer includes security tables when
present in the SQLite backup, and accepts older snapshots without them.
SQLite independently adds the same optional schema without changing beta auth.
The development down script drops these tables too; it is still destructive,
never a production rollback strategy.

Re-run reviewed restricted-role grants for the two new tables, then hardening,
after migration and before runtime startup. Hardening restricts products,
stations, scans, invitations, requests and audit events by transaction-local
business ID. QR/invitation resolution has SELECT-only token capabilities;
receipt resolution remains SELECT-only. Scope never persists across transactions.
Identity bindings are SELECT-only for runtime; audit records allow SELECT/INSERT,
with UPDATE/DELETE/TRUNCATE revoked. Migrations, bindings, privileges and runtime
credentials belong to different responsibilities; never use owner credentials in
SCENE_DATABASE_URL. Users, businesses, memberships, sessions and migration metadata
still require trusted backend-wide operations and server authorization. This is
backend RLS defense in depth, not authorization for a browser to connect directly.

No hosted migration has been performed. See SECURITY_INTEGRATION_REPORT.md for
managed auth limitations and required cutover evidence.

## Version 4 backend integration

The current schema version is **4**. Upgrades from 1/2/3 are transactional and add
locations, customers, guest sessions, durable rate buckets, verification flows,
revocation cutoffs, billing state/events and invitation outbox. Station content/
destination/location fields, addressed invites, recovery-session purpose and
request customer associations are additive. New records use opaque text IDs.
PostgreSQL composite foreign keys reject cross-tenant station/location,
request/customer, guest/station and outbox/invitation references. The importer
orders new parent tables before dependent rows and requires every application
table to be empty, including optional v4 tables absent from an old source.

Grant the reviewed restricted backend role SELECT/INSERT/UPDATE/DELETE on new
application tables (audit UPDATE/DELETE and identity UPDATE/DELETE are revoked
by hardening), then run hardening as the migration administrator. Never grant
runtime schema ownership, CREATE, role membership with owner powers, SUPERUSER,
BYPASSRLS or production owner credentials. Startup requires all expected RLS
flags and schema version 4. No migration runs automatically at PostgreSQL startup.
Do not run the development down script against retained business data.

The Psycopg adapter disables automatic prepared statements (`prepare_threshold=None`)
for Supavisor transaction-pooler compatibility. Tenant/receipt/capability settings
are transaction-local, never session-persistent. Use a verified direct/session
connection for migration/restore administration; validate the actual runtime
pooler/TLS configuration in staging before cutover.
