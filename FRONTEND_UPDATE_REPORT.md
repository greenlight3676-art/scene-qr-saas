# Frontend: guest help with location context

The customer problem is explicit: a guest needs help, and staff need to know
where to respond. Landing copy and the labelled example show a Table 07 water
request reaching the staff queue with location context. Guest actions repeat the
scanned station name; staff cards visibly separate request type from “From station”.
No geolocation, automatic staff routing or guaranteed response time is claimed.
Station context comes from the existing QR/backend response, not a guest-supplied
address. It remains escaped before rendering.

Account screens now share the existing plum/ivory/bronze styling, responsive layout,
labelled inputs, readable help, visible keyboard focus, busy buttons and actionable
error states. The confirmation script previously removed query parameters before
checking recovery/onboarding mode. It now captures mode first and still scrubs
query/fragment proofs from the address bar. Verification transitions to password,
onboarding or workspace as appropriate. Duplicate submissions are blocked while
pending, failures leave a retry available, and recovery/onboarding retain CSRF.
Phone sign-in remains visible instead of disappearing behind the signup action.

All existing URLs/API contracts are preserved. No backend, schema, provider
configuration, Stripe, deployment or hosting changes were made. Email/provider
browser responses in the new tests are synthetic; real acceptance remains blocked
as recorded in BACKEND_ACCEPTANCE_TASKS.md.

Baseline Python: 79 passed, 21 skipped. Existing frontend runner, JS syntax,
Python test compilation and whitespace checks passed. No local Chromium is
installed; no package/browser installation was attempted. New browser tests cover
320/390/768px recovery and errors, onboarding query mode/CSRF, token-hash scrubbing,
duplicate-submit prevention, mobile sign-in and clear request/station messaging.
Screenshots are saved as CI test artifacts; visual inspection is not claimed from
static source or unexecuted tests. Final CI results follow after execution.

Verified frontend source: `ac0682e513e53d6bcd3592147bc43cd1ab94818f`, published
on qr-overnight-build after merging the latest remote changes through da8efff.
All four jobs passed in
https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/40159601204.
The first browser run passed 15/16 and exposed a moving-button hover instability
at 390px. Account actions now stay stationary, reduced-motion hover does not
translate buttons, and the complete browser suite was rerun successfully.

- 16 Chromium workflows passed, including 320/390/768px recovery/error/focus
  checks, onboarding and token-hash/double-submit checks.
- The real guest → staff workflow asserts that both interfaces show the same
  backend-provided station name; synthetic help requests were used.
- 26 frontend regression tests passed; application Python: 79 passed, 27 skipped
  (11 PostgreSQL and 16 browser cases run separately).
- PostgreSQL: 11 database/restore checks and 59 restricted-role API tests passed;
  two SQLite-only cases skipped. Container checks passed.
- Screenshots for the landing, account recovery and existing guest/dashboard
  journeys are available in the run's founder-browser-evidence artifact.

No final failures remain. Browser assertions confirm layout bounds and workflows;
manual visual review and real physical-device/provider acceptance remain separate.
This is one frontend improvement batch, not a claim that every backend capability
has a dashboard screen. Backend credential/provider blockers are unchanged.
