# SCENE — The Experience OS
**Version:** 0.1 product blueprint  |  **Date:** October 18, 2026  |  **Status:** prototype / product specification

> Working brand name only. Check domain and trademark availability before selling or publicly launching. This plan is based on the TRIO / OrderFlow-style concept and is not affiliated with OrderFlow, Toast or any existing product.

## Executive decision

**Build a multi-tenant SaaS for contextual QR-powered customer experiences.** A business signs up, selects an industry template, configures a brand and a set of QR spots, prints the QR codes, and receives customer interactions on a staff dashboard. The same infrastructure serves restaurants, barbershops, automotive service businesses, retail and other service businesses. Avoid building a separate codebase per industry.

**Why this wins:** the merchant can get value from a simple QR menu/request workflow immediately. The visual magic (animation, floor plans, themed experiences) is a premium layer, not a dependency. Price for actual labor/time saved, not flashy graphics alone.

## Product positioning

- **Customer:** "Scan once. Do what you came for." A fast branded web experience, no app installation.
- **Merchant:** "Turn physical spaces into self-service touchpoints." Configure QR spots, products/services, and manage incoming requests.
- **Platform owner:** "Launch and manage multiple businesses from one account." Recurring subscription revenue from an industry-flexible system.
- **First proof:** TRIO-inspired restaurant demo with one simulated table; then pilot in a real location with permission.

### Product guardrails

1. A QR scan should reach the relevant action in **two taps or fewer** on typical workflows.
2. QR codes never expose private business data, admin privileges, payment secrets or guest identity.
3. All order-like requests remain **requests** until an authenticated staff member confirms them or a supported integration acknowledges them.
4. No unnecessary sign-up for guests. Staff and owners authenticate.
5. Accessibility first: accessible contrast, 44px-ish hit targets where feasible, keyboard support, `prefers-reduced-motion`, semantic labels.
6. Never imply a third-party POS/payment integration is live if it hasn't been implemented, authorized, tested and approved.

## Product surfaces

### A. Marketing + self-service onboarding

- Home: value proposition, industry walkthroughs, live demo links, FAQs, pricing, support.
- Sign-up: email/password or passkey via managed auth; verify email before activating business.
- Wizard: business name → industry → address/timezone → brand color/logo → catalog/service list → first QR spot → preview → print.
- Trial and billing: Stripe Billing subscription, invoices, failed-payment recovery and webhooks. Consider free demo, paid activation; set price limits and trial policy in dashboard. No client-side enforcement of paid entitlements.
- Location configuration: multiple branches per company only on eligible plans.

### B. Customer mobile web app (`/e/{public_business_slug}/{spot_slug}`)

- Loads directly from a printed QR/NFC tag without account creation.
- Identifies the business and *spot* (restaurant table, barber chair, auto service bay, store shelf, etc.).
- Branded welcome panel, clear primary action, compact service catalog, cart/selection or task form.
- Create a service request with appropriate type, explicit confirmation, then receive a status screen.
- Context actions are template-dependent:
  - Restaurant: view menu, ask for water, call staff, request bill. Order submission and payment require an authorized integration or staffed manual approval.
  - Barber: check in, select a service, call staff, join the waitlist (optional).
  - Auto: ask for quote, locate vehicle service status, request advisor; never reveal a customer's repair details based only on a public QR.
  - Retail: browse curated products, request a size/item, ask for help.
- Accessibility: text alternatives; don't make navigation depend on sound/animation/3D.
- Optional appearance: immersive animated scene or later isometric restaurant experience.

### C. Employee operations (`/app/queue`)

- Unified real-time queue filtered by merchant, location and assigned staff.
- New → Accepted/In progress → Completed; cancelled and rejected states as needed.
- New request notification sound/visual, optional browser push with staff opt-in.
- Staff can take ownership, respond, complete; duplicate/cancelled requests cannot be accidentally fulfilled again.
- Service-level timers and notes; avoid displaying PII to staff who don't need it.
- Realtime using server-originated authorized channels; browser reconnection and offline/retry messaging.

