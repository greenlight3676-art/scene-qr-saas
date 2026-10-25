-- Additive customer workflows. Apply before deploying growth.py. Existing v4 runtime remains compatible.
BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS idx_request_growth_tenant ON public.requests(business_id,id);
CREATE TABLE IF NOT EXISTS growth_settings(business_id BIGINT PRIMARY KEY REFERENCES businesses(id),
       profile TEXT NOT NULL DEFAULT 'general', review_url TEXT NOT NULL DEFAULT '', booking_url TEXT NOT NULL DEFAULT '',
       setup_complete BIGINT NOT NULL DEFAULT 0, updated_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS growth_jobs(request_id BIGINT PRIMARY KEY, business_id BIGINT NOT NULL REFERENCES businesses(id),
       stage TEXT NOT NULL CHECK(stage IN ('new','contacted','quoted','booked','won','lost','archived')),
       quote_cents BIGINT, quote_description TEXT NOT NULL DEFAULT '', quote_expires BIGINT,
       quote_revision BIGINT NOT NULL DEFAULT 0, accepted_revision BIGINT,
       appointment_at BIGINT, followup_at BIGINT, revenue_cents BIGINT,
       note TEXT NOT NULL DEFAULT '', revision BIGINT NOT NULL DEFAULT 1, updated_at BIGINT NOT NULL,
       FOREIGN KEY(business_id,request_id) REFERENCES requests(business_id,id));
CREATE INDEX IF NOT EXISTS idx_growth_followup ON growth_jobs(business_id,followup_at);
ALTER TABLE public.growth_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.growth_jobs FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.growth_jobs FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.growth_jobs TO scene_runtime;
CREATE POLICY scene_backend ON public.growth_jobs TO scene_runtime USING (business_id::text=current_setting('scene.tenant_id',true)) WITH CHECK (business_id::text=current_setting('scene.tenant_id',true));
ALTER TABLE public.growth_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.growth_settings FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.growth_settings FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.growth_settings TO scene_runtime;
CREATE POLICY scene_backend ON public.growth_settings TO scene_runtime USING (business_id::text=current_setting('scene.tenant_id',true)) WITH CHECK (business_id::text=current_setting('scene.tenant_id',true));
COMMIT;
