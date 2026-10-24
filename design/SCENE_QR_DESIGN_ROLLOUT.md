# Scene QR — Lundy Design System rollout
Scope: incremental frontend changes that preserve the current FastAPI/SQLite pilot, auth, real tenant isolation, working requests, and data. **No deployment or production connection is authorized by this plan.**

## Existing implementation observations (code review, not tested)
- `static/index.html`: marketing, owner workspace, guest preview, and auth modal in one page.
- `static/style.css`: current midnight/plum/bronze look; multiple hand-authored component values and motion effects.
- `static/app.js`: renders dashboard screens and QR guest flow; intro is session-gated with a skip button and reduced-motion check.
- Current README explicitly labels this a beta; managed Postgres, email recovery and Stripe are not yet production-ready. Do not claim these features exist.

## First vertical slice: guest scan → request → receipt
1. Inventory QR entry points, welcome/content, action selection, request confirmation, receipt and status. Keep no-signup guest flow.
2. Define semantic tokens mapped to existing values; no sweeping palette replacement and no forced visual redesign.
3. Ensure the first meaningful guest action is visible and responsive at 320–390px, with primary controls >=44px where possible.
4. Audit status language to clearly distinguish requested, accepted/in progress, completed, and any denied/cancelled states actually implemented.
5. Keyboard/screen-reader pass for focus order, form validation, live status announcements and control labels.
6. Preserve real server API contracts, CSRF/guest token boundaries and authorization.

## Second slice: owner dashboard
1. Establish reusable shell/nav/page title/form/table/empty state and status components.
2. Standardize spacing, typography, surface, border, focus and status tokens gradually.
3. Verify owner switches between businesses without cross-tenant display leakage or stale responses.
4. Ensure all owner actions have pending/disabled/error/success states and explicit confirmations for destructive actions.
5. Charts must distinguish scans/page loads from unique people; show exact units and real data provenance.

## Third slice: onboarding and brand studio
1. Clarify the sign-up journey and initial setup with progress indications and recoverable state.
2. Preview brand choices with accessible contrast. Avoid using brand choices to override status/error semantics.
3. Include properly labelled fields, inline validation and copy that never implies live Stripe/POS/email integrations.
4. Recheck translated/localized layouts when locale support actually ships.

## Fourth slice: polish and QA
- Use compact contextual transitions for cards and navigation; minimize blur and shadows under constrained performance.
- Run phone and desktop real-interaction checks: 320, 375, 390, 768, 1024, 1440 px; slow 4G; 200% zoom; reduced motion; keyboard-only; accessible contrast.
- Maintain a flow-by-flow matrix: onboarding → create business → create QR → scan public code → submit request → staff status → private receipt → analytics; additionally simulate two businesses and verify denial across tenants.
- Run `python3 -m pytest -q tests` and `node --check static/app.js` before and after implementation. Use browser checks when available, and report untested flows plainly.
- Do not merge visual changes if they weaken access controls, request status truthfulness, form submission, focus usability, or persistence.

## PR sequencing for Codex
- **PR A**: semantic CSS tokens and component inventory; screenshots before/after; no API changes.
- **PR B**: guest QR vertical slice interactions and accessibility; add test evidence.
- **PR C**: owner workspace consistency, data and responsive states; tenant isolation regression.
- **PR D**: focused cinematic motion + performance validation; preserve reduced-motion paths.
- **PR E**: cross-browser release audit with prioritized defects and launch blockers.
Each PR should be independently reviewable and include commands actually run, evidence and risk.

## Product identity
Scene QR is the flagship product. It must not be styled identically to RVC or Ghostline. Export the **rules and reusable skills**, not the branded appearance, tenant data or business logic, to other repos.
