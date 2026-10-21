# Task 0 — audit and stabilization

Scope: existing FastAPI/SQLite beta, one shared platform, no framework/schema/design
migration, merchant connection, public deployment, or payments.

## Findings and changes

| Severity | Finding | Resolution |
| --- | --- | --- |
| Medium | Origin validation compared host only, accepted a different scheme, and could throw on malformed URLs. | Compare scheme, normalized host and port; reject malformed/null origins and cross-site Fetch Metadata when Origin is absent. Private mutations still require the session CSRF token. |
| Medium | Knowing a guest client key plus a public station token disclosed an existing request ID/status, including requests at another station in that business. | Existing request details now require the private receipt and original station. Otherwise return a generic 409 without request details. |
| Medium | Login/join strings lacked length limits; whitespace-only product/business names could pass validation before being stripped. | Bound credential/invite inputs and trim names before field length validation. |
| Medium | Barber/auto cart submissions always used the unsupported `order` kind. | Submit catalog selections as `service` for those industries; validate every supplied product ID against the active tenant catalog and retain its authoritative name. |
| Medium | Partial cart failures left successful selections available to resend; rapid clicks could create concurrent submissions with different keys. | Remove successfully submitted selections and guard concurrent action/cart submissions. |
| Low | Sensitive API responses lacked explicit cache policy. | All API responses use `Cache-Control: no-store`, including errors. |

All private routes reviewed use a server-side session and membership grant; setup
writes restrict owner/manager roles, and invitations/member lists restrict owners.
Resource mutations scope IDs by business. Public QR responses contain catalog and
station labels, not private queues/members. QR resolution requires an active
station and current token. No confirmed cross-business route leak was found in
this review. This is a focused code review, not a full penetration test.

Added API regressions cover the fixes, cross-tenant resource IDs, revoked membership,
expired sessions, and unsupported/foreign catalog products. Existing workflow,
CSRF, staff-role, invitation reuse and QR rotation tests remain.

## Validation and repository state

- Baseline `python3 -m pytest -q tests`: blocked, `No module named pytest`.
- Dependency installation: blocked, `No module named pip`; venv bootstrap also
  lacks ensurepip, and bootstrap download failed DNS resolution. No API test pass
  is claimed, either before or after the changes.
- Baseline and final `node --check static/app.js`: passed.
- Final `python3 -m compileall -q server.py tests`: passed (syntax only).
- `node --test tests/frontend.test.cjs`: passed; exercises four industry carts,
  partial failure recovery, and concurrent submission prevention using mocked
  HTTP responses. It is not a browser/device check.
- Existing GitHub Actions CI already installs Python dependencies, runs API tests,
  and checks JS syntax. Extended it to run guest submission regressions.
- This workspace has no usable Git repository/remote (`git status` reports
  "not a git repository"). No commit, branch, PR, or hosted CI run was created.
- No migration, data deletion, new environment variables, or runtime DB added.

## Next checks before merge/pilot

1. In an environment with Python 3.11+ and pip, install both requirement files,
   run `python3 -m pytest -q tests`, `node --check static/app.js`, and
   `node --test tests/frontend.test.cjs`. Resolve any API failures before merge.
2. Connect a private repository, run CI, and open one scoped Task 0 PR. Suggested
   title: "Stabilize tenant-safe guest submissions and origin validation". This
   report supplies change scope, rationale, validation and remaining limitations.
3. Locally scan/preview each template, add a sample catalog selection, submit a
   service request, and complete it from staff. Verify receipt status updates.
4. On two phones, verify cart double taps, partial network failure recovery,
   restricted staff setup access, business switching, and QR rotation (old scan,
   redirect, PNG and submission URLs must stop working). Verify keyboard and
   reduced-motion behavior; no visual changes were made in this task.

## Remaining risks and production blockers

- Python API suite and real browser/phone verification remain outstanding here.
- Memory-only rate limits are single-process, can be reset by capacity clearing,
  and are not sufficient for public abuse protection. Request bodies have no
  transport-level size cap; add a reverse-proxy limit before a pilot.
- If the first submission response is lost, its private receipt cannot be
  recovered with the client key alone. A retry with that key safely returns 409;
  confirm with staff before creating another request. Frontend in-flight guards
  do not provide durable network retry/idempotency or cross-tab coordination.
- Status serialization relies on the existing single-process DB lock. Keep one
  worker/instance; distributed concurrency belongs to subsequent phases.
- Session expiry and membership checks exist, but verified email, password reset,
  user revocation UI, session cleanup and audit trails remain Task 2 work.
- Task 1 next: an opt-in managed Postgres migration plan with tenant constraints,
  reversible migrations, import/recovery instructions and SQLite compatibility.
- Follow DEPLOYMENT_CHECKLIST.md: HTTPS, secure cookies, demo off, persistent disk,
  backups/restoration, privacy controls, monitoring and real owner authorization.
  Configure trusted proxy/host handling so origin and generated URLs reflect the
  actual HTTPS site; do not trust arbitrary forwarded headers.
- Billing, POS, payments, confirmed reservations and kitchen delivery remain
  unimplemented. Demo offerings are fictional; all submissions are staff requests.
