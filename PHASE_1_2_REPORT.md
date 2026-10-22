# Scene QR database security and structured requests — 2026-10-21

Local implementation only. No Supabase project restored, no hosted schema changed,
no packages installed, no messages sent, no deployment or GitHub push performed.

## Recovery evidence and next gate

Connected Supabase `list_projects` returned two inactive projects (Cutz by Kev and
an unnamed project) and active Legends Barbershop on 2026-10-21. None is positively
identified as Scene QR. Owner identification is pending. Do not infer that a
barbershop database is this app. Do not resume projects or import data until the
specific destination and scope are confirmed and recorded in config/APPROVALS.md.
Supabase authentication/password recovery is still unimplemented.

## Database access model

`database_security.py` enables RLS on all ten application/metadata tables, revokes
PUBLIC/anon/authenticated table privileges, and grants policies only to a named,
restricted backend role. It refuses privileged roles, backend ownership and unknown
existing policies. Changes are transactional and repeatable. Role privileges still
must be provisioned as in POSTGRES_MIGRATION.md; policies do not grant privileges.

Requests enforce transaction-local tenant scope, set after membership validation or
QR resolution. Receipt lookup sets a hashed capability and has a SELECT-only policy.
Unscoped requests are hidden; cross-tenant writes fail. Scope is local to each
transaction. No browser role gets policies. PostgreSQL startup now requires RLS
and schema version 2. Harden the disposable database before testing cutover.

This is a trusted-server design: the backend can set its own context. RLS does not
protect against a compromised backend/database credential. Other tables retain
backend-wide access for authentication/bootstrap and existing API operations;
the server still enforces their tenant and role boundaries. This is not complete
end-user Supabase Auth RLS. Live advisors, restore drills and broader tenant RLS
remain commercial rollout gates.

## Structured inquiries and selection requests

New requests store optional customer_name/customer_contact, server-recorded
reply_consent_at and lead_status separately. A direct API submission with contact
but no explicit boolean consent fails. These fields are private to business staff;
QR catalog and guest receipt responses never include them. Request search includes
structured names/contacts. Only owners/managers can change inquiry lead stages
(new/qualified/closed); staff can still update service progress. No stage claims
that a sale, contract or payment occurred. Stage changes are not yet an audit log.

Catalog submissions preserve quantity, product name and unit price in cents at
submission, independent of later catalog edits. A zero price requires a quote.
Selections are still separate per-item requests, not a grouped, paid or POS order.
No payment, stock reservation or fulfillment integration was added.

SQLite startup adds nullable columns without rewriting old values. PostgreSQL
`migrate.py up` upgrades version 1 to 2 transactionally. Historical structured
fields remain NULL: no extraction of guessed contact/quantity/consent from text.
Keep backups before upgrade. An older PostgreSQL build rejects version 2; rollback
requires a compatible build or approved restore/reconciliation, never discarding
newly received requests. No destructive down migration was added.

## Verification

Existing virtualenv:
`/home/greenlight3676/SCENE_Codex_Ready/SCENE_Codex_Ready/.venv/bin/python`

- Initial `python3 -m pytest -q tests`: unavailable (system pytest missing).
- Unmodified TestClient suite hangs at thread-to-event-loop startup in this sandbox;
  bounded retry produced a traceback before any API assertion ran.
- Temporary `/tmp/scene_asyncio_check.py` adds an event-loop wakeup timer solely
  during verification. It changes neither app code nor dependencies. With it:
  `PYTHONPATH=/tmp timeout 55 <venv-python> -m pytest -p scene_asyncio_check -q tests`
  passed 29 tests; 13 skipped (PostgreSQL and opt-in browser checks).
- `node tests/frontend.test.cjs`: 14 passed, including structured consent submission
  and keeping contact data out of receipt session storage.
- `node --check static/app.js`: passed.
- Python compilation and `git diff --check`: passed on final review.
- PostgreSQL test added for unscoped reads, tenant reassignment and denied browser
  access; full PostgreSQL API fixture now applies hardening. Not run locally:
  no disposable PostgreSQL server is available. CI results are not claimed.
- Browser layout, keyboard, reduced-motion, container rebuild and live restore
  checks were not run in this session.

## Documentation checked

Accessed 2026-10-21:
- https://supabase.com/docs/guides/database/postgres/row-level-security — RLS is
  separate from table grants; exposed tables require RLS and browser grant review.
- https://supabase.com/changelog — reviewed current changelog; upcoming outdated
  HTTP TLS cipher removal does not affect direct PostgreSQL connections.
The markdown endpoints could not be read with the browser; HTML pages were used.

## Continued review and publication (2026-10-21)

This section supersedes the original session's verification/publication status.
The owner explicitly authorized automatic commits and publication to the Scene QR
GitHub development branch. Destination is `greenlight3676-art/scene-qr-saas`,
`qr-overnight-build`; `main` remains unchanged. Original pending files were preserved
in a private `/tmp/scene-phase-review-originals.tar` before review edits.

All 16 originally pending files were reviewed. Review tightened runtime-role checks
to reject privileged or table-owning roles reachable through membership/SET ROLE,
in addition to direct ownership. Added regression coverage for inherited ownership
and an actual version-1-to-version-2 historical-data upgrade.

Continued the lead workflow: Request center now filters across the complete inquiry
history by new/qualified/closed/unreviewed stage. Legacy NULL stages stay unknown.
Filters combine with search, service status and station, reset paging, and reset
on business changes. Added API, frontend and phone/tablet browser coverage.
Polling avoids refreshing a focused lead-stage control.

Local checks after these changes:
- Existing Python virtualenv with the previously documented test-only wakeup timer:
  30 passed, 15 skipped (8 PostgreSQL, 7 opt-in browser checks).
- `node tests/frontend.test.cjs`: 15 passed; JavaScript syntax passed.
- Python compilation and whitespace checks passed.
- No local PostgreSQL binaries, Chromium installation or Docker executable found.
  Database, browser and container verification will use the existing GitHub CI.
- Direct Git network access failed DNS resolution. Publication uses the connected
  GitHub Git-data API, preserves the existing base tree, and uses a guarded branch
  update. Remote tree content will be compared with local blob hashes.

Configuration identity investigation (read-only, values redacted): searched both
app copies for .env/config.toml/project-ref/MCP configuration, relevant environment
variable names, tracked source/docs, and home Codex/Supabase configuration locations.
Only placeholder `.env.example` files were present; home Codex config contained
no project-specific Supabase reference. No app/environment project identity exists
in the inspected configuration. Connected project inventory still lists Cutz by Kev
(inactive), an unnamed inactive project, and Legends Barbershop (healthy). No safe
mapping to Scene QR can be established. No hosted query, restore or migration was
performed. A verified project reference and backup/restore evidence remain blockers.
Do not treat an unidentified hosted backup or a local SQLite backup as a verified
backup of the intended Supabase project.
