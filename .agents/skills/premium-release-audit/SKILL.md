---
name: premium-release-audit
description: Audit premium product UI end-to-end for consistency, working interactions, accessibility, performance, security-facing UX, mobile defects, and launch readiness. Use before demos, publishing, client handoff, or claiming a redesign is finished.
---
# Premium Release Audit

## Rule zero
A slick screenshot is not a pass. Verify real flows against backend behavior. For Scene QR, read AGENTS.md and honor cross-tenant and guest-data security rules. Never publish, charge, enable Stripe, expose live customer records, or trigger hosting without explicit approval.

## Audit sequence
1. Inventory routes, components, roles, forms, buttons, cards, filters, modals and language variants; make a test matrix.
2. Run existing project tests and lint/typecheck/build commands if available. Establish a baseline before changes.
3. Test every link/button and navigation target; check browser Back, page reload, loading, empty, malformed data, long content, offline and backend error states.
4. Test actual writes in a safe/local/test environment: create/edit/delete/retry/cancel; verify data survives reload; distinguish front-end simulation from persisted state. Do not use production data for test writes without authorization.
5. Inspect responsive UI at 320, 375, 390, 768, 1024, 1440 CSS px when possible; check horizontal overflow, obscured controls, tap targets, sticky headers, mobile keyboard, safe-area overlap, rotation and zoom.
6. Visual-quality pass across ALL pages: token consistency, type scale, grid rhythm, aligned edges, images, section pacing, brand feel, video/posters, icon consistency, high-quality dark/light states.
7. Accessibility pass: keyboard, screen reader labels, focus restoration, form errors, live regions, contrast, touch targets, 200% text, reduced-motion.
8. Performance pass with representative throttling: LCP, INP, CLS, JS weight, video/blur costs, image dimensioning, layout shifts, no render loops.
9. Security-facing pass: private pages require login, no secrets in UI or logs, tenant A cannot read/act on tenant B, rate limiting, CSRF protections where relevant, QR does not grant private access.
10. Retest every issue fixed, then report evidence, release blockers and non-blockers separately.

## Grading
- P0: data leak, unauthorized access, irreversible data loss, fake production integration or broken primary revenue flow.
- P1: broken primary navigation, signup, QR, request, accessibility blocker, significant mobile overlap.
- P2: visual inconsistency, recoverable UX issue, poor loading/error state, noticeable performance issue.
- P3: polish improvements.
Never say 'fully tested' if checks were only code-reviewed or could not run.

## Release report
Return a compact report with: tests run and results, screen/flow coverage, before/after changes, defect list with severity, security/real-service integration status, manual checks outstanding, and exact go/no-go blockers. Prefer a PR to uncontrolled direct changes.
