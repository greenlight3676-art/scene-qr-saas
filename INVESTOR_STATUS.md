# Scene QR investor overview — October 26, 2026

Scene QR is a public-beta service-workflow product for physical businesses.
Customers scan a location-specific QR without installing an app; staff manage
requests with table, counter, chair or bay context in a shared workspace.

## Product implementation

The qr-overnight-build development branch includes customer pipelines,
revision-guarded private-receipt quotes, manually confirmed appointment records,
follow-up dates and team-recorded outcomes by QR placement. Authentication,
tenant/role authorization and durable rate limiting have automated contract tests.
These statements describe implemented code, not verified live-provider operation.

The public Sites beta is https://scene-qr.dnice2609.chatgpt.site/ . Deployment
records confirm public version 13 published October 25. That record alone does
not establish which development-branch backend features are active there.

## Validation and boundaries

Revenue, paying-customer counts, retention, willingness to pay and production-scale
adoption are not verified. Initial industry segments remain hypotheses. Page loads
include previews and refreshes; placement revenue is entered by the business and
is not processor-verified revenue or proof that QR placement caused a sale.

In-app notices require an open workspace. Follow-up messages are owner-reviewed
drafts. Appointments are manually confirmed. No automated email/SMS outreach,
background push, availability scheduling, guest payment collection, POS delivery
or working AI automation is claimed. Stripe code is test-mode only; real provider
acceptance and live billing remain incomplete.

## Next evidence milestones

1. Pass PostgreSQL migration, tenant isolation and growth API CI on the exact
   release commit; verify backend and frontend versions together in the beta.
2. Complete restricted runtime/TLS, real Auth verification/recovery/invitation
   delivery, isolated hosted restore and Stripe test-account acceptance.
3. Run an authorized real-business pilot and record active businesses, QR-originated
   requests, completed requests / submitted requests, response/completion times,
   repeat usage, feedback and paid conversion. Exclude synthetic/demo traffic.

No pilot outcomes or customer commitments are supplied by this overview.
Round size, use of proceeds and terms remain unfinalized.

## Evidence

- Growth implementation: https://github.com/greenlight3676-art/scene-qr-saas/pull/9
- Transaction ordering fix: https://github.com/greenlight3676-art/scene-qr-saas/pull/10
- Growth merge CI (failed PostgreSQL setup): https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/40220811859
- Main CI (different source, passed): https://github.com/greenlight3676-art/scene-qr-saas/actions/runs/40253566006
- GROWTH_RELEASE.md and BACKEND_ACCEPTANCE_TASKS.md describe behavior limits and
  outstanding live acceptance. Older reports are historical, not current results.

This revision is prepared for review; no investor email has been sent or changed.
