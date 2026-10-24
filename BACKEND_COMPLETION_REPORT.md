# Scene QR backend completion report

## Current backend-only follow-up — 2026-10-24

Synced branch source `4db17ad038cc01c6ab43fe8fe5a2c68375d7296f` before edits.
Native Git pull failed DNS; the connected GitHub integration retrieved the latest
commit/files, verified Git object hashes and the exact tree, then fast-forwarded
the local branch. The hosted status below supersedes the historical empty-project
observations in this report.

**Recorded hosted verification:** SUPABASE_CONNECTION.md now records applied
schema v4, 21 RLS-protected tables, least-privilege NOLOGIN `scene_runtime`, and
rollback-only tenant isolation/anonymous-denial SQL checks. This follow-up reviewed
the archived SQL and status; it did not repeat those hosted SQL fixture checks or
reapply any migration. Fresh read-only connector checks confirmed ACTIVE_HEALTHY,
PostgreSQL 17.11, the recorded migration entry, 21 public tables with RLS enabled
and zero security-advisor lints. Table inventory reports only the schema metadata
row; application tables are empty. These metadata checks do not exercise the
credentialed application connection. SQLite stays available. No new SQL migration
is needed for these fixes.

Backend fixes:

- Provider-verified subject/email must match the initiating flow even if that
  subject already has an identity binding. Mismatched signup/recovery hashes
  cannot create an organization or issue a session. Revocation is rechecked under
  the provisioning transaction after the external identity read.
- Stripe raw-body verification/reconciliation runs in the worker threadpool,
  keeping blocking database/provider work off the ASGI event loop. Transactional
  event deduplication and tenant capability scopes remain intact.
- Invalid signed customer objects and out-of-range timestamps return 400 without
  consuming the event ID. Malformed canonical subscription responses return 503,
  roll back projection/dedupe and allow a retry. Report time bounds reject values
  outside the database's signed 64-bit integer range with 422.

**Credential-blocked checks:** real backend PostgreSQL connection with restricted
LOGIN credentials and verified TLS/pooler settings; live Supabase signup/email
verification/login/recovery and session acceptance; SMTP/invitation delivery;
Stripe test-account checkout/portal/webhook acceptance. Synthetic provider tests
do not establish these results. Hosted backup/restore, capacity/monitoring and
privacy acceptance also remain outstanding. No hosting was created, no deployment
or hosted write was attempted, and no emails or charges were initiated.

Baseline: 64 local Python tests passed; 21 skipped (11 PostgreSQL and 10 browser
cases require separate CI jobs). Existing JavaScript syntax passed. Final local
and CI results for this follow-up are recorded after execution below.

