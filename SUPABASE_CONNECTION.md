# Scene QR SaaS — verified Supabase destination

Verified 2026-10-22 using the connected Supabase account.

| Setting | Value |
| --- | --- |
| Owner organization | FORGE |
| Project name | Scene QR SaaS |
| Project reference | `cwehqnziwabvnzviaqlf` |
| Region | `us-east-1` |
| API URL | `https://cwehqnziwabvnzviaqlf.supabase.co` |
| Dashboard | https://supabase.com/dashboard/project/cwehqnziwabvnzviaqlf |
| Server | PostgreSQL 17.11 |
| Application tables | None at verification |
| Application migrations | None at verification |

This is the newly created **Scene QR SaaS** project. Do not repurpose the Cutz by Kev, Legends Barbershop or unnamed Supabase projects.

## Important: connected project is not a completed migration

The existing working app is FastAPI + SQLite by default. Its optional PostgreSQL adapter is server-side Psycopg, enabled by `SCENE_DATABASE_URL`; its migrations use `SCENE_MIGRATION_DATABASE_URL`. Managed registration, login, confirmation/recovery and onboarding APIs/UI, invitations and an outbox are implemented and tested with synthetic providers. Hosted provider configuration/delivery verification and realtime remain outstanding. See `BACKEND_COMPLETION_REPORT.md` and `OPERATIONS_RUNBOOK.md`.

* Do **not** point the browser at server/database credentials. Never commit database passwords, service role keys, access tokens, `.env` files, or customer data.
* Do **not** run `migrate.py up`, `database_security.py`, `supabase db push`, or a hosted data import until the schema plan, restricted runtime role, backup/recovery path and target environment have been reviewed and validated.
* Continue testing PostgreSQL migrations and tenant/RLS security against a disposable **local** database or isolated test environment, as existing GitHub CI does. `main` and live infrastructure stay untouched without a separate deployment decision.
* Reference `POSTGRES_MIGRATION.md`, `PHASE_1_2_REPORT.md`, `DEPLOYMENT_CHECKLIST.md`, `CODEX_TASKS.md`, and `AGENTS.md`.

## Link the CLI from your own Chromebook

The following establishes local CLI project identity but does not run database migrations:

```bash
cd ~/scene-qr-saas
npx supabase --help
npx supabase login
# Only if the repository does not already have supabase/config.toml:
# npx supabase init
npx supabase link --project-ref cwehqnziwabvnzviaqlf
```

The CLI may prompt for a password/browser sign-in. Enter secrets only in their intended authenticated prompts. Never paste credentials into chat or GitHub.

## Work to complete before live cutover

1. Validate the new database is still empty and verify migration/rollback and restore strategy; review hosted database backups available under the project plan.
2. Provision a least-privilege *server-only* runtime role and a distinct migration role. Confirm privileges and RLS via negative tenant A/B and guest-access tests.
3. Apply application schema and security as one reviewed, repeatable migration sequence, then recheck Supabase security advisors. Preserve SQLite and its backup for rollback/reconciliation.
4. Switch only a private staging app to the restricted PostgreSQL URL, with HTTPS and no demo users. Test phone QR scans, customer requests, staff status changes and isolation.
5. Implement Supabase Auth or another managed auth system with verified email and recovery before any broad public or commercial launch. Define backups, monitoring and privacy policies.

**Status:** Project identity verified; no hosted schema, user data, or deployment changed during this documentation update.
