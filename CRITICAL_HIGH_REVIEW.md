# Critical/high follow-up — 2026-10-27

Base: `da1fb7d53b81059f68d23fa698cce978670121f2` (PR #11).

## Confirmed and repaired

- **High: draft disclosure.** The private guest journey returned quote prices,
  scope, expiry and tentative appointment times from jobs saved as New or
  Contacted. This contradicted the editor's explicit Quoted publication step.
  Journey responses now include quote fields only while Quoted or while the
  exact revision remains customer-accepted. Editing invalidates acceptance and
  hides the new draft. Appointment times appear only for Booked/Won jobs.
  Owner/manager access, tenant isolation and receipt authorization are preserved.
  No schema migration is required.
- **Hosted edge protections:** the separate Sites source previously omitted
  CSP and anti-framing headers on both pages and proxied responses. The paired
  site change adds these at the edge and preserves cross-site fetch metadata,
  rejecting cross-site API requests even when Origin is absent. External HTTPS
  campaign images remain allowed; scripts and API connections remain same-origin.

## Evidence

The new backend regression failed against the base with draft fields in the
customer response. With the fix, 84 Python tests pass (28 PostgreSQL/browser
tests skipped without their opt-in environments). The baseline was 83 passing.
The separate Sites suite passes 72 checks, including two regressions that failed
before the edge changes. Its build and Worker artifact validation pass.

Read-only hosted verification: Scene QR Supabase is ACTIVE_HEALTHY, application
tables have RLS, browser roles have no direct table grants, and tenant/capability
policies target the restricted backend role. The live API readiness returned
200/ok. These checks do not establish email delivery, recovery or hosted restore.

## Remaining launch gates

- Backend deployment must use this reviewed source; a GitHub commit alone does
  not change the running FastAPI service. The existing Sites proxy still uses
  the existing Render API with Supabase storage. No Supabase-only API port is
  implemented by this patch.
- Supabase's security advisor reports leaked-password protection disabled.
  Available connector tools do not expose Auth-setting updates. This review
  does not claim that setting was enabled.
- Real signup/recovery/invitation delivery, hosted backup restoration, physical
  phone acceptance, and Stripe provider acceptance remain unverified. No email,
  real charge or customer-data mutation was performed by this review.
- `main` is older than the active backend/frontend branches. Integrate scoped
  branches deliberately; do not deploy old main over the working beta.