### D. Merchant studio (`/app`)

- Overview: scans, meaningful interactions, open requests, completion times; avoid vanity-only metrics.
- Experience builder: templates, header, brand assets, featured content, catalog/services, service-request types.
- QR manager: create codes, batch print PDF/SVG, rotate/disable code, see per-spot scan analytics.
- Team: invite staff with role, revoke access, audit sensitive actions.
- Billing, location settings, data export/deletion, support, plan management.

### E. Platform admin (`/admin`, owner only)

- See merchants, subscription and onboarding status, aggregate high-level usage, support tickets and service health.
- Template library with publish/version/archive and plan-controlled feature flags.
- Account suspensions and code disabling with audit trails and legitimate-business safeguards.
- **No default access to each merchant's customer data:** staff/support access is exceptional, permissioned, audited and time-limited.

## One platform, many industries

Use a **config-driven experience engine**. All businesses share tenant identity, locations, QR spots, catalog, roles, requests, analytics and subscription status. Templates control which customer actions are enabled, language/appearance and request fields. Avoid hard-coded behavior for specific named businesses.

| Industry | QR spot | Guest primary action | Staff action | MVP? |
| --- | --- | --- | --- | --- |
| Restaurant | Table | Browse menu / request service | Handle request | Yes |
| Barbershop | Chair / lobby | Check in / select service | Handle check-in | Yes, template |
| Automotive service | Counter / bay | Request quote / advisor | Respond / schedule follow-up | Yes, template |
| Retail | Shelf / fitting room | Request item / help | Assist customer | Yes, template |
| Fitness / events / hotels | Station / venue / room | Industry-specific action | Industry workflow | Later |

Build and sell **one excellent restaurant pilot first**, then validate barber and auto before adding many niche modules. TRIO is a candidate, not a confirmed production customer.

## MVP boundaries

### Must ship for a pilot

1. Authentication and roles: platform admin / business owner / manager / staff; no guest sign-up.
2. Tenant and location setup with editable branding.
3. Four starter templates sharing the same UI engine.
4. QR destinations with per-spot association and rotation/disable support.
5. Public mobile-first customer landing page and editable catalog/services.
6. Submit guest request and see response/confirmed status.
7. Authorized staff queue with real-time updates and retry handling.
8. Simple merchant analytics (unique visits approximately, request counts, completed counts), with privacy-minimizing analytics.
9. Subscriptions/entitlement gates, invoices, owner billing portal and webhook-based activation.
10. Audit logs, basic rate limiting, backups, monitoring, privacy disclosures, test coverage.

### Explicitly outside MVP

- Real 3D/isometric restaurant with people avatars (very high implementation cost).
- Actual food ordering to Toast until API authorization and scope are verified.
- Live card payments or split-bill collection.
- AI concierge that gives food allergen or medical advice.
- Multi-person games with competitive leaderboards, guest location tracking, customized native mobile apps.

### Suggested premium roadmap

- **Phase 2:** POS/payment integrations, shared bill view where supported, reward points, more templates, multilingual experience (English/Spanish first), printable NFC-ready signage kits.
- **Phase 3:** interactive floor plans, mini-games, AI concierge backed by approved business sources, smart recommendations, advanced analytics, white-label domains.

## User journeys

### Customer guest at Table 05
1. Scan QR → land on `https://.../e/trio/table-05` (the code is location-specific, not user-specific).
2. Read table identity, menu and large contextual actions.
3. Tap "Need water" → server creates a deduplicated request. Immediate confirmation and ticket/reference.
4. Staff member accepts; guest status updates without reload.
5. Staff completes request; guest sees completed status. All statuses are authoritative from server.

### Restaurant owner onboarding
1. Create verified account.
2. Create business and first location; select Restaurant template.
3. Add 3 menu items, choose brand colors, preview mobile.
4. Create QR spot "Table 05" and download print-ready code.
5. Invite an employee with Staff-only permissions.
6. Scan code with real phone, create a test request, mark it completed.
7. Enable paid plan (webhook confirms) and start pilot.

