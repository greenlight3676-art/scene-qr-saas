# TRIOS Restaurant Edition — Scene QR integration

Goal: a TRIOS-branded tenant using the existing Scene QR service, NOT a separate backend.

## Demo route
- /trios (branded landing/menu); /trios/table/:stationToken (guest)
- /trios/staff (authenticated team queue); /trios/owner (authenticated dashboard)
- All tenant-scoped reads/writes must resolve organization_id server-side; never trust arbitrary organization IDs supplied by guests.
- Reuse existing station tokens, request creation, receipt polling, owner/manager roles, audit events and rate limits.

## Guest
- TRIOS name, warm gold/charcoal theme, responsive menu.
- QR scan identifies station/table and offers: Call server, Water, Napkins, Check.
- On submit: persisted request ID and status, then receipt tracks New -> In progress -> Done.
- No login needed for guest; prohibit customer data from seeded demo.

## Staff
- Authenticated staff sees only TRIOS requests; table, type, elapsed time, status.
- Start and Done actions persist and reflect on guest receipt.
- Realtime if available; otherwise reliable polling and reconnect handling.

## Owner
- TRIOS-specific QR station management, menu catalog, team roles, requests and activity.
- Do not expose other tenants. No fabricated analytics.

## Deferred integrations
- Menu orders, kitchen routing, shared tabs, Toast/POS, and payment settlement must remain labeled Demo/Coming soon until backed by working, verified integrations.
- No fake checkout or payment confirmations.

## Acceptance demo
1. Owner creates TRIOS workspace and Table 01 station.
2. Phone A scans QR and requests water.
3. Staff phone B sees request for Table 01.
4. Staff taps Start then Done.
5. Phone A receipt updates to Done.
6. Second organization's staff cannot view or mutate TRIOS data.
7. Refresh/reconnect retains request state.

## Deployment
Keep existing Scene QR homepage and customers unchanged. Build in feature branch, test on mobile, deploy preview before production.