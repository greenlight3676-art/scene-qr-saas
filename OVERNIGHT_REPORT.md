# Overnight development report

Date: 2026-10-21

## Pass 1: source inspection blocked

- Inspected `/home/greenlight3676/scene-qr-saas`, Git status, branches, and the applicable parent `AGENTS.md`.
- Workspace contains no application files, README, tests, dependency manifests, or previous report.
- Git reports branch `qr-overnight-build`, no commits, and no local or remote-tracking branches. A remote is configured, but no fetch or push was performed.
- Located a separate candidate project at `/home/greenlight3676/SCENE_Codex_Ready/SCENE_Codex_Ready`, containing Python source, static assets, tests, and documentation. Its relationship to the intended working copy needs confirmation before import.
- No application changes, package installations, deployments, database operations, or external writes performed.

## Verification

- `git status`: no commits and initially no tracked application files.
- `git branch -a`: no branches listed.
- `git log` and `git ls-tree HEAD`: unavailable because HEAD has no commit.
- Application tests, lint, and production build: blocked by absent application source.

## Remaining work

- Confirm whether to import the candidate local project or use another source.
- Read the confirmed project's instructions and README, inspect implementation, and establish baseline checks.
- Continue priorities from the requested overnight workflow against that baseline.
- Passes 2–4 have not run; repeating development against an empty workspace would not resolve the source blocker.

## Source restored with owner confirmation

Copied the confirmed local project into this workspace, excluding Git metadata,
virtual environments, caches, secrets and runtime databases. The source copy is
unchanged. Used its existing Python environment without installing packages.
Baseline: 20 Python tests passed, 8 optional browser/PostgreSQL tests skipped;
JavaScript syntax and existing frontend regression runner passed. System Python
has no pytest. The first sandboxed suite stalled; the approved external run passed.

## Development pass 1 — request stabilization

- Added a compare-and-set status update to reject a concurrent stale transition.
- Bounded request kind input; overview now uses the full database open count.
- Failed logout keeps the signed-in UI and reports the error; opening another
  guest view cancels the previous receipt poll.
- JavaScript syntax and frontend regression runner passed after changes.
- No schema changes. Remaining passes address staff access, analytics, guest input.

## Development pass 2 — organization team lifecycle

- Added owner-only role changes and membership removal, protected by CSRF,
  tenant checks and owner-membership safeguards. Revocation takes effect on the
  next API call, including existing sessions.
- Team screen now lists members and supports staff/manager role changes and
  access removal with wrapping mobile controls.
- Prevented stale business responses from rendering after a workspace switch;
  clear generated invitation URLs when changing businesses or signing out.
- Verification: 21 Python tests passed, 8 skipped; JS syntax and frontend runner
  passed. A new test initially missed required price input; corrected fixture.
- Supabase auth, verified email, recovery and audit history remain incomplete.
  CODEX_TASKS.md requires an owner-connected Supabase project before opting in;
  none was supplied. Existing local auth remains available, with no new packages.

## Development pass 3 — complete operational analytics

- Request-type totals now aggregate the entire tenant history, independent of the
  250-row queue display. Open requests sort before completed history.
- Added per-station page-load/request counts and seven daily UTC totals, with
  zero-filled dates and accessible table headings on the dashboard.
- Clarified page-load counting and the queue display limit in product copy.
- Verification: 22 Python tests passed, 8 skipped, including a 260-request
  regression proving full-history counts, old open-request visibility and tenant
  isolation. JavaScript syntax passed.
- No migration or external analytics service required; counts are not unique
  people, conversions, paid orders or revenue.

## Development pass 4 — guest inquiries, receipts and final checks

- Added a real guest message/inquiry form with optional name/contact details,
  reply-consent checkbox, client/server input bounds and blank-question rejection.
  Inquiries enter the private staff request queue; no email/SMS is sent.
- Every successful cart selection retains a private receipt; poll all pending
  receipts and restore up to 50 per QR location from tab session storage.
  Contact/message content is not persisted in that browser receipt storage.
- Added consent, inquiry failure, receipt retention and public contact-privacy
  regressions. Failed inquiry submission preserves entered fields.
- Improved auth-dialog keyboard focus and required signup business name.
- Fixed Dockerfile omission of storage.py, which would break server import.
- Cleared stale workspace content during business switches and bound mutation
  paths to the business whose controls were rendered.
- Updated README with accurate functionality, privacy and operational limits.

## Final verification

Used the existing environment at
`/home/greenlight3676/SCENE_Codex_Ready/SCENE_Codex_Ready/.venv/bin/python`.
No package installation was performed.

- `timeout 60 <existing-python> -m pytest -q tests`: **23 passed, 8 skipped**
  (3.67 seconds). API tests explicitly clear the configured application database
  URL so they use disposable SQLite; opt-in test PostgreSQL remains separate.
