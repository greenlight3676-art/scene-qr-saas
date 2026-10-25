# Customer workflows

This release adds a Today screen, guided setup, a separate customer pipeline, private receipt quotes, follow-up dates, placement outcomes and customer return links. Owners/managers manage customer jobs; staff retain the service queue and Today actions. Existing printed QR tokens and request statuses are preserved.

## Deployment order

1. Apply `migrations/growth_postgres.sql` to the existing database with the migration-owner role. It adds two tables and an index, grants the existing runtime role scoped access, and revokes browser-role access. It does not modify customer records or change schema version 4.
2. Deploy the backend containing `growth.py` and the updated Docker copy list. Startup verifies RLS on both new tables.
3. Deploy the Sites frontend. The new API routes are backward compatible with the previous frontend.

Rollback: deploy the previous backend/frontend version and keep the additive tables. Do not drop tables containing customer data. A new environment must apply the original migrations and this supplemental migration before startup.

## Behavior and limits

- Inquiries retain their original request IDs and QR placement. Job stages are separate from service status; recording Won does not mark the staff request Done or collect a payment.
- Quotes require scope, USD amount and future expiry before the Quoted stage. Guests can respond only with their private receipt. Quote edits reset acceptance; revision checks reject stale edits and stale quote responses. Booking is manually confirmed by the business; there is no availability calendar, automatic scheduling or payment capture.
- In-app alerts run while the workspace is open. There is no background push, email/SMS delivery or automated outreach in this release. Return/follow-up drafts are reviewed and copied by the owner, and contact consent is surfaced. Booking/review links appear to all completed-receipt holders, without filtering by sentiment.
- Revenue is explicitly team-recorded on Won jobs, not a processor-verified payment or causal attribution claim. Missing revenue is counted separately. Page-load counts include previews, refreshes and repeat visitors.
- Pipeline lists are paginated. Today uses the existing recent-250 request snapshot for in-progress/aged counts and labels that limit. New-request counts use the existing full backend aggregate.
- Profiles select a suggested campaign flow; tint mode preselects the vehicle/tint form. Owners provide actual services, offers, photos, proof and prices.

## Validation

83 backend tests passed; 27 opt-in/environment tests skipped. 70 frontend tests passed. Isolated browser review covered desktop customer editing/save, setup, results, mobile navigation and 360px form fit. Database tenant read/write and browser-grant checks used temporary fixtures in a rolled-back transaction; no production customer data was changed.

PostgreSQL transaction review: authenticate and apply durable rate limits before opening the scoped business transaction. Regression checks reject nested database transactions, which would self-block the PostgreSQL advisory lock.
