# PostgreSQL/Supabase security preparation — 2026-10-22

Historical preparation report. Current implementation and verification supersede
these limits in [BACKEND_COMPLETION_REPORT.md](BACKEND_COMPLETION_REPORT.md).

Destination identity supplied/previously verified: FORGE, `cwehqnziwabvnzviaqlf`,
us-east-1. No hosted migration, production write, identity binding, email send,
installation or deployment was performed during this work. SQLite remains default.

## Integrated locally

- Additive PostgreSQL version 3 upgrades from versions 1/2; atomic import includes
  optional security tables from newer SQLite backups and retains legacy sources.
- Transaction-local tenant RLS for requests, products, stations, scans, invites,
  audit history. SELECT-only QR/invite/receipt capabilities support public flows.
  Browser roles receive no policies/access to private app tables.
- Runtime role verification checks both authenticated login and effective role,
  rejects inherited administrative privileges/ownership and schema CREATE access.
- Core audit history is written in the same transaction as request creation,
  request/lead status changes and membership changes. It stores IDs/actions/time,
  not contact details, messages, bearer tokens or passwords. Only business owners
  can read the latest 100 events through the API. It is not a complete security
  event or immutable external audit service. SQLite file owners can modify data.
- Optional `SCENE_AUTH_MODE=supabase` uses a fixed project Auth API with a modern
  publishable key, verified nonanonymous subject lookup, password login, recovery
  request and password update endpoints. It rejects local beta sessions and
  legacy password signup/join in managed mode. No email-based automatic linking.
- Secure HttpOnly SameSite cookies, CSRF checks and hashed local session IDs are
  retained. Managed provider access tokens stay in backend-only session storage;
  treat this database and backups as secrets. No refresh tokens are retained.
  Managed sessions expire within an hour/provider lifetime and revalidate with
  Auth `/user` on each private request; outages fail closed. Password reset deletes
  local sessions. Users must log in again after access-token expiry.

## Not complete / hosted blockers

Production launch remains blocked. Backup entitlement, actual backup/restore drill,
restricted runtime credential provisioning, TLS verification, hosted policies and
security advisors remain unverified. No disposable PostgreSQL server is installed
locally; migration/RLS rehearsal uses the separate ephemeral GitHub CI database.
Do not substitute the hosted project URL for a test database URL.

Managed auth requires approved provisioning of Supabase users and explicit
`auth_identities(subject,user_id)` bindings by a migration administrator. Obtain
the verified subject from the provider, review ownership separately, and bind it
with a parameterized transaction. No binding UI/CLI is supplied. Self-service
managed signup, invitations, confirmation callback and recovery UI are unfinished.
The current browser beta still has its local login UI; managed login works through
the same API but managed onboarding/recovery needs completion before rollout.

Supabase email confirmation must be enabled; configure approved SMTP, rate limits,
Site URL and exact redirect allowlist in staging. Test real email verification,
expired/replayed links, recovery and provider signout there with approved accounts.
A `/user` lookup does not establish immediate global JWT revocation guarantees.
Cross-system password-update/database-failure recovery and refresh-token rotation
remain incomplete. No service-role/owner key is required by the auth transport.

Users, businesses, memberships and sessions retain backend-wide RLS policies for
trusted authentication/membership lookups; endpoints still enforce membership on
private operations. Browser Data API remains denied. Runtime credentials are
trusted server credentials and must never reach browsers. Durable distributed
rate limiting, comprehensive auth audit events, encrypted token storage/key
rotation, retention controls, realtime, monitoring and post-cutover reverse
reconciliation remain open gates. No production-readiness claim is made.

## Verification

Baseline: existing venv with `/tmp/scene_asyncio_check.py` sandbox timer workaround:
`PYTHONPATH=/tmp:. <existing-venv>/bin/python -c
"import scene_asyncio_check,pytest; raise SystemExit(pytest.main(['-q','tests']))"`
38 passed, 18 skipped (PostgreSQL/browser services unavailable locally).
Plain `python3 -m pytest -q tests` failed: default interpreter has no pytest.
No packages were installed. Final verification and CI evidence are recorded below.

Security references consulted on 2026-10-22: Supabase connected documentation
search, email confirmation/recovery guidance at
https://supabase.com/docs/guides/auth/passwords and server auth/security guidance
in the Supabase skill. The changelog markdown fetch was attempted but the web
reader rejected its content type; no claim of a complete changelog review.

Final available local suite: **43 passed, 19 skipped** (9 PostgreSQL database
cases and 10 browser cases). Authentication provider tests use synthetic responses;
no hosted provider or mail delivery was exercised. JavaScript syntax, Python
compilation and `git diff --check` passed; existing frontend Node test runner
passed. Remote runtime startup now requires `sslmode=verify-full`.

Publication/CI blocker: the connected GitHub read request failed with a transport
error reaching `chatgpt.com/backend-api/ps/mcp`. No claim of PostgreSQL rehearsal
success is made until CI can actually run and its results are inspected.

Git fallback also failed: `git ls-remote origin refs/heads/qr-overnight-build`
returned `Could not resolve host: github.com`. Publication and CI inspection are
blocked by network connectivity, not owner approval. Reconnect and push this
reviewed branch without force, then inspect all jobs before any hosted migration.

Follow-up focused verification: **11 managed-auth/storage checks passed**,
including additive SQLite session preservation and remote TLS requirements.
Python compilation, JS syntax and whitespace checks were repeated after the
follow-up edits. PostgreSQL/browser validation remains skipped, not passed.

The authorized `git push origin HEAD:qr-overnight-build` was attempted and failed
with the same GitHub DNS error. Git had no configured author; the local commit
uses the explicit automated identity `Codex <codex@localhost>` for this commit
only, without changing global Git settings or attributing work to the owner.
