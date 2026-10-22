# Scene QR Founder’s Test — 2026-10-22

**Verdict: FAIL for commercial launch. Do not launch or charge businesses yet.**
Core beta workflows are tested with synthetic local/CI data. No payment, hosted
Supabase authentication, production deployment or real merchant workflow is verified.
PASS means only the explicitly stated test scope; BLOCKED is not a pass.

## Reviewed source and inherited work

Started with local `a6b4a92`; GitHub had six newer commits through `6837e31`.
Imported their exact blob/commit hashes and final tree before editing, preserving
pending local TASKS/approval records. Reviewed AGENTS.md, README.md, CODEX_TASKS.md,
DEPLOYMENT_CHECKLIST.md, SUPABASE_CONNECTION.md, API/frontend, storage/schema/RLS,
backup/import code, tests, Dockerfile and CI. No prior Founder report existed.

The existing Founder test was **not green**. Reproduced its short receipt-token
assertion failure locally. GitHub run [39721432687](https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39721432687)
failed application and PostgreSQL API jobs; browser and container jobs passed.
A short token correctly returns 401; a full-length incorrect token returns 404.
The corrected test checks both without weakening authentication.

## Critical customer requirements

| Requirement | Result | Evidence and boundary |
| --- | --- | --- |
| Business signup, login/logout, session expiry, CSRF and origin checks | PASS | `test_signup_login_logout_and_validation`, `test_private_cache_session_expiry_and_membership_revocation`, origin tests; local SQLite. Managed auth is a separate failing gate below. |
| Owner dashboard, branding and catalog management | PASS | API settings, catalog-edit, snapshot and role regressions; server persistence rather than visual-only forms. Browser verification pending CI. |
| Create, rename, pause/resume and rotate QR locations; generate PNG | PASS | Station and Founder API tests check live tokens, PNG signature, unavailable/rotated tokens and surviving private receipts. PNG decoding/printed signs on physical phones remains blocked. |
| Real mobile customer scan over cellular/HTTPS | BLOCKED | No public staging URL, printed sign or physical phones in this environment. Chromium viewport checks do not establish this requirement. |
| Browse services, quantities, notes and submit inquiries/requests | PASS | Four-industry JS tests and catalog/quantity/consent API checks. These are unpaid requests requiring staff confirmation. |
| Lead arrives only in the correct business queue | PASS | Founder lifecycle and structured-inquiry tests check contact search, lead qualification, other-business denial and public response privacy. |
| Staff/manager/owner permissions and status updates | PASS | Invitation, one-use/revoked invite, member role/revocation and forward-only transition regressions. No email invitation delivery or audit log is implemented. |
| Accurate operational analytics and input validation | PASS | Full-history, UTC daily, station, quantity/snapshot and lead-stage tests. New resource-ID validation checks all nine numeric route variants against zero, negative and overflowing IDs. Counts are page loads/requests, never revenue or unique customers. |
| Interrupted submissions and refresh safety | PASS | JS regression reproduces lost-response duplicate risk and verifies a per-QR delivery lock; malformed/5xx responses cannot claim success; confirmed validation errors permit correction. Lock persists in session storage when available. Browser committed-but-lost-response/refresh check awaits CI. Manual staff reconciliation is still required; no exactly-once/offline guarantee. |
| Persistence across database backup/restore and process restart | BLOCKED | Local synthetic SQLite backup/restore and WAL tests pass. New Docker account/request/restart check awaits CI. Hosted restore/recovery and volume replacement remain untested. |
| Cross-business authorization and customer privacy | PASS | API negative tenant/resource/role tests and private receipt checks; new JS regression clears cached contacts/invites when workspace access is denied. This is application-level evidence, not proof of full database tenant isolation. |
| WCAG 2.2 AA and full mobile/keyboard accessibility | BLOCKED | Existing focus/reduced-motion rules and browser keyboard/layout checks reviewed. No full screen-reader/contrast audit, physical device review or formal conformance test completed. |
| Production latency, concurrency and abuse resistance | FAIL | No production load test; synchronous DB/password work runs inside async handlers, PostgreSQL uses a global transaction lock, and rate limits are process-memory only. Do not infer capacity from test duration. |
| Verified email, password recovery, managed Supabase Auth and audit history | FAIL | Not implemented; current authentication is local application sessions/passwords. |
| Commercial subscriptions, payments and POS/order fulfillment | FAIL | No Stripe/webhooks/entitlements or authorized POS integration. No real payment/booking/order claim permitted. |
| Hosted Supabase migration, restricted roles and complete tenant RLS | BLOCKED | SUPABASE_CONNECTION.md records project identity `cwehqnziwabvnzviaqlf`; linking/migration/auth are separate. Disposable database tests await CI. Only requests have tenant/receipt DB predicates; other backend policies are broad, so full tenant RLS is unfinished. No hosted writes performed. |
| Production hosting, HTTPS, backup schedule, monitoring and privacy operations | BLOCKED | No production deployment or live restore drill tested. Retention/export/deletion, operational alerts and venue acceptance remain launch gates. |

