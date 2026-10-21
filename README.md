# SCENE QR — Live Multi-Business Beta

**SCENE QR turns physical spaces into interactive, branded mobile experiences.** This runnable pilot includes four industry templates and a shared server-backed request queue for customers, staff and business owners. It is a genuine web app with a database, not the old standalone simulation.

### What's working

- Business signup and login; per-business membership access checks.
- Roles: owner (full business management and invites), manager (service and setup), staff (view/update requests).
- Owners can list teammates, change staff/manager roles and revoke business access immediately.
- One-use 24-hour invite links; staff can join using a new email/password or their existing account password.
- Real PNG QR codes generated from random unique tokens. Owners can rotate old QR links if printed signage is lost.
- Guest menu and services, quick-action requests, request cart, server-side validation of every item and request.
- A guest receives a private receipt and can view its updated request status; staff queue checks for updates automatically every ~6.5 seconds.
- Four design templates: restaurant, barbershop, automotive and retail.
- Catalog management, QR station management, visual branding, request and basic scan analytics.
- A responsive phone customer view and premium owner dashboard.
- Automated cross-tenant, role permission, guest status and QR rotation tests.

### Run the beta locally

Requires **Python 3.11+**.

```bash
cd scene-qr-saas
python3 -m pip install -r requirements.txt
SCENE_DEMO=1 python3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/`. For the fictional demo account, sign in with `demo@scene.local` / `SceneDemo2026!`. **Do not publish this demo account or demo mode on the open internet.** The sample businesses, products and prices are fictional and NOT verified TRIO offerings.

To create your own clean workspace instead, stop the server and run in a new directory with a new database path and `SCENE_DEMO=0`:

```bash
SCENE_DB=./my-scene.db SCENE_DEMO=0 python3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --workers 1
```

Select **Start building**, sign up with a business name and industry, then open **QR stations** to get working downloadable codes.

