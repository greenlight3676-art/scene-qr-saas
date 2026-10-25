# Scene QR — Graphite review

## Direction and scope

Implements the user-supplied Lundy Design Studio reference for Scene QR. Midnight graphite, ivory, bronze, restrained plum/teal. The public page is structured around an interactive scan → request → staff completion explanation. The sample is labeled and performs no live writes. The authenticated workspace and guest pages retain the existing Render API/Supabase contracts.

Semantic styles, consistent branding, readable operational labels, smaller guest headers, service icons, mobile navigation focus management, modal background isolation, and useful guest load/retry states are implemented. Closing the account dialog now removes background inertness before restoring focus. Receipt polling still synchronizes text, semantic status, and persisted state.

This version is saved for design review. It does **not** replace the public production version. The user's reference requires permission before publishing. No billing, database, Render configuration, access policy, prices or customer data were changed.

## Verified coverage

| Route / flow | Evidence | Severity | Status / next step |
|---|---|---|---|
| Public landing / walkthrough | Actual browser: scan → request receipt → staff Start → Mark done; receipt indicator Done. Sample-only code makes no API writes. | None observed | Pass |
| Public landing / responsive | Browser iframe viewport review at 320, 375, 390, 768, 1024, 1440px; document width equals available viewport width at all six. Vertical scrollbar consumes 15px. | None observed | Pass for horizontal overflow; physical devices remain untested |
| Guest QR → request → receipt refresh → staff completion | Actual disposable local FastAPI/SQLite demo backend; Call server created request #1; receipt survived reload; staff Start/Mark done updated guest receipt to Done. | None observed | Pass locally; no production ticket created |
| Guest unavailable QR / retry | Invalid local QR displays a direct explanation, Try again and staff-help guidance; retry returns to the same useful failure state. | P1 fixed | Pass |
| Staff screens | Actual local browser visited Overview, Queue, Catalog, QR stations, Analytics, Brand, Team access; all rendered expected headings without desktop horizontal overflow. | None observed | Visual/navigation pass; not a new exhaustive write test of every admin form |
| Account dialog | Background becomes inert; Escape closes dialog and returns focus to Create workspace. Added regression verifies background activation precedes focus restoration. | P1 fixed | Pass |
| Mobile navigation | 320px browser iframe: focus moves to Close menu, Shift+Tab wraps from first link to Sign out, Tab wraps back, Escape closes and returns focus to Open navigation; closed rail removed from accessibility tree. | P1 fixed | Pass |
| Color contrast | 12 named text/control pairs meet 4.5:1 text or 3:1 control/focus thresholds. Body 16.80:1, muted 8.06:1, primary 9.34:1, guest body 13.06:1, guest description 5.62:1, guest control outlines 3.52/3.76:1. Existing tests cover dynamic business-accent contrast. | P2 fixed | Selected pairs pass; not a whole-page automated WCAG certification |
| Frontend / proxy regressions | 57 Node tests passed: submission, duplicates, partial failure, consent, revoked access, receipt privacy/status, paging, email callbacks, QR URLs/downloads, proxy boundaries, sample walkthrough, focus order, selected contrast pairs. | None observed | Pass |
| Backend regression | 79 pytest tests passed; 26 opted-in/environment-specific tests skipped. No backend source/schema changes in this review. | None observed | Pass for executed tests |
| Packaging | JS syntax checks; bundled Worker build and artifact validation. | None observed | Pass when accompanying saved version is created |

## Unverified limits / release grading

- 200% browser zoom and enlarged OS text: unverified. Operational font sizes now use rem; layouts and dialogs remain fluid/scrollable, but that is implementation evidence, not a measured zoom test.
- Physical iPhone, low-performance phone, tablet rotation, and software keyboard: not tested in this cloud environment.
- Screen-reader speech and full keyboard-only traversal of every admin form: not completed. Semantic labels and live regions remain present; targeted dialog/menu tests passed.
- Slow-network/offline timing, expired real email links and production authenticated owner flows: not retested. Existing Node regression coverage is retained. Guest unavailable/retry was tested in the real browser.
- Field Core Web Vitals and lab LCP/INP/CLS: not measured. No audit score or performance-compliance claim is made.
- New production email delivery, Stripe, POS and confirmed bookings are outside this change and are not claimed as integrated.
- Existing shared design PR #2 is open and unmerged; this change does not assume it is present in main.

**Review status:** ready for visual approval and further device testing. **Release status:** not approved/published; production retains the previously published version.
