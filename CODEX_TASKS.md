# SCENE — Build order for Codex

> Use one manageable pull request per step. Prioritize reliable operations over elaborate visuals.

## Task 0 — Audit + repository foundation (start here)
- Run baseline tests and review security-critical routes for tenant leaks, request validation, CSRF, sessions and QR rotation.
- Fix confirmed defects with regression tests. Set up CI for Python API tests and JS syntax checks.
- Improve module structure only where needed; no redesign or framework migration yet.
- Deliver: concise audit with severity, passing CI, PR explaining changes.

## Task 1 — Managed Postgres migration plan and implementation
- Design tenant-checked SQL schema, migrations and per-tenant role checks. Prefer Postgres; use Supabase only when credentials/project are connected by owner.
- Make migration opt-in through environment config; preserve SQLite beta for local regression testing until replacement is proven.
- Provide migrations, least-privilege access, negative cross-tenant tests and data import/recovery instructions.
- Do not silently drop, overwrite or export current business data.

## Task 2 — Production authentication and staff lifecycle
- Add verified email/password reset and secure invite delivery via supported auth provider; roles/revocation and audit log.
- Make sessions expire properly and protect state-changing endpoints; test access after member removal.
- Keep server-side permissions authoritative.

## Task 3 — Real-time operational queue
- Replace periodic polling with tenant-scoped SSE/websocket or managed realtime where sensible; reconnect safely and support polling fallback.
- Prevent duplicate handling via idempotency/optimistic locking; show clear status on guest phone and staff dashboard.
- Test two browsers/devices against one shared server and blocked cross-tenant subscriptions.

## Task 4 — Owner/platform subscriptions
- Integrate Stripe Billing **only after** owner supplies accounts, plans and webhook secrets securely.
- Add signed webhook verification, deduplication, subscription statuses, failed-payment treatment and server-side entitlement checks.
- Platform admin views must not grant unrestricted tenant customer-data access.
- No charging in demo tests.

## Task 5 — Premium QR customer experience builder
- Dynamic themes, menu/catalog blocks and per-location actions across restaurant, auto, barber and retail templates.
- Print-quality QR with clear labels, bulk export, token rotation and accessible no-animation mode.
- Make the visual design polished, cinematic and very mobile-friendly; avoid requiring a long intro every scan.

## Later, NOT MVP
- 3D restaurant layout, mini-games, AI concierge with trusted data, actual POS orders, payments/split bills and loyalty.
- Gate risky integrations until merchant approval, legal/privacy review and end-to-end verification.

## Acceptance checks for every task
`python3 -m pytest -q tests` and `node --check static/app.js` (if installed); cross-tenant regression; working phone view; updated docs; no credentials in git.