References reviewed: [Supabase email templates](https://supabase.com/docs/guides/auth/auth-email-templates)
defines OTP/token-hash proofs used by these flows. Provider settings were not
changed. The Supabase changelog markdown fetch failed; no new Supabase API or
schema feature was introduced.

## Historical implementation and verification — 2026-10-22

Date: 2026-10-22. Local development and isolated tests only. No production data,
hosted schema, paid resources, customer messages, real Stripe charges or deployment
were changed. SQLite beta stays the default; new tables/columns are additive.

## Delivered code

| Area | Implemented behavior | Verification boundary |
| --- | --- | --- |
| Authentication | Supabase server password login; email-code/hash verification bound to an HttpOnly browser flow; verified subject provisioning; signup creates owner business only after verification; verified invitation join; addressed invites; logout/all; recovery-only sessions with CSRF; local revocation committed before external password update | Synthetic provider contracts locally; real SMTP/provider flows await staging |
| Sessions/roles | Opaque hashed session IDs, secure HttpOnly SameSite cookies, CSRF/origin checks, absolute access-token lifetime, provider revalidation outside DB locks, reset revocation cutoff; owner/manager/staff enforced per private operation | Unit/API negative tests; no refresh-token storage (re-login on expiry) |
| Database | Transactional v1→v4 upgrades; additive SQLite compatibility; read-only snapshot importer preserves IDs and optional new tables in dependency order; restricted runtime-role validation and remote verified TLS; tenant RLS on business data; anonymous Data API denied | Disposable PostgreSQL 16/17 rehearsals passed; hosted changes not authorized |
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

Recovery/compatibility follow-up: addressed invitation email is now available in
the existing team form; verified users without a business get an onboarding form.
Logout revokes the local cookie even when the provider is unavailable. A pending
password update blocks normal sign-in, leaves old sessions revoked on failure,
and requires a fresh provider-verified recovery flow to retry. Success revokes
sessions again before releasing the block. Recovery bearer reuse is rejected.

Legacy beta accounts can explicitly migrate through
`POST /api/auth/migrate-identity` with **both** a provider-verified matching-email
access token and their existing beta password. It preserves the user ID and
memberships, revokes old local sessions, refuses any reassignment and requires no
runtime owner/service credential. Email matching alone still never links an
account. Tests cover incorrect credentials, successful dual proof and rebind denial.

Verified source `b8bc335` passed **all four CI jobs** in
https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39892454692:
62 Python tests; 24 frontend tests; 11 PostgreSQL migration/RLS/import/actual
pg_dump→pg_restore checks; 50 restricted PostgreSQL API checks (one SQLite-only
trigger test skipped); 10 Chromium workflows; Docker readiness/startup and account/
request persistence after restart. Expected negative permission errors in the
PostgreSQL service log are assertions, not failing checks.

The final recovery/UI/legacy-migration follow-up passed **64 local Python tests,
21 skipped** (11 separate PostgreSQL and 10 browser cases). Python compilation,
JavaScript syntax, frontend runner and whitespace checks passed. Provider responses
remain synthetic; no real email, hosted Auth user or Stripe subscription was created.

The prior successful database CI used PostgreSQL 16. The CI service is now being
aligned to PostgreSQL **17**, matching the hosted project's major version; the
dump/restore drill uses that service's own tools. PostgreSQL 16 compatibility is
already demonstrated, while the final PostgreSQL 17 outcome is recorded below.

Supavisor compatibility: Psycopg automatic prepared statements are disabled with
`prepare_threshold=None`, following current Supabase transaction-pooler guidance:
https://supabase.com/docs/guides/troubleshooting/disabling-prepared-statements-qL8lEL
(accessed 2026-10-22; supports the pooler compatibility setting). Transaction-local
RLS context remains unchanged. The database integration test checks the actual
connection configuration. Hosted pooler/TLS acceptance is still a staging gate.

Source `232d2b2` also passed all four jobs in
https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39894113861,
including the final recovery, dual-proof migration and existing UI compatibility
changes. The last compatibility batch targets PostgreSQL 17 and disables automatic
prepared statements; final target-version CI evidence follows below.

## Final verified source and acceptance evidence

Source **be0027300a45e12c2d808e574fda843b977cf5bb** is published on
`qr-overnight-build`. Its remote tree exactly matches the locally committed tree.
All four jobs passed in [run 39895059070](https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/39895059070).

| Executed check | Result |
| --- | --- |
| Local complete Python suite | 64 passed; 21 skipped (11 PostgreSQL, 10 browser, executed separately in CI) |
| CI application Python suite | 64 passed; same 21 intentional skips |
| CI frontend regression suite | 24 passed; zero failed/skipped |
| Disposable PostgreSQL 17 migration, constraints, RLS, importer and actual dump/restore | 11 passed |
| PostgreSQL restricted runtime-role API/auth/payment/mail contracts | 52 passed; one SQLite-only trigger case skipped |
| Founder lifecycle on SQLite and restricted PostgreSQL | One passed on each backend (also included in broader suites) |
| Chromium mobile/guest/staff workflows | 10 passed |
| Production container | Build, non-demo startup, readiness/static assets and account/request persistence after restart passed |
| Compilation, JavaScript syntax, whitespace checks | Passed |

There are zero failed tests in the final run. Earlier QR tenant-scope and outbox
fixture failures were corrected and rerun. Assertions cover tenant A's inability
to read/write tenant B's private data, unscoped runtime denial, anonymous/browser
role denial, privilege escalation, immutable audit history and transaction-local
scope cleanup. The backup rehearsal restores synthetic data into a separate,
disposable database and compares table counts. It is not a hosted recovery drill.

Native Git transport remains blocked by sandbox DNS. Publication succeeded through
the connected GitHub integration using exact tree comparison and expected-head,
non-forced branch updates. Local pre-publication commits were retained on backup
branches; `main` was not changed. This final report update changes documentation
only and records the verified source above.

**Deployment readiness: blocked pending external acceptance.** Code and disposable
integration checks are complete for the implemented scope. Hosted backup/recovery,
restricted runtime credentials and TLS/pooler connection acceptance; real Supabase
verification/recovery/invitation delivery; Stripe test-account/webhook acceptance;
ingress, monitoring, privacy/retention and capacity acceptance remain incomplete.
Live billing remains disabled. A production rollout requires separate approval
after these gates pass. No hosted migrations, customer messages, real charges or
deployment were performed, and the working SQLite beta remains available.

Follow-up local result (2026-10-24): **70 passed, 21 skipped** in the complete
Python suite using the existing venv and documented sandbox asyncio workaround.
The 11 PostgreSQL and 10 browser cases are intentionally reserved for isolated CI.
Python compilation, JavaScript syntax and whitespace checks passed. An initial
new billing fixture reused another test's synthetic subscription ID; corrected
that fixture, reran all six billing cases successfully, then passed the full suite.
No failed test remains locally. Provider transports remain injected/synthetic.
