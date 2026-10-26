-- Development only: requires an empty schema; never use to roll back business data.
DROP TABLE IF EXISTS growth_jobs, growth_settings;
ALTER TABLE requests DROP CONSTRAINT IF EXISTS request_customer_tenant;
ALTER TABLE stations DROP CONSTRAINT IF EXISTS station_location_tenant;
DROP TABLE IF EXISTS mail_outbox, guest_sessions, customers, locations, rate_buckets, auth_flows, auth_blocks, billing_accounts, billing_events;
DROP TABLE IF EXISTS audit_events, auth_identities;
DROP TABLE scans, invites, sessions, requests, products, stations, memberships, businesses, users, scene_migrations;
