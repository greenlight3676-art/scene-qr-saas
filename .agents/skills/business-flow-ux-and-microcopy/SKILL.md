---
name: business-flow-ux-and-microcopy
description: Design usable onboarding, accounts, QR flows, appointment/request funnels, owner dashboards, clear forms, notifications, microcopy, empty/error states, and conversion flows for business websites and SaaS.
---
# Business Flow UX & Microcopy

## Flow-first method
1. Identify user role and JTBD: guest, owner, staff, manager, admin. Draw the happy path and the five most plausible bad paths for each.
2. Enumerate every screen and edge state: new account, validation error, email verification pending, expired invitation, loading, zero items, offline, unauthorized, duplicate submission, saved, conflict, abandoned flow.
3. Make one primary action obvious per screen and keep the next step visible. Minimize fields; ask permissions only when needed; preserve work when possible.
4. For QR guests: scanning must show the correct business and station; no signup required for basic request flows; distinguish requests from actual orders or bookings. Protect guest receipt tokens.
5. For business owners: prioritize first-value onboarding (business → template → QR placement → sample preview → real customer request), not vanity dashboards.
6. For multi-tenant dashboards: selection and filtering must never rely on the UI for authorization. Server checks and tenant tests are required for every private resource.
7. For actions with consequences: contextual confirmations for destructive actions, undo where safe, explicit status and timestamps; status changes must reflect actual backend state.
8. For metrics: label data provenance, date range, units, refresh latency; distinguish page loads from deduplicated human scans and leads from actual purchases. Include accessible tabular summaries of charts.

## Microcopy rules
- Remove filler and repetitive phrases. Lead with why users should act, then the step.
- Use a controlled glossary for **scan**, **request**, **order**, **reservation**, **appointment**, **lead**, **QR station**, **business**, **team member**; never interchange distinct events.
- Prefer verb + noun labels: 'Create QR code', 'Send request', 'Invite teammate'. Avoid 'Submit', 'Learn more' where context is unclear.
- Good empty state: 'No requests yet. Share a QR code to start receiving requests.'
- Good validation: 'Enter a valid phone number.' Point to exact field; never say only 'Something went wrong'.
- Errors: state what happened, whether saved, how to retry, and how to get help. Never expose internals.
- Onboarding: make optional steps skippable and resumable. Avoid misleading urgency and fake social proof.
- Localization: support Spanish where requested, longer labels, plurals, RTL and locale formats. Do not machine-translate business names.
- Notification permissions: opt-in at a relevant moment, clear purpose; respect refusal.

## Workflow deliverables
For each changed flow provide: user-role map, sequence, screen/state table, exact labels/error copy, success metrics, data/security dependencies, and test cases (including cancellation, replay, retry, cross-tenant denial).

## References
- https://developer.apple.com/design/human-interface-guidelines/
- https://developer.apple.com/videos/play/wwdc2025/404/
- https://developer.apple.com/videos/play/wwdc2025/356/