### Test

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest -q tests
node --check static/app.js
```

The tests make their own temporary database. No live services, email provider, Stripe account or API keys are needed for this beta.

### Host for a limited private pilot

Run this app on an HTTPS host with a **persistent mounted volume** for the SQLite file; deploy **one** Uvicorn worker only. Provide environment values:

```text
SCENE_DEMO=0
SCENE_DB=/data/scene.db
SCENE_SECURE_COOKIE=1
SCENE_PUBLIC_URL=https://your-actual-domain.example
```

`SCENE_PUBLIC_URL` must be the URL guests can actually reach from their phone **before** you print QR codes. Do not print codes while pointing at localhost. Put a TLS reverse proxy in front and keep private credentials in the host's environment variables. Never expose the development demo publicly. Back up the mounted SQLite DB, ideally daily and before updates.

Optional Dockerfile is included; a hosting provider must separately configure HTTPS, a persistent disk and a single running instance. Browser cookies are set Secure when `SCENE_SECURE_COOKIE=1`.

### IMPORTANT: limits before charging businesses

This is a **beta for pilots, not a fully operational commercial SaaS**. The current persistence is local SQLite, not Supabase/PostgreSQL. It has no password reset, email verification or email-delivered invites, billing/payment processing, POS integration, inventory sync, confirmed appointments, real kitchen order transmission, true push-based realtime, support dashboard, audit logs, backup scheduler, or production observability. Analytics count page loads rather than unique human scans; they can include refreshes and automated traffic. Rate limiting is memory-only and not shared across workers. Running many application instances against this SQLite file is unsupported. The staff/pilot can submit **requests**, not paid orders.

Before public rollout: migrate to managed PostgreSQL with tenant-scoped RLS and roles; add robust authentication with email verification/recovery and audited invitations; use a durable queue/realtime; load-test and security-audit the guest endpoint; wire Stripe Billing and webhooks (if selling subscriptions); install backups and monitoring; publish proper Terms/Privacy; verify relevant business data and integration availability. Never assume Toast or any other POS permits order creation until separately authorized.

### Folder map

- `server.py`: API, authentication, roles, tenant isolation, QR routes and SQLite storage.
- `static/index.html`: landing, login, dashboard and guest app shell.
- `static/app.js`: fully connected frontend.
- `static/style.css`: visual system and responsive layouts.
- `tests/test_api.py`: automated workflow and abuse tests.
- `SCENE_PLATFORM_BLUEPRINT.md`: long-term architecture and roadmap.
- `DEPLOYMENT_CHECKLIST.md`: checklist before a real merchant pilot.

This is an original implementation inspired by the TRIO video, not a copy of the video creator's code or proprietary assets.

### Task 0 stabilization

See [AUDIT_TASK_0.md](AUDIT_TASK_0.md) for findings, validation limits, and pilot checks.
API responses use `Cache-Control: no-store`. Catalog selections for barber and auto
use service requests and validate the selected product against the business.
Duplicate guest submissions return existing request details only when the caller
supplies the original `x-scene-ticket` receipt and uses the same station. A retry
without that receipt receives HTTP 409; the client key alone is not a receipt.
If the initial response is lost, confirm with staff rather than automatically
submitting a new key, which could create a duplicate request.

These fixes require no database migration or new environment variables. Existing
SQLite data and URLs remain supported. CI is configured in `.github/workflows/ci.yml`;
it must run successfully in a connected repository before merging or deployment.

### Experimental PostgreSQL transition (Task 1)

SQLite remains the default and is preserved. An explicit versioned PostgreSQL
schema and read-only, empty-target SQLite importer are available; see
[POSTGRES_MIGRATION.md](POSTGRES_MIGRATION.md) for environment configuration,
least-privilege grants, backup/import and rollback limits. Install
`requirements-postgres.txt` before opting in with `SCENE_DATABASE_URL`.
Do not cut over production data yet: RLS and full PostgreSQL workflow validation
remain open gates. Mobile queue controls now wrap on small screens with larger
touch targets, retaining the existing visual design.

### Overnight workspace update (2026-10-21)

The application was restored into `scene-qr-saas` from the owner-confirmed local
project; use this directory in place of the older example directory above.
No existing source copy, hosted service or merchant database was changed.

The dashboard now shows full-history request-type totals, per-station activity
and seven daily UTC page-load/request counts. The queue shows at most 250 rows,
prioritizing active requests. Counts include previews, refreshes and automated
traffic; they do not measure unique people or revenue.

Guests can send a question and optional name/contact details to the business's
private staff queue. The form asks for reply consent when contact details are
provided. This is an inquiry capture workflow; it sends no email, SMS or CRM
notification. Authorized business staff can read these messages. Do not submit
sensitive information. Production retention/deletion policy remains open work.

Each successful selection now keeps its own private receipt. Up to 50 receipts
are stored per QR location in browser session storage and restored on refresh
in that tab, when browser storage is available. Closing the tab can lose them;
this is not an account-backed receipt history. If a submission response is lost,
check with staff before retrying to avoid duplicate requests.

Owner-only team controls are under **Team access**. Staff and managers cannot
change membership, and owner access cannot be removed or demoted using these
controls. Revocation is business-specific; other business memberships remain.
These controls use the existing local authentication. Supabase authentication,
verified email, password recovery and an audit history are still pending.

Validation and remaining environment blockers are in
[OVERNIGHT_REPORT.md](OVERNIGHT_REPORT.md). No new packages or migrations are
required. The Docker image now includes the required `storage.py` module;
image building remains to be verified where Docker is available.

### GitHub verification

GitHub Actions runs Python/JavaScript regressions, the full API suite against a
restricted disposable PostgreSQL runtime role, Chromium phone/tablet workflows,
and a production Docker build/startup smoke check. The container test uses
`SCENE_DEMO=0` and an isolated ephemeral database; it does not publish an image
or start a public deployment.

To run browser tests locally with an installed Chromium:

```bash
python3 -m pip install -r requirements-browser.txt
python3 -m playwright install chromium
SCENE_BROWSER_TESTS=1 python3 -m pytest -q tests/test_mobile.py
```

GitHub hosts the source and automated checks. GitHub Pages cannot run this
FastAPI backend; public application hosting still needs an HTTPS service and
persistent storage as described above. Historical local reference screenshots
are excluded from source publication.
