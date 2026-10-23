# Scene QR backend completion report

Date: 2026-10-22. Local development and isolated tests only. No production data,
hosted schema, paid resources, customer messages, real Stripe charges or deployment
were changed. SQLite beta stays the default; new tables/columns are additive.

## Delivered code

| Area | Implemented behavior | Verification boundary |
| --- | --- | --- |
| Authentication | Supabase server password login; email-code/hash verification bound to an HttpOnly browser flow; verified subject provisioning; signup creates owner business only after verification; verified invitation join; addressed invites; logout/all; recovery-only sessions with CSRF; local revocation committed before external password update | Synthetic provider contracts locally; real SMTP/provider flows await staging |
| Sessions/roles | Opaque hashed session IDs, secure HttpOnly SameSite cookies, CSRF/origin checks, absolute access-token lifetime, provider revalidation outside DB locks, reset revocation cutoff; owner/manager/staff enforced per private operation | Unit/API negative tests; no refresh-token storage (re-login on expiry) |
| Database | Transactional v1→v4 upgrades; additive SQLite compatibility; read-only snapshot importer preserves IDs and optional new tables in dependency order; restricted runtime-role validation and remote verified TLS; tenant RLS on business data; anonymous Data API denied | Disposable PostgreSQL rehearsal required; hosted changes not authorized |
| Organizations | Existing business is the tenant/organization; authenticated users create/list their own organizations, owner membership created server-side | Cross-tenant API contracts |
| Locations/QR | Multiple tenant locations; active states; unique high-entropy station codes; rotate/pause/resume; menu/service/info destinations; escaped dynamic text; two-hour hashed guest sessions bound to tenant/station | Lifecycle/negative tests; no arbitrary external redirects |
| Guests/requests | Public business/menu APIs, real database-backed requests, item/quantity/consent validation, private receipts, idempotency checks, status transition conflicts and durable abuse buckets | Existing and expanded end-to-end request flows; requests remain unpaid staff requests |
| Customers | Consent-backed private customer records; tenant/role-scoped paginated list/create; owner redaction updates associated structured inquiry fields | Anonymous/foreign tenant denial, consent and redaction contracts |
| Dashboard | Locations/QR/catalog/staff/settings/request history, filtering, analytics, period reports and owner audit history | Existing UI preserved; new backend contracts tested separately |
| Audit | Transactional request/status/lead/member/catalog/QR/settings/invite/business/session/billing/provider-acceptance actions; IDs/action/time only | Runtime append-only RLS/grants; database administrators remain trusted |
| Billing | Stripe test-mode checkout/portal; server price mapping; raw-body HMAC timestamp/signature verification and rotation; event-id/payload dedupe; canonical subscription reads; fail-closed active/trialing unexpired entitlements | Synthetic signatures and provider results only; no real charges or live-key support |
| Email | Durable addressed-invitation outbox; explicit worker, dry-run default; stable provider idempotency keys, bounded retries, revoked/used/expired invite checks; owner status API | Injected transports; provider acceptance is not proof of inbox delivery |
| Operations | Environment/host/HTTPS validation, explicit production gates, `/healthz` liveness and `/readyz` DB/schema readiness, bounded request bodies including streaming, sanitized validation, request IDs and route-template logs, threadpool-compatible blocking endpoints, Docker and CI updates | Local checks and CI evidence below; monitoring provider and restore policy need operator configuration |

## API additions

- Auth: `/api/auth/verify`, `/api/auth/recovery-session`,
  `/api/auth/complete-recovery`, `/api/auth/accept-invite`, `/api/auth/logout-all`.
  Existing signup/login/join/recover/reset endpoints remain compatible for local
  beta mode; managed mode verifies identity, never trusts roles in user metadata.
