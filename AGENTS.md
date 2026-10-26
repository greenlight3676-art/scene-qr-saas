# SCENE QR — Codex engineering instructions

## Product and goal
SCENE QR is a multi-tenant, industry-configurable SaaS for QR-powered experiences at restaurants, barbershops, automotive services, and stores. Guests scan a QR code without signing in; employees handle requests; each business manages branding, catalog, QR spots and staff. TRIO is a fictionalized restaurant pilot in demo data, not an authorized production merchant. Keep this ONE shared platform with templates rather than making separate applications.

## Source of truth
- `README.md`: verified current capabilities and how to run the beta.
- `SCENE_PLATFORM_BLUEPRINT.md`: product plan and desired architecture.
- `DEPLOYMENT_CHECKLIST.md`: conditions before any public or commercial rollout.
- `CODEX_TASKS.md`: prioritized scope. Complete one phase/PR at a time.
- `server.py`, `static/*`, `tests/test_api.py`: currently working FastAPI + SQLite implementation. Avoid unrelated rewrites.

## First actions on every assignment
1. Read these instructions and the relevant source files before editing.
2. Run `python3 -m pytest -q tests` (after installing `requirements.txt` + `requirements-dev.txt`) and `node --check static/app.js` if Node is installed. Record baseline failures, do not assume tests pass.
3. Make the smallest safe changes needed; add appropriate tests, especially negative authorization tests.
4. Run tests again and report changes, remaining risks, and manual verification steps.
5. For sweeping migrations, first produce a transition plan, keep the existing app runnable, and avoid destructive data operations without explicit authorization.

## Mandatory security rules
- Treat organization membership and role authorization as server-side checks on EVERY private operation; new queries must be tenant-scoped. Test tenant A cannot read or mutate tenant B resources.
- Public QR tokens are **not** authentication. No private customer or employee data should be exposed by scanning a QR code.
- Never include passwords, payment tokens, API keys, `.env`, or real customer data in commits, logs, screenshots or tests. `.env.example` contains placeholders only.
- Demo users/passwords and `SCENE_DEMO=1` are strictly local. Never activate demo mode in deployed environments. Use actual deployment env only in secure host settings.
- Do not call an unauthenticated guest request a paid order, confirmed reservation, or delivered POS ticket. POS/Toast/payment integration requires real merchant authorization, credentials and external testing.
- Account for CSRF, rate limits, idempotency, input validation, status transitions, audit trails and privacy during changes.
- Database migrations must be reversible/tested; support existing beta data unless explicitly approved to discard it.

## Product / quality rules
- Guest views must be mobile-first, accessible, fast to open from a QR scan, and require no signup. Respect `prefers-reduced-motion`.
- Premium visual direction: cinematic but readable, warm ivory/plum/bronze accents, smooth purposeful animations; do not sacrifice usability for animation.
- Prefer clear modular code and automated tests over giant one-shot rewrites. Fix bugs first, then add features.
- Use only sample merchant data and accurate product copy; do not invent TRIO menu items, pricing, or integration permissions.
- Maintain compatibility with existing URL contracts during incremental refactors when practical.
- Treat existing UI screenshot PNGs as *references*; they are not proof of production readiness.

## Working definition of done
- Updated implementation is runnable, syntax-valid and covered by relevant tests.
- Authorization, tenant-isolation, guest privacy and abuse cases have negative tests.
- Docs updated for installation, env vars, migration and deployment.
- No secret or SQLite runtime DB accidentally committed.
- Explain what is simulated versus truly integrated, and list remaining production blockers.

## Reusable design skills
When changing frontend layout, flows, copy, animation, accessibility, or preparing a demo, consult the matching skills in `.agents/skills/`:
- `premium-product-design`: coherent design systems and page hierarchy.
- `cinematic-motion-and-materials`: purposeful movement, transitions and glass-like overlays.
- `business-flow-ux-and-microcopy`: onboarding, QR requests, dashboard flows and copy.
- `inclusive-responsive-frontend`: accessibility, mobile, internationalization and performance.
- `premium-release-audit`: interactive QA before demos or client handoff.
- `higgsfield-commercial-director`: plan credible Higgsfield marketing videos with sales-first demonstrations, time-coded shot plans, source media continuity, and limited-credit preflight; see its Scene QR commercial reference.
Keep these skills subordinate to the security rules, working functionality, test requirements, and no-unauthorized-deployment constraints above.
