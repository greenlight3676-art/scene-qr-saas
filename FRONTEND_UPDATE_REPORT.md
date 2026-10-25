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