- `/api/organizations` GET/POST; `/api/businesses/{slug}` public GET.
- `/api/admin/{slug}/locations` GET/POST and `/{id}` PATCH;
  `/api/admin/{slug}/qr` GET and `/{station_id}` PATCH;
  `/api/q/{token}/session` POST (send `x-scene-guest` on submissions).
- `/api/admin/{slug}/customers` GET/POST and `/{id}/redact` POST;
  `/api/admin/{slug}/reports` GET; `/audit` GET; `/mail` GET.
- `/api/admin/{slug}/billing` GET; `/billing/checkout` POST requires stable
  `Idempotency-Key` and a server-configured plan name; `/billing/portal` POST.
- `/api/billing/webhook` POST accepts signed **test-mode snapshot events** only.
  Subscribe to `customer.subscription.*`, `invoice.paid`, `invoice.payment_failed`.
  Redirect success never grants access. Unknown/unbound customers are ignored.

## Supabase verification and hosted boundary

Connected read-only inspection returned project `cwehqnziwabvnzviaqlf`,
`Scene QR SaaS`, `us-east-1`, ACTIVE_HEALTHY, PostgreSQL 17.11, expected
organization ID `yrgfwtjoxfdpslqeyjtt` (FORGE from prior verified record).
Public application table inventory is empty. Security advisors returned no lints.
An empty project has no app policy to validate. No migration or production write
was performed. Hosted backup entitlement/restore, credentials, TLS, schema/RLS,
Auth confirmation settings, SMTP, redirect allowlist and end-to-end staging
acceptance remain unverified. Never use owner credentials as runtime credentials.

## Production configuration and rollout

Use `.env.example` for placeholder-only configuration. `SCENE_ENV=production`
requires no demo mode, secure cookies, managed Supabase Auth, PostgreSQL, a valid
HTTPS public origin, explicit trusted hosts, guest sessions and subscription
checks. Defaults preserve the SQLite beta. The container disables raw Uvicorn
access logs; custom logs omit actual QR paths, query strings and request bodies.
Configure an ingress body/time limit, restrict forwarded headers to the actual
proxy, and supply private logging/alerting destinations before deployment.

Auth email templates must present `{{ .Token }}` as a code entered at
`/auth/confirm` in the initiating browser. Alternatively use a token-hash link
in the fragment `https://YOUR_HOST/auth/confirm#token_hash={{ .TokenHash }}`.
Use separate signup/recovery templates with the correct provider verification
type. Configure Supabase Site URL and exact redirect allowlist, verified SMTP
sender and appropriate CAPTCHA/rate settings. No email template/config was
changed remotely. Existing local users require a separately reviewed identity
migration; matching email alone never links a legacy account.

Invitation creation with an email queues a draft. Review the owner `/mail` API,
record explicit scoped sending authorization in `config/APPROVALS.md`, configure
a verified sender/Resend key, and only then run an approved worker with
`SCENE_MAIL_SEND=1 python mail_delivery.py --send`. Default invocation is a dry run.
No worker/scheduler was started. Retry stops before the 24-hour provider
idempotency window; ambiguous old attempts require manual review. Sender DNS,
provider delivery/bounce monitoring and scheduling remain operator setup.

Billing requires owner-supplied test credentials, reviewed API version, approved
plan/price mapping and test webhook secrets. No prices/currencies or commercial
terms are invented. Live billing is deliberately refused until a separately
approved release; the current backend can be staged with synthetic/test-mode
subscriptions and cannot charge real customers.

## Data and security limitations

- Private business data (requests, catalog, stations, scans, invites, audit,
  locations, customers, guest sessions, subscriptions, outbox) has tenant/capability
  RLS. Authentication/membership/organization bootstrap tables still need trusted
  backend lookups; they are not browser APIs. The backend role can set transaction
  capabilities and is trusted to authenticate/authorize. Never expose it to clients.
- Provider access tokens, temporary verification flows and queued invitation links
  remain in private backend database storage/backups; enforce storage encryption,
  access controls, backup retention and incident rotation. No custom cryptography
  or unreviewed refresh-token mechanism was introduced.
