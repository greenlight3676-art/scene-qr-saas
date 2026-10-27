# Production blocker follow-up — 2026-10-27

## Implemented

- The prior draft-quote/appointment privacy repair is merged and deployed to the
  existing API. Deployment dep-dbg33ei9lscs738ss7tg is live at source 1588436a.
- Business setup reports tenant-scoped observed services, active QR locations,
  teammates, requests and completions. Solo operators can skip team/catalog
  additions. Its two-phone guide explains the physical owner/staff/guest check.
  A manual guest-page checkbox never marks provider/device checks as verified.
- Owner-only subscription status/configuration, Checkout and billing portal UI
  use the existing server-priced and idempotent endpoints. The Sites proxy now
  preserves Stripe-Signature and Idempotency-Key and forwards raw body bytes.
- Billing defaults to test mode; the explicit live setting requires matching
  live keys/events/provider state. Signature checks, replay protection, canonical
  subscription reconciliation, cancellation and failed-payment access checks are
  retained. No live mode setting was enabled and no charge was made.
- Configured, enabled team invitations send after commit using the existing
  durable outbox. Owner-only retry and provider delivery checks distinguish
  queued, accepted, delayed, bounced and delivered mail. No sender was invented;
  no customer email/SMS alert capability is claimed.
- Setup controls have named headings, status regions, visible labels, wrapping
  text, responsive columns and 44px controls. Auth errors are announced.

## Verified existing infrastructure

Read-only Supabase inspection: 23 public tables have RLS, zero lack RLS, zero
browser-role table grants. scene_runtime can log in and is neither superuser nor
bypass-RLS. The existing Render service uses /readyz and the intended repository.
These are infrastructure facts, not proof of email delivery or phone acceptance.

## Still needs account/real-world completion

- Resend reports no verified sending domains. A domain the owner controls, DNS
  verification, secure runtime key/sender and a nominated test mailbox are needed.
  Custom Supabase Auth SMTP settings and leaked-password protection remain
  unverified/disabled; current native tools do not expose their management API.
- No Stripe account is connected through the available management workflow.
  Actual plan amounts, matching test/live prices and webhook secrets are absent
  from this session. Real provider checkout, renewal, failure and cancellation
  acceptance remains required. Hosting credentials were not printed or changed.
- Automatic approval review rejected new Stripe, Supabase-management and
  Render-management connections because specific account access was not approved.
  Do not bypass that rejection using another execution path.
- The invitation outbox does not implement customer email/SMS alerts. A chosen
  provider, consent model, sender and delivery tracking are still required.
- Physical iPhone/staff/customer checks, unassisted onboarding observation,
  VoiceOver/TalkBack, real usability feedback and a hosted restore require actual
  devices/users or approved recovery infrastructure. Automated simulations must
  not be relabeled as those outcomes.
- Workspace request/outcome metrics include any tests. Recorded revenue is
  manually reported, not independently verified payment revenue. No real leads,
  customers, testimonials or sales were fabricated.

Provider references reviewed: https://docs.stripe.com/webhooks,
https://docs.stripe.com/keys,
https://resend.com/docs/api-reference/emails/retrieve-email.
