# Scene QR SaaS tasks

- [x] Inspect workspace and record missing source.
- [x] Restore owner-confirmed application source, excluding secrets/runtime data.
- [x] Read project instructions, source and README; establish baseline checks.
- [x] Pass 1: request transition conflict check and dashboard/session fixes.
- [x] Pass 2: owner-managed staff roles and business access revocation.
- [x] Pass 3: complete-history analytics, station counts and UTC daily activity.
- [x] Pass 4: guest inquiry/contact form, multiple private receipts, accessibility
  improvements and Docker module fix.
- [x] Final available checks: 23 Python tests and 11 frontend tests passed;
  Python compilation and JavaScript syntax passed. See OVERNIGHT_REPORT.md.
- [x] Verify phone/tablet workflows in real Chromium; five browser checks passed.
- [x] Build container and verify non-demo startup in GitHub Actions.
- [x] Run disposable PostgreSQL migration/permission and full API parity checks in CI.
- [ ] Implement and verify database RLS before commercial rollout.
- [ ] Connect owner-authorized Supabase auth; implement verification/recovery,
  invitation delivery and audit history.
- [ ] Complete production realtime, durable abuse protection, observability and
  contact-data retention controls before public rollout.

## Continued development and GitHub publication

- [x] Verify owner authorization and empty GitHub destination.
- [x] Add browser, PostgreSQL API parity and container startup CI jobs.
- [x] Run all five Chromium phone/tablet tests; fix 768px status touch target.
- [x] Verify consent, multiple receipts and team-access UI flows in Chromium.
- [x] Inspect 320px dashboard screenshot and update verification documentation.
- [x] Publish initial application to main; verify all 38 source blob hashes.
- [x] Inspect GitHub Actions results and fix confirmed failures.

- [x] Inspect initial GitHub Actions results; identify restricted-role fixture failure.
- [x] Confirm repaired PostgreSQL migration and full API parity jobs pass.

- [x] All four CI jobs passed on source commit 4e28ae92304a1988fd9d23b797db6e8c8619f567.

## Autonomous development batch — request history and guest selection

- [x] Add tenant-scoped paginated request history, search, status/type/station
  filters and full-history counts; make inquiries easy to find.
- [x] Add mobile guest catalog search/category filters and quantity controls,
  with server-validated quantities and preserved inquiry drafts.
- [x] Add owner-only pending invitation listing and revocation.
- [x] Cover authorization, validation, pagination and phone workflows with tests.
- [x] Publish verified code and inspect all four CI jobs; document remaining gates.

- [x] Verify explicit filter reset and unchanged settings saves in Chromium.
- [x] Verify final interaction-fix commit in GitHub Actions (all four jobs passed).
- [x] Complete the planned feature batch and record remaining production gates.

## Supabase recovery/security, then structured leads/selections (2026-10-21)

- [x] Inspect connected Supabase inventory read-only. No project is unambiguously
  Scene QR; request owner identification. No hosted database was changed.
- [x] Prepare explicit backend-role database hardening with RLS on every app table,
  denied browser-role access, tenant-scoped request writes and receipt-only reads.
  Wire hardened configuration into disposable PostgreSQL CI fixtures.
- [x] Run PostgreSQL RLS/import/API checks in GitHub CI: 8 database and 24 API
  cases passed on source 4c18454 (no local disposable server).
- [ ] Owner identifies Scene QR Supabase project; inspect its recovery/security state,
  prepare a scoped restore/migration preview and obtain required hosted-action approval.
- [x] Add structured inquiry name/contact/consent timestamps, private contact search,
  manager/owner lead stages, and catalog quantity/name/price snapshots.
- [x] Verify API/privacy/authorization and additive SQLite schema preservation:
  29 Python checks passed using the documented sandbox timer workaround;
  14 frontend checks passed; JavaScript syntax and Python compilation passed.
- [x] Verify 7 phone/tablet Chromium workflows in CI, including lead-stage filters.
- [ ] Complete manual keyboard/accessibility review and production backup/restore drill.

See `PHASE_1_2_REPORT.md` for commands, boundaries and unverified gates.

## Review and development-branch publication — 2026-10-21

- [x] Review all 16 pending files; preserve a private local snapshot before edits.
- [x] Confirm GitHub main matches local base; choose existing local branch
  `qr-overnight-build` as the development publication destination.
- [x] Re-run baseline: 29 Python and 14 frontend tests passed; PostgreSQL/browser
  checks skipped locally. Standard TestClient still requires sandbox timer workaround.
- [x] Fix inherited database-role/ownership bypass checks; add PostgreSQL regressions.
- [x] Continue lead workflow with full-history lead-stage filters and regressions.
- [x] Publish reviewed code and verify remote tree and all four GitHub Actions jobs.
- [ ] Identify Scene QR Supabase from configuration and verify a backup before any
  hosted migration. No matching reference found in either app copy or environment.