## Confirmed defects fixed

1. **High — duplicate delivery after lost responses.** The old client generated a
   new key on every retry. Failed network responses could follow committed writes.
   Record delivery uncertainty before sending, stop further cart items on ambiguous
   failure, refuse automatic resubmission, preserve the marker across tab refresh,
   and require an explicit staff-check acknowledgement to resume. Store no inquiry
   contact/message fields in that marker. Browser storage denial/new tabs remain
   limitations; this does not replace server-side recoverable idempotency.
2. **Medium — false success on unreadable/missing receipt responses.** Reject
   malformed JSON/receipt payloads and preserve uncertainty rather than claim receipt.
3. **Medium — revoked workspace retains private UI data.** A denied workspace load
   clears cached business, request page, drafts and invitation URL and replaces
   private content with an access message. Already-seen data cannot be recalled.
4. **Medium — numeric ID overflow causes server errors.** Bound resource path IDs
   to positive signed 64-bit values before querying either database.
5. **CI regression — invalid Founder assertion.** Correct the 401/404 distinction
   and test both short and well-shaped wrong receipt tokens.
6. Remove unsupported landing claims about rewards/bookings and literal realtime;
   non-demo startup labels its CTA as QR creation instead of a seeded demo.

## Verification performed in this workspace

- System `python3 -m pytest -q tests`: BLOCKED (`No module named pytest`).
- Existing environment: `/home/greenlight3676/SCENE_Codex_Ready/SCENE_Codex_Ready/.venv/bin/python`.
- Unmodified TestClient run stalled under sandbox thread wakeup restrictions.
  Used existing `/tmp/scene_asyncio_check.py` timer workaround **only in the test
  launcher**, not application/CI code. Command: `timeout -k 3 60 <python> -c
  "exec(open('/tmp/scene_asyncio_check.py').read()); import pytest;
  raise SystemExit(pytest.main(['-q','tests']))"`.
- Final local Python run: **38 passed, 18 skipped**, one upstream TestClient
  deprecation warning. Skips: eight disposable PostgreSQL and ten browser cases.
- `node tests/frontend.test.cjs`: **24 passed**; `node --check static/app.js`: passed.
- Python compilation and `git diff --check`: passed. Runner `bash -n`: passed;
  runner was reviewed, not executed or scheduled.
- Explicit `pytest -q tests/test_postgres.py`: **8 skipped**, no disposable server.
- Explicit `SCENE_BROWSER_TESTS=1 ... pytest -q tests/test_mobile.py -x`: **BLOCKED**
  before browser startup, socket creation denied (`PermissionError: Operation not
  permitted`). No browser packages or tools installed.
- Docker executable is unavailable locally; image build/restart test delegated
  to the existing GitHub Actions environment, not asserted locally.

## CI and publication evidence

Pending publication of this audit. Required jobs: application + JS, disposable
PostgreSQL migration/RLS/API + explicit Founder gate, Chromium workflows, Docker
build/non-demo guest workflow + restart persistence. Browser artifacts contain
synthetic test data only and expire after seven days. Record exact source commit,
run URL and actual job conclusions here after checking GitHub.

## Launch decision and next work

The first paying customer still lacks account recovery, billing, verified staging
operations and a physical end-to-end acceptance run. Prioritize managed auth and
audit history, production abuse/retention controls, approved staging database
security and restore rehearsal, then HTTPS/two-phone venue acceptance and billing.
Keep development on `qr-overnight-build`; no production or hosted schema changes
were part of this audit. Green CI alone cannot turn the above FAIL/BLOCKED gates
into a commercial launch approval.
