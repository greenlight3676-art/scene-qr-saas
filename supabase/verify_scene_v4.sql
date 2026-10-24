BEGIN;
SET LOCAL search_path=public,pg_catalog;
INSERT INTO users(id,email,password,created_at) VALUES (-901,'scene-rls-a@example.invalid','synthetic-no-login',0),(-902,'scene-rls-b@example.invalid','synthetic-no-login',0);
INSERT INTO businesses(id,owner_id,name,slug,industry,created_at) VALUES (-901,-901,'Synthetic A','scene-rls-test-a','automotive',0),(-902,-902,'Synthetic B','scene-rls-test-b','automotive',0);
INSERT INTO products(id,business_id,name) VALUES (-901,-901,'Synthetic A'),(-902,-902,'Synthetic B');
INSERT INTO stations(id,business_id,label,code,token,created_at) VALUES (-901,-901,'A','A','synthetic-qr-a',0),(-902,-902,'B','B','synthetic-qr-b',0);
INSERT INTO requests(id,business_id,station_id,kind,receipt_hash,client_key,created_at,updated_at) VALUES (-901,-901,-901,'service','synthetic-receipt-a','test-a',0,0),(-902,-902,-902,'service','synthetic-receipt-b','test-b',0,0);
SET LOCAL ROLE scene_runtime;
DO $$ DECLARE n integer; BEGIN
IF (SELECT count(*) FROM products)<>0 OR (SELECT count(*) FROM requests)<>0 THEN RAISE EXCEPTION 'Unscoped access leak'; END IF;
IF has_schema_privilege(current_user,'public','CREATE') THEN RAISE EXCEPTION 'Runtime can create schema objects'; END IF;
IF EXISTS (SELECT 1 FROM pg_roles WHERE pg_has_role(current_user,oid,'MEMBER') AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole)) THEN RAISE EXCEPTION 'Privileged role inheritance'; END IF;
PERFORM set_config('scene.tenant_id','-901',true);
IF (SELECT count(*) FROM products)<>1 OR (SELECT count(*) FROM requests)<>1 THEN RAISE EXCEPTION 'Own tenant access failed'; END IF;
UPDATE products SET name='Forbidden' WHERE id=-902;
GET DIAGNOSTICS n=ROW_COUNT;
IF n<>0 THEN RAISE EXCEPTION 'Cross-tenant update'; END IF;
BEGIN
INSERT INTO products(id,business_id,name) VALUES (-903,-902,'Forbidden');
RAISE EXCEPTION 'Cross-tenant insert accepted';
EXCEPTION WHEN insufficient_privilege THEN NULL; END;
BEGIN
UPDATE products SET business_id=-902 WHERE id=-901;
RAISE EXCEPTION 'Tenant reassignment accepted';
EXCEPTION WHEN insufficient_privilege THEN NULL; END;
BEGIN
INSERT INTO requests(id,business_id,station_id,product_id,kind,receipt_hash,client_key,created_at,updated_at) VALUES (-903,-901,-901,-902,'service','synthetic-bad','test-bad',0,0);
RAISE EXCEPTION 'Cross-tenant product reference accepted';
EXCEPTION WHEN foreign_key_violation THEN NULL; END;
UPDATE products SET name='Allowed synthetic update' WHERE id=-901;
GET DIAGNOSTICS n=ROW_COUNT;
IF n<>1 THEN RAISE EXCEPTION 'Own tenant update failed'; END IF;
BEGIN
UPDATE audit_events SET action='forbidden';
RAISE EXCEPTION 'Audit mutable';
EXCEPTION WHEN insufficient_privilege THEN NULL; END;
BEGIN
DELETE FROM auth_identities;
RAISE EXCEPTION 'Identity binding deletion allowed';
EXCEPTION WHEN insufficient_privilege THEN NULL; END;
BEGIN
INSERT INTO auth_identities(subject,user_id) VALUES ('synthetic-unverified',-901);
RAISE EXCEPTION 'Unverified identity insert accepted';
EXCEPTION WHEN insufficient_privilege THEN NULL; END;
PERFORM set_config('scene.tenant_id','',true);
PERFORM set_config('scene.receipt_hash','synthetic-receipt-a',true);
IF (SELECT count(*) FROM requests)<>1 THEN RAISE EXCEPTION 'Private receipt lookup failed'; END IF;
PERFORM set_config('scene.receipt_hash','',true);
PERFORM set_config('scene.qr_token','synthetic-qr-b',true);
IF (SELECT count(*) FROM stations)<>1 OR (SELECT count(*) FROM requests)<>0 THEN RAISE EXCEPTION 'QR capability leaked private requests'; END IF;
END $$;
RESET ROLE;
SET LOCAL ROLE anon;
DO $$ BEGIN
BEGIN PERFORM 1 FROM users LIMIT 1; RAISE EXCEPTION 'Anonymous users exposed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
BEGIN PERFORM 1 FROM requests LIMIT 1; RAISE EXCEPTION 'Anonymous requests exposed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
SET LOCAL ROLE authenticated;
DO $$ BEGIN
BEGIN PERFORM 1 FROM customers LIMIT 1; RAISE EXCEPTION 'Authenticated direct customers exposed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
BEGIN PERFORM 1 FROM sessions LIMIT 1; RAISE EXCEPTION 'Authenticated direct sessions exposed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
ROLLBACK;
SELECT 'passed: tenant isolation, mutation denial, foreign keys, capability access, audit immutability, browser denial; synthetic fixtures rolled back' AS verification;