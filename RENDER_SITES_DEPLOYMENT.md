# Render + Sites beta deployment

The existing Python backend runs on Render (scene-qr-api), with Supabase schema v4 and a restricted scene_runtime LOGIN role. Sites hosts the existing frontend and forwards app API calls over HTTPS, retaining only Scene application cookies. Runtime credentials are stored only in Render environment settings. Never commit or print their values.

The Docker image contains the public Supabase Root 2021 CA retrieved from the certificate link in Supabase Database Settings. Its SHA-256 fingerprint is 807025AD50D4ED219D2C9C7D299C004F824EB00CF7F65AFEF607D07B72E6CAFA. Runtime PostgreSQL uses sslmode=verify-full and /app/certs/supabase-prod-ca.crt via the session pooler.

For this explicitly requested pilot without Stripe, set SCENE_PILOT_WITHOUT_BILLING=1 and SCENE_REQUIRE_SUBSCRIPTION=0. All production Auth, database, secure-cookie, explicit-host and guest-session requirements remain mandatory. The default still requires subscriptions. This pilot grants unpaid guest request access to every onboarded business; it is not a paid subscription release.

Sites remains owner-private. Render Free can sleep on idle. Custom SMTP, real signup/reset email acceptance and hosted backup/restore remain outstanding. Do not claim commercial launch readiness from a passing readiness endpoint.
