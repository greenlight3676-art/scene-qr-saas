-- Scene QR: indexes for Supabase's 16 unindexed-FK findings (2026-10-27).
-- Apply in a controlled maintenance window after reviewing existing indexes.
-- CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
-- These indexes do not alter rows or RLS policies.
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_audit_actor ON public.audit_events(actor_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_business_owner ON public.businesses(owner_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_growth_request ON public.growth_jobs(business_id,request_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_guest_business ON public.guest_sessions(business_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_guest_business_station ON public.guest_sessions(business_id,station_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_guest_station ON public.guest_sessions(station_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_mail_business ON public.mail_outbox(business_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_mail_business_invite ON public.mail_outbox(business_id,invite_hash);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_request_customer ON public.requests(business_id,customer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_request_product_tenant ON public.requests(business_id,product_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_request_station_tenant ON public.requests(business_id,station_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_request_product ON public.requests(product_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_request_station ON public.requests(station_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_scan_station_tenant ON public.scans(business_id,station_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_scan_station ON public.scans(station_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS scene_idx_session_user ON public.sessions(user_id);