### Platform-owner workflow
1. Check new merchants and activation status.
2. Help with onboarding without accessing their customer data unnecessarily.
3. Manage template versions, subscription metadata and technical alerts.
4. Collect product feedback and prioritize verified customer demand.

## Recommended production architecture

- **Web app:** Next.js / React / TypeScript. Mobile-first; guest views ultra-lightweight and accessible. Distinct routes for public guest, merchant app and platform administration.
- **Design:** CSS tokens + reusable UI components, per-tenant brand theme with constrained readable contrast; tasteful motion, no mandatory long intros on repeat scans.
- **Auth / DB:** Supabase Auth + PostgreSQL, Row Level Security with explicit tenant membership checks. Backend validates everything; RLS is defense in depth. Test negative cross-tenant access cases.
- **Backend:** Next.js server routes or Supabase Edge Functions for request creation, staff actions, QR generation, Stripe webhooks and integrations. Keep admin/service keys server-side only.
- **Realtime:** Supabase Realtime private channels or server fan-out with tenant/location authorization. Guests subscribe only to their own opaque request IDs/tokens, not general location feeds.
- **Media:** Object storage per tenant with signed upload URLs, MIME/file size checks and safe file handling.
- **Billing:** Stripe Billing; webhook idempotency, entitlement table, delayed/cancelled/failed-payment states, owner billing portal.
- **Analytics:** Server-logged, privacy-preserving scan/request events; filter bots; retention policy; location-specific event indexes.
- **Operations:** CI/CD, separate staging/prod environments, automated migrations, error tracking, health checks, backup restoration drill.

### Data model (minimum production tables)

| Table | Critical fields | Rules |
| --- | --- | --- |
| `organizations` | `id`, `name`, `status`, `created_at` | Tenant root |
| `memberships` | `org_id`, `user_id`, `role`, `status` | Unique membership, strict RLS |
| `locations` | `id`, `org_id`, `name`, `timezone` | Indexed by tenant |
| `experiences` | `id`, `org_id`, `location_id`, `template_id`, `theme_json`, `published_version` | Publish atomically |
| `qr_spots` | `id`, `org_id`, `location_id`, `experience_id`, `label`, `public_token`, `disabled_at` | Opaque unguessable token, rotate/revoke |
| `catalog_items` | `id`, `org_id`, `location_id`, `price_cents`, `currency`, `available`, `sort_order` | Merchant-controlled; no trust in client price |
| `requests` | `id`, `org_id`, `location_id`, `qr_spot_id`, `type`, `status`, `version`, `created_at`, `completed_at` | Server validates transition; idempotency key |
| `request_items` | `id`, `org_id`, `request_id`, `catalog_item_id`, `quantity`, `quoted_price_cents` | Server creates authoritative snapshot |
| `guest_sessions` | `id`, `org_id`, `qr_spot_id`, `secret_hash`, `expires_at` | Anonymous, time-limited, secret never in URLs/logs |
| `request_events` | `id`, `org_id`, `request_id`, `actor_id`, `type`, `at` | Audit + history |
| `scan_events` | `org_id`, `location_id`, `qr_spot_id`, `day`, `count` or privacy-aware events | Short retention / data minimization |
| `subscriptions` | `org_id`, `stripe_customer_id`, `stripe_subscription_id`, `plan`, `state`, `period_end` | Stripe event is source of truth for billing status |
| `integrations` | `org_id`, `provider`, `scopes`, `status`, `secret_ref` | Encrypted credentials / server secrets |
| `audit_log` | `org_id`, `actor_id`, `action`, `created_at`, `details` | Protected, minimally scoped |

Indexes: every tenant-owned major table indexed on `(org_id, ...)`; requests by `(org_id, location_id, status, created_at DESC)`; QR by `public_token`; event rollups by date and location.