- [x] Final available local checks: 30 Python tests and 15 frontend tests passed;
  syntax/compilation/whitespace checks passed. 8 PostgreSQL and 7 browser cases
  await GitHub CI; no local tooling was installed.
- [x] Check home Codex/MCP/Supabase config locations without exposing values:
  no project-specific Scene QR Supabase identity exists in inspected config.

- [x] Publish source `2a954f4` to development branch and verify exact tree match.
- [x] Verify initial CI: application, PostgreSQL (8 database + 24 API cases),
  and container jobs passed. Browser job found 2 filter-draft races; 5 cases passed.
- [x] Preserve unapplied request filters during lead-save refreshes; 16 frontend
  tests and syntax/whitespace checks passed locally.
- [x] Publish and verify browser-race correction across all four CI jobs.

Final verified source: `4c1845455d4dcf15972d09933598f3fe1101aca1`.
CI: https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39716306446
All four jobs passed. Follow-up publication updates documentation only. Supabase
project identity and backup evidence remain unverified; no hosted migration ran.

## Autonomous operational improvements — 2026-10-21

- [x] Add tenant/role-protected catalog editing with stable item IDs and preserved snapshots.
- [x] Add station rename/pause/resume without rotating printed QR tokens; preserve receipts.
- [x] Add full-history inquiry-stage and catalog-request quantity analytics.
- [x] Add optional selection notes, accessible controls and reduced-motion scrolling.
- [x] Run local and GitHub API/PostgreSQL/browser/container checks; fix failures.
- [x] Publish verified changes and progress to `qr-overnight-build` only.
- [x] Recheck safe Supabase configuration; no matching reference exists. Hosted work
  remains blocked without verified identity/backup.

Local operations-batch verification: 33 Python checks passed, 17 skipped for
separate PostgreSQL/browser runs; 20 frontend checks, syntax, compilation and
whitespace checks passed. GitHub CI remains pending for this source revision.

Operations source `1f41e1d`: application/PostgreSQL/container CI passed. Both new
browser cases exposed an ambiguous test selector for two default stations; scoped
to the target station ID and queued for complete re-verification (7 existing cases passed).

Operations batch verified on `d1c8386edb756682985534a1aacf134898c9633f`.
All four CI jobs passed: 33 application checks, 20 frontend checks, 8 database
checks, 27 PostgreSQL API checks, 9 Chromium workflows, and container build/startup.
https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39717836606
No hosted database or production deployment changed. Remaining commercial gates
are tracked above; Supabase identity/backup are still unverified.

## Overnight launcher — 2026-10-21

- [x] Save the owner's six-round launcher at `/home/greenlight3676/qr-overnight.sh`,
  mark executable and verify with `bash -n` (passed).
- [ ] Start overnight execution. Blocked: `command -v codex` finds no executable
  in the current PATH. tmux is available; no session was started, no packages
  installed and no automated rounds or pushes were performed by this launcher.

## Supabase CLI link — 2026-10-21

- [x] Record owner-supplied project reference `cwehqnziwabvnzviaqlf` and scoped
  login/link authorization in `config/APPROVALS.md`.
- [ ] Authenticate CLI and link project. No standalone Supabase CLI is installed;
  offline npx failed with ENOTCACHED. Requested `npx supabase login` produced no
  login prompt while waiting for package resolution and was interrupted.
  Linking was not attempted because authentication did not complete.
  No hosted database changes were made.

## Founder’s Test audit — 2026-10-22

- [x] Import and hash-verify six newer remote commits through `6837e31`, preserving
  pending local documents; read Founder lifecycle, CI, Docker and Supabase records.
- [x] Run original baseline: 33 Python checks passed, 17 skipped with documented
  sandbox timer; JavaScript checks passed. Reproduce the new Founder gate failure.
- [x] Fix reproduced ID overflow, uncertain-delivery duplicates, stale private UI
  and Founder assertion regressions; local 38 Python / 24 JS checks pass.
- [x] Record requirement-level PASS/FAIL/BLOCKED evidence in FOUNDER_TEST_REPORT.md;
  commercial launch fails. Add CI browser lost-response and container restart checks.
- [x] Publish source `1266d139` and inspect run 39723075114: all four jobs pass;
  38 Python, 24 JS, eight PostgreSQL security/migration, 32 PostgreSQL API, ten
  Chromium workflows and expanded container/restart checks verified.
- [x] Publish final evidence/report; launch remains FAIL with explicit unfinished gates.

## Secure PostgreSQL/Supabase preparation — 2026-10-22

