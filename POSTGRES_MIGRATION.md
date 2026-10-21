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
NOT implemented: the shared server still has table-wide access. RLS with verified
transaction-local identity and narrowly scoped public QR access remains required
before commercial rollout. Global transaction advisory locking deliberately
preserves SQLite queue/idempotency/invite serialization across connections; it
limits throughput and is not Task 3 realtime or distributed scaling.

Remaining validation: full API suite on PostgreSQL (including concurrent requests,
invite reuse, tenant A/B roles and guest privacy), import failure/recovery fixtures,
restricted-role permission tests, RLS negative tests, live backup recovery and
real phone/browser layout verification. No POS, payment or reservation integration
was added. Submissions remain requests for staff.