### Tenant isolation and permissions

- Deny by default. Every merchant query scopes to organization membership and location permissions.
- Never accept an arbitrary `org_id` from a request body without verifying ownership/role server-side.
- Public guest writes flow through rate-limited server APIs; anonymous clients cannot read `requests` tables directly.
- Guest request status requires an opaque scoped session credential with expiry; not just `request_id`.
- Use PostgreSQL RLS for defense in depth, tested with authenticated User A / User B / anonymous permutations.
- App administrators shouldn't be tenant data superusers in regular app code.
- Staff can update only allowed request status transitions; price/catalog editing is manager/owner-only.
- Request lifecycle protected against double submissions, concurrent state changes and replay attacks.
- Stripe and POS webhooks require signature verification plus event de-duplication.
- Public QR tokens must be random, revocable and validated; a code does **not** authenticate a guest to see private data.
- CSRF protection as appropriate, XSS-safe rendering, CSP, TLS, security headers, secrets separation, rate limits, spam abuse mitigation, backups, incident response.

## API contract (example)

```text
POST /api/onboarding/business                  owner auth; create tenant via transactional server flow
POST /api/locations/:locationId/spots          manager auth; mint unique public token
GET  /api/public/experience/:publicToken      public; sanitized, published config
POST /api/public/requests                      public; validated body + guest session + rate limit + idempotency key
GET  /api/public/requests/:id/status           guest auth; scoped token
GET  /api/app/requests                         staff auth + tenant/location scope
POST /api/app/requests/:id/accept               staff auth + transition validation
POST /api/app/requests/:id/complete             staff auth + transition validation
POST /api/app/catalog                           manager auth
POST /api/billing/create-checkout               owner auth; Stripe server-side
POST /api/webhooks/stripe                       signature verify + event dedupe
GET  /api/app/metrics                           owner/manager auth; tenant-scoped aggregates
```

### QR format and design

- Printable QR code should point to stable short `https://yourdomain.com/q/{random_public_token}`.
- Token resolves to published experience and `qr_spot`; avoid merchant names and table IDs as the sole access secret.
- Generate actual vector SVG and high-DPI PNG, contrast verified, quiet zone, printed sign instructions.
- Print marketing copy "SCAN TO ORDER / REQUEST HELP" matched to real functionality.
- Rotate and deactivate compromised/scribbled codes; log potential fraudulent scans with minimal tracking.
- For NFC use the same HTTPS deep link, not a special codepath.

## Visual system and motion direction

**Brand direction (provisional):** cinematic midnight ink, cream/gold highlights, lavender/plum gradients and subtle glass. Not a generic green dashboard. Use visual richness in discovery and onboarding, but reduce weight on customer pages so they load on slow connections.

- Product shell: compact left nav on desktop, single-level nav on mobile.
- Primary screens: Welcome, Experience Builder, QR Spots, Live Queue, Catalog, Analytics, Billing, Admin.
- Guest: visual hero → contextual 3-action row → featured products → request/cart → status.
- Animations: optional first-visit logo reveal, elegant card entrance, glowing button hover, subtle 3D illustration. Never repeat a five-second intro every time a customer scans; no forced animation while staff need urgent service.
- i18n: localization-ready strings and timezones in v1 architecture; ship English first, Spanish once audited and supported by the business.

## Monetization experiment

These are **hypotheses**, not market-validated prices:

| Tier | Candidate price | Limits and value |
| --- | --- | --- |
| Launch | $49/month | 1 location, 5 QR spots, catalog, requests lite |
| Grow | $99/month | 1 location, expanded QR spots, staff queue, branded templates, standard analytics |
| Expand | $199/month | Multiple locations, advanced analytics, support and supported integrations |

- Consider a one-time onboarding/setup charge only for manual migration, photography, print kits or custom branding.
- Never claim unlimited physical usage if cloud or support costs could spike; apply a clear fair-use cap.
- Stripe, payment processing, hosting, email/SMS, support, storage, tax, integration access and AI API costs reduce margin.
- Do *not* take a transaction cut for restaurant food payments in the MVP; keep payments out of initial scope.
- First sell a pilot with a written scope and performance goals before assuming high monthly retention.

