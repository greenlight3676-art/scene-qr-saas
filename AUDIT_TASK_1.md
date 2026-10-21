# Task 1 — PostgreSQL transition foundation (not cutover approval)

Implemented opt-in PostgreSQL adapter, explicit transactional versioned schema,
empty-target read-only SQLite import with integrity/count checks and identity
sequence recovery. Startup rejects demo mode, privileged runtime roles and an
unmigrated PostgreSQL database. No environment/data changes occur by default;
SQLite initialization and URL contracts remain unchanged.

Composite foreign keys reject tenant-mismatched request station/product and scan
references. Existing server membership/role checks remain authoritative. Shared
transaction advisory locking preserves existing request/invite read-check-write
serialization, with timeouts; this intentionally limits throughput. A schema
owner and separate restricted runtime role are documented. RLS remains unfinished,
as do full PostgreSQL API parity, concurrency and import recovery tests. These
are explicit Task 1 completion gates, not claims of production readiness.

Small CSS changes wrap dashboard headings/header/queue controls on narrow phones,
provide 44px queue controls, and use 16px mobile form inputs. Existing colors and
layout remain. Browser/device verification remains manual.

Validation in this workspace:
- Baseline and final system `python3 -m pytest -q tests`: blocked, pytest absent.
- System pip and venv ensurepip absent. Bootstrap downloaded with approved network
  access; sandbox installation failed DNS for pypi.org. Escalated installation
  did not produce a usable test environment during validation.
- No local psql/PostgreSQL server available; PostgreSQL tests not executed here.
- Python compileall for server/storage/migration/tests: passed.
- Three stdlib unittest adapter regressions: passed.
- node --check static/app.js: passed.
- node --test tests/frontend.test.cjs: passed.
- git diff --check: passed.
- Added disposable PostgreSQL 16 CI job for migration repetition, down/up and
  negative station/product tenant references. Hosted CI has not run.

Manual checks before cutover: restore backup into a scratch database, import and
compare counts privately, test existing QR links/receipts, guest submit and staff
completion in two browsers, test tenant A/B access and role restrictions using the
restricted runtime role, verify stale/duplicate status actions, and inspect narrow
phone layout, keyboard focus and reduced motion. Do not use runtime data for CI.

Requests remain staff requests. No POS, payments, email provider, realtime push,
billing, public deployment or external merchant integration was introduced.
