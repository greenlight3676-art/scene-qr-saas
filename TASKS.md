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
