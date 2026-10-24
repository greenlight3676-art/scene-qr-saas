# Scene QR frontend

Sites serves Scene QR and proxies app requests to the fixed Render backend at https://scene-qr-api.onrender.com. Supabase remains the application datastore. Only Scene cookies and required application headers reach Render. Database credentials, Sites tokens, and private customer data are not bundled.

## Scene Studio release

A plum-and-copper product page introduces the actual scan → request → staff flow. A clearly labeled interactive walkthrough and four industry examples work without an account or backend writes. Staff use a light workspace framed by a plum navigation rail. Guests receive branded mobile pages, consistent service icons, readable controls, and private request receipts. Receipt polling now keeps visual status synchronized with its text and persisted state.

Auth, catalog editing, QR download and rotation, request filters/history, team permissions and brand autosave retain their API contracts. The site is public as explicitly requested; staff operations remain protected by app authentication and backend authorization. Billing remains excluded.

## Source and checks

Editable assets live in `frontend/`; `node scripts/bundle-frontend.mjs` generates `worker/assets.js`. Run `node --test scripts/*.test.*`, `bash scripts/build.sh`, and `node scripts/validate-artifact.mjs`. The deployment contains only the bundled Worker and hosting manifest. Development adapters, dependencies and local test databases are excluded.

Verified for this release: 44 Node checks; 79 backend tests (26 environment/opt-in tests skipped); browser review of desktop and phone layouts; real isolated local guest request → staff Start → Mark done → guest Done. The local QA adapter's cookie forwarding was repaired so authenticated preview can run. Production business data was not used or modified for this check.

The local-only `/__qa?width=375` route provides a narrow iframe for layout inspection. Optional `.scene-preview-backend` and ignored `.qa/` enable an isolated local backend for QA; neither is shipped. There is no hosted demo account or synthetic merchant fixture in the production bundle.