- Local auth remains a beta compatibility path; production validation requires
  managed auth. Recovery/signup intentionally require the initiating browser.
- Reset failures after revocation require a fresh recovery attempt; old local
  sessions stay revoked. In-flight already-authorized work may finish. Provider
  global token revocation/refresh behavior needs staging verification.
- Audit append-only restrictions apply to runtime, not administrators. There is
  no external tamper-proof audit archive. Redaction covers structured fields;
  free-text inquiry messages and retained backups require a privacy review.
- PostgreSQL transaction advisory serialization preserves correctness; capacity
  and multi-instance load targets have not been established. Guest queues use
  polling; no POS, inventory, paid guest orders or confirmed reservations exist.
- Rate buckets are shared/durable but fixed-window; apply edge/DDoS controls and
  retention/monitoring at ingress. Client IP trust is a deployment responsibility.

## Tests and evidence

Baseline: 45 passed, 19 skipped, using the existing Python environment and sandbox
asyncio timer workaround. Default `python3` lacks pytest. No packages installed.
The initial expanded run found an outbox test consuming another tenant's old
synthetic message; scoped the worker test to its tenant. Focused follow-up passed.
Final local and GitHub outcomes are recorded below after execution.

## GitHub and readiness

Git DNS remains unavailable in this sandbox. The connected GitHub read now works
and found remote head `4d91bb4`; the previous local `46d70a9` had not been
published. Publication uses a reviewed connector tree/commit and a non-forced,
expected-head branch update; no main or production deployment changes.

Release decision: **NOT approved for production deployment** until the hosted
backup/restore/security/credential and provider staging checks above pass.
Locally implemented behavior is distinguished from real provider integration;
passing synthetic tests is not a production-readiness attestation.

## Sources checked (2026-10-22)

- Supabase Auth OpenAPI: https://raw.githubusercontent.com/supabase/auth/master/openapi.yaml
  — `/signup`, `/verify`, `/recover`, `/user`, password tokens and verified identity contract.
- https://supabase.com/docs/guides/auth/passwords — confirmation and recovery configuration.
- https://docs.stripe.com/webhooks — signatures, raw-body verification, snapshot events.
- https://docs.stripe.com/billing/subscriptions/webhooks — subscription/invoice lifecycle.
- https://docs.stripe.com/api/checkout/sessions/create — server-created checkout sessions.
- https://resend.com/docs/api-reference/emails/send-email — provider email API/idempotency.

First full expanded local run after the outbox fixture fix: **60 passed,
20 skipped** (10 disposable PostgreSQL checks, 10 browser workflows). Existing
frontend runner and JS syntax passed; Python compilation/whitespace checks passed.
The suite uses isolated synthetic databases. Follow-up checks and CI will be
recorded with their actual outcomes; no skipped check is counted as passed.

Published integration source `a06d3e2` with exact local/remote tree match. CI run
39891619290 passed application and container/restart jobs and all **10 PostgreSQL
migration/RLS/import tests**. Restricted PostgreSQL API parity exposed one real
bug: a QR/location join ran before setting tenant scope, so RLS correctly hid the
location and made a valid QR appear unavailable. Corrected resolution to validate
the token first, set transaction-local tenant scope, then verify active location.
This keeps RLS strict; no policy was weakened. Added clearer HTTP assertions,
concurrent transition checks and a separate disposable dump/restore drill.

Follow-up local checks: 15 auth/backend/operations cases passed after the QR lookup
correction; concurrent request completion allows one winner and returns a conflict
for the other. Managed production startup/signup/login additionally verify the
provider public settings require email confirmation. Hosted migration inventory
is also empty. The CI dump/restore drill reuses the existing PostgreSQL container
tools; no local package installation or hosted test database is required.
See OPERATIONS_RUNBOOK.md for staging, backup/restore and incident procedures.