- `node tests/frontend.test.cjs`: **11 passed**, covering four industries,
  partial failures, duplicate-click protection, all receipts, inquiry consent,
  private receipt storage and failed-form preservation.
- `node --check static/app.js`: passed.
- `python3 -m compileall -q server.py storage.py migrate.py backup.py tests`: passed.
- `git diff --check`: exited successfully, but this unborn repository's imported
  files are all untracked, so it does not verify a tracked implementation diff.
- No separate lint tool or frontend production bundler is configured. This is a
  Python application serving static frontend files.
- Docker executable unavailable: image build not run. The missing module COPY
  was corrected by source inspection only.
- Playwright Python package exists, but its Chromium executable is absent:
  browser/mobile screenshots and keyboard layout verification were not run.
- No disposable PostgreSQL URL configured: PostgreSQL integration tests skipped.
- Existing FastAPI/TestClient dependency emits one deprecation warning about
  httpx; no dependencies changed to suppress it.
- Sandbox API TestClient attempts stalled; one was interrupted and bounded
  retries timed out. The approved external test runs passed. No app/test process
  intentionally remains running.

## Remaining work and blockers

- Supabase project/auth connection is not provided. Per CODEX_TASKS.md, connect
  an owner-authorized project before migrating auth. Email verification,
  password recovery, invite delivery and durable audit history remain open.
- Validate PostgreSQL/RLS and live concurrent workflows on a disposable database.
- Run Chromium mobile/keyboard/reduced-motion checks and build the container in
  an environment with those existing tools available.
- Add durable realtime/delivery, rate limiting, observability and production
  privacy/retention controls before public use.
- Contact inquiries currently live in request messages, accessible to authorized
  business staff. No CRM export, automated reply or email delivery is integrated.
- Requests are not paid orders or confirmed bookings. A lost submission response
  still requires staff confirmation before retrying; no automatic retry added.
- Session-storage receipts are limited to this tab and 50 per QR location. They
  are not permanent account-backed history.
- All restored files remain untracked; no commit, push or deployment was made.

All four focused development passes above are complete. This does not mean all
long-term product priorities or production-readiness requirements are complete.
No destructive migration, production data change, remote fetch/push, external
message or deployment was performed. No secrets were imported.

## Continued development and authorized GitHub publication — 2026-10-21

The owner requested "continue and deploy to github" and confirmed no additional
confirmation is needed. Scope and destination are recorded in config/APPROVALS.md.
The existing public repository `greenlight3676-art/scene-qr-saas` was verified
empty using both the connected GitHub account and read-only Git remote inspection.
This section supersedes the earlier no-publication restriction for code and CI
publication to this repository only; production hosting/data remain separate.

Changes prepared for the initial publication:

- Added Docker build/startup CI with demo mode disabled and an ephemeral DB.
- Added Chromium CI for all mobile workflows, including actual inquiry consent,
  multi-selection receipts, reload recovery, team role changes and revocation.
- Added full API parity checks against a disposable restricted PostgreSQL role.
- Added requirements-browser.txt, secret/runtime exclusions in .dockerignore,
  and ignored historical local screenshot artifacts for source publication.
- Downloaded test Chromium into /tmp using the existing Playwright package.
- Browser verification found a 37px tablet status selector; fixed it to at least
  44px at all widths. Re-run: all 5 browser tests passed in 43.04 seconds.
- Inspected the real 320px dashboard screenshot. Browser assertions verify no
  horizontal overflow at tested widths (320, 390 and 768 pixels), reachable
  controls, no page errors, staff/guest status propagation and private inquiry
  receipt handling. Tests use synthetic fixtures only.
- JavaScript syntax, 11 frontend regressions and Python compilation passed.
- Local Docker and PostgreSQL services remain unavailable; their CI checks must
  complete on GitHub before claiming those checks passed.
- A pre-publication sensitive-pattern scan found no private keys, service tokens
  or credential-bearing URLs apart from explicitly disposable CI fixture URLs.

GitHub source publication does not host the running FastAPI service. GitHub Pages
cannot execute this backend. No paid host or production database is configured.

### Initial GitHub publication result

- Published 38 source/configuration files on main in commit
  a0902690e594dcc927fe9acab20b0211060a8888. Verified every published blob hash
  matches the corresponding local file. No working files were overwritten.
- GitHub run: https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39594656514
- Container build/non-demo startup, browser workflows and regular tests passed.
- PostgreSQL migration CI passed four checks and failed its restricted-role
  check. The fixture's administrative connection plus startup role option did
  not produce the intended restricted identity. Kept the runtime guard intact;
  changed test fixtures to authenticate as actual isolated restricted LOGIN
  roles with an explicitly disposable fixture password. Added assertions for
  both authenticated and effective identities before testing permissions.
- A final non-browser local run passed 23 tests with 10 optional cases skipped;
  the 5 browser cases passed separately. PostgreSQL validation continues in CI.