## Pilot success criteria / KPIs

**Activation:** owner configures a spot and scans it with a real phone in under 15 minutes after account verification.

**Guest conversion:** 80%+ of pilot test guests reach menu/help in two taps or fewer; report actual measured number.

**Operations:** request appears to staff in a few seconds under normal connection; handle reconnect and degraded network gracefully.

**Trust:** zero known cross-tenant data leaks; RLS negative tests pass; QR cannot access a private order/account by guessing URL.

**Reliability:** no duplicate service request after impatient double tap; no duplicate payment (future).

**Business case:** ask pilot partner whether staff actually saved time or handled service faster, and if they would pay the expected monthly price.

## Suggested build order

**Sprint 1 — foundation**
- Repo, lint/format/test, Next.js app shell, database migrations, auth, tenant/location roles, route architecture, basic design system, staging deploy.

**Sprint 2 — core guest journey**
- Experience schema, catalog builder, QR spot issuance and print assets, public QR entry page, request creation and guest status polling, validation and idempotency.

**Sprint 3 — staff and analytics**
- Realtime queue, accept/complete flow, role testing, analytics event rollups, mobile smoke tests, accessibility pass.

**Sprint 4 — sellable pilot**
- Stripe Billing + webhooks, plan gates, invited pilot onboarding, customer/staff testing in physical environment, instrument errors, privacy policy and support.

**Then:** Validate second and third sectors. Only after payment and usage proof, invest in 3D, POS or AI features. Timing is an estimate, not a guaranteed build schedule.

## Verification checklist

- [ ] Merchant A cannot read or modify Merchant B objects through UI, API, database policies or real-time channels.
- [ ] Anonymous QR request cannot create an arbitrary org/location entry or override price.
- [ ] QR revoked / subscription paused / spot disabled produce explicit safe states.
- [ ] Guest requests deduplicated; full and partial failures handled without false success.
- [ ] Staff cannot do manager-only edits; deactivated staff cannot rejoin channels.
- [ ] Request status updates reliable through refresh, reconnect and multi-tab scenarios.
- [ ] Billing activation and removal follow verified webhook events; plan switches work.
- [ ] Webhook retries, race conditions and double-delivery are safe.
- [ ] Forms validated at client and server; customer inputs cannot inject markup or scripts.
- [ ] Clear consent/privacy disclosures, analytics minimization, retention and deletion workflow.
- [ ] Tested on low-end Android / iPhone, slow network, keyboard, VoiceOver/TalkBack, reduced motion.
- [ ] Printed QR verified at multiple sizes and on different devices.
- [ ] Third-party integrations separately authorized and tested before marketing as live.

## TRIO and Toast integration caveat

Toast Standard API access is currently **read-only**; write access requires appropriate custom or partner access. Therefore, the MVP must not promise that pressing "Send" places an order directly into TRIO's Toast POS. Staff service requests and an independent demo queue are an acceptable first pilot, with permission from the restaurant. Toast's access models are documented at:
- https://doc.toasttab.com/doc/devguide/apiIntegrationTypes.html
- https://support.toasttab.com/en/article/Standard-API-Access

Alternative future integrations should use official vendor-approved paths; e.g. Square offers Orders API and OAuth, with limitations and fees to review.

## Artifact inventory

- `index.html`: self-contained, responsive **interactive prototype**. No framework build step or API key needed.
- `SCENE_PLATFORM_BLUEPRINT.md`: this production product/architecture document.
- `README.md`: how to run and what is/isn't implemented.

**Critical limitation:** the HTML demo uses browser `localStorage` only. It has no tenant security, accounts, scannable production QR, shared realtime backend, payments, subscription processing, printed codes or live integrations. Use it to demonstrate/sell the concept and validate screens, not to handle real guests.