- [x] Read connection, migration, security, storage, authentication and test code.
- [x] Establish baseline: existing venv, sandbox timer; 38 passed, 18 skipped.
- [x] Verify additive migrations through version 4, import and expanded tenant RLS in disposable CI PostgreSQL 16 and 17 (see final completion report).
- [x] Verify managed-auth negative tests, session revocation and private audit records: final local suite 43 passed; 19 PostgreSQL/browser checks skipped.
- [x] Publish verified development source to qr-overnight-build and inspect CI; final source be002730.
- [ ] Hosted backup/restore drill and restricted-role credential provisioning.
- [x] Implement managed identity provisioning, signup/invite onboarding and recovery UI; real hosted identities remain a staging gate.
- [ ] Verify hosted email confirmation, delivery and password recovery in staging.

See SECURITY_INTEGRATION_REPORT.md for the exact integration boundary.

Historical security preparation follow-up: 11 managed-auth/storage checks passed.
The complete backend mission below supersedes the earlier publication/CI blocker:
Git DNS still fails, but the connected GitHub integration published verified trees
and disposable PostgreSQL rehearsals passed. No hosted production changes occurred.

## Complete backend mission — 2026-10-22

- [x] Inspect repository, latest local/remote commit, required documents and baseline.
  Baseline: 45 passed, 19 skipped; default Python lacks pytest; reused existing venv.
- [x] Reverify Supabase read-only: expected project healthy, us-east-1, public tables
  empty; security advisor no findings (does not validate absent app schema).
- [x] Implement managed registration/verification/onboarding/recovery, revocation
  before external password updates, managed invite acceptance and logout-all.
- [x] Implement additive v4 schema, locations, QR content/destinations, guest sessions,
  durable rate limits, consent-backed customers/redaction, reporting and audit events.
- [x] Implement Stripe test-mode checkout/portal, signature verification, transactional
  dedupe, canonical subscription reconciliation and server-side request entitlements.
- [x] Implement invitation outbox, explicit/dry-run worker, bounded retries, revoked
  invitation checks, production env validation, readiness and redacted request logs.
- [x] Complete final unit/API/contracts/concurrency checks and disposable PostgreSQL CI:
  64 application tests, 11 PostgreSQL 17 migration/RLS/restore checks and 52 restricted-role API checks passed; exact skips in completion report.
- [x] Publish logical batches with exact local/remote tree verification; source be002730.
- [ ] Hosted restore/security/TLS/SMTP/Stripe staging acceptance and deployment approval.

See BACKEND_COMPLETION_REPORT.md for evidence, limitations and release decision.

## Backend-only follow-up — 2026-10-24

- [x] Sync latest qr-overnight-build source 4db17ad with verified Git object/tree
  hashes through the connected integration after native Git DNS failure.
- [x] Read hosted v4/RLS applied status and archived SQL; do not reapply initial
  migration, create hosting, deploy or alter hosted data.
- [x] Establish local baseline: 64 passed, 21 skipped; JavaScript syntax passed.
- [x] Fix bound-identity email-flow verification, webhook worker execution and
  malformed payload/retry handling, and report integer bounds; add regressions.
- [x] Publish source 704911b with exact tree match; all four CI jobs passed in
  run 40068688294. Local/CI Python: 70 passed, 21 skipped; PostgreSQL: 11 database
  checks and 58 API checks passed (one SQLite-only skip); browser: 10 passed.
- [ ] Credentialed connection, real Auth/email and Stripe provider acceptance.

No credentials were provisioned and no provider checks are represented as passed
by synthetic tests. Current hosted SQL evidence comes from SUPABASE_CONNECTION.md.

## Ordered acceptance work — Stripe excluded

- [x] Sync newer workflow/restore commits through 9d892ee before edits.
- [x] Verify hosted v4 and NOLOGIN/restricted role flags with read-only SQL;
  verify FORGE Free plan and inspect current backup documentation.
- [x] Add offline-default, read-only DB/Auth preflight with secret-safe output:
  seven new tests passed. No mail/Stripe/migration/deploy action exists in this tool.
- [x] Prepare code-based signup/recovery email template drafts and ordered
  BACKEND_ACCEPTANCE_TASKS.md with concrete prerequisites and evidence boundaries.
- [x] Rerun existing Auth, mail, two-business/restored API and backup tests:
  18 passed using synthetic/disposable data; not provider acceptance.
- [ ] Provision private runtime login and verify actual TLS/pooler connection:
  blocked by private credential destination and runtime connection configuration.
- [ ] Configure Auth/email and perform approved mailbox/session acceptance:
  blocked by origin, recipient, sender/SMTP credentials and configuration access.
- [ ] Export hosted backup and restore separately: blocked by private archive
  location, dump credentials, client tools and an approved isolated restore target.

No Stripe action, hosting, deployment, installation, initial migration or external
email was performed. The owner's requested origin/recipient/credential location
details are pending. See BACKEND_ACCEPTANCE_TASKS.md for the ordered handoff.
