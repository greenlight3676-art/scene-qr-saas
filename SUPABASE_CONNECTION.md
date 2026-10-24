# Scene QR SaaS — hosted Supabase status

## Verified destination
- Project: Scene QR SaaS
- Organization ID: `yrgfwtjoxfdpslqeyjtt` (FORGE)
- Project reference: `cwehqnziwabvnzviaqlf`
- Region: `us-east-1`
- API URL: https://cwehqnziwabvnzviaqlf.supabase.co
- Dashboard: https://supabase.com/dashboard/project/cwehqnziwabvnzviaqlf

## Hosted database setup completed
This status supersedes the empty-project inspection in earlier reports.
The owner requested Supabase setup in the current session. The isolated Scene QR
project had no public tables or migration entries before the change. No SQLite
data was available here or imported, and no running app was switched.

Hosted migration `20261024031054_scene_v4_backend_schema_and_rls` applied
successfully. Its SQL is archived in
`supabase/migrations/20261024031054_scene_v4_backend_schema_and_rls.sql`.
Schema statements were generated from the existing v1 SQL and the v2/v3/v4 Python
schema modules at source `13cb9005cfa73ffcfda4ae051c8bcfe560eb99ab`.
No application behavior was rewritten.

- Application schema version: **4**.
- **21 tables**, each with RLS enabled.
- Table privileges revoked from PUBLIC, anon, authenticated and service_role.
- Dedicated `scene_runtime` role has no superuser, bypass-RLS, database/role
  creation or application schema creation privileges; it owns no app objects.
- Runtime gets table DML and identity sequence privileges only as needed.
  Audit events and identity bindings allow SELECT/INSERT only; schema version
  metadata allows SELECT only.
- Policies match the existing backend security model: tenant scope and selective
  QR, receipt, invitation, mail-worker and billing capabilities.
- `scene_runtime` is **NOLOGIN**, with no password provisioned. This prepares
  privileges without creating or exposing a reusable credential.
- Synthetic fixtures were inserted in one transaction, tested under the runtime
  and browser roles, and rolled back. Users, businesses and requests remain empty.
- Live SQL checks passed for unscoped denial, tenant A/B read and mutation
  isolation, tenant reassignment denial, composite foreign keys, own-tenant update,
  audit immutability, identity-binding protections, receipt access, QR privacy and
  direct anonymous/authenticated table denial.
- Supabase security advisors returned **zero lints** after application.

The rollback-only verification SQL is in `supabase/verify_scene_v4.sql`.
This is database verification, not a live hosted API or provider acceptance test.
No app tests were rerun locally because no Python/JavaScript application code
changed; earlier application CI evidence remains in BACKEND_COMPLETION_REPORT.md.

## Next: connect a private hosted backend
1. Choose the actual HTTPS backend host. This repository runs FastAPI; the Supabase
   database itself does not execute server.py. Sites may remain the frontend.
2. In a private authenticated database administration session, provision a strong
   password and LOGIN for `scene_runtime`, or a separate unprivileged LOGIN role
   that inherits it. Never use the postgres owner role for application traffic.
   Store credentials directly in the backend host's secret settings.
   No real password or connection string belongs in chat, Git or screenshots.
3. Set `SCENE_DATABASE_URL` to that restricted role's verified connection URL
   using `sslmode=verify-full`. Verify the actual pooler hostname/port from the
   project's Connect panel; do not guess them. Keep a separate administrative
   migration URL if future upgrades are needed.
4. Set `SCENE_AUTH_MODE=supabase` and
   `SCENE_SUPABASE_PUBLISHABLE_KEY` from the existing project API settings.
   Check managed_auth.py for its URL/configuration contract. Never use a secret or
   service-role key. Configure secure cookies, the real public origin and trusted
   hosts as OPERATIONS_RUNBOOK.md describes.
5. Configure Supabase confirmation-required email/password auth, the actual Site
   URL and exact allowed redirects, and code/token-hash email templates matching
   /auth/confirm. No Auth provider settings or SMTP templates were changed here.
6. Test signup/confirmation, login, recovery and QR request → correct owner queue
   → status update from the hosted app and phone. Database-only checks cannot
   establish these flows.
7. Preserve any existing SQLite data and back it up/restore-test it before an
   explicitly planned import or cutover. Hosted recovery, monitoring and capacity
   remain unverified. This empty-project initialization is not a recovery drill.

Email delivery and Stripe test-account/webhook acceptance remain outstanding.
No emails, live charges, paid resources, deployed app or production cutover were
created by this setup. Do not rerun the initial bootstrap SQL on this populated
schema; it intentionally refuses any pre-existing public application tables.
