"""Explicit database-owner hardening; no hosted changes run on application startup.

Run with SCENE_MIGRATION_DATABASE_URL and --runtime-role after reviewing the plan.
The backend role is trusted to authenticate users; browser roles get no policies.
"""
import argparse
import os
from storage import connect, verify_runtime_role
from migrate import TABLES, SECURITY_TABLES
from backend_schema import TABLES as BACKEND_TABLES, TENANT_TABLES


def harden(raw, runtime_role):
    from psycopg import sql
    role = raw.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=%s', (runtime_role,)).fetchone()
    if role is None or any(role.values()) or runtime_role in ('anon', 'authenticated', 'service_role'):
        raise RuntimeError('A dedicated restricted backend role is required')
    verify_runtime_role(raw, runtime_role)
    for browser_role in ('anon', 'authenticated'):
        if raw.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (browser_role,)).fetchone():
            if raw.execute("SELECT pg_has_role(%s,%s,'MEMBER') AS inherits", (browser_role,runtime_role)).fetchone()['inherits']:
                raise RuntimeError('Browser roles must not inherit backend access')
    schema = raw.execute('SELECT current_schema() AS name').fetchone()['name']
    for table in (*TABLES, *SECURITY_TABLES, *BACKEND_TABLES, 'growth_jobs', 'growth_settings', 'scene_migrations'):
        target = sql.Identifier(schema, table)
        owner = raw.execute('SELECT pg_get_userbyid(relowner) AS name FROM pg_class WHERE oid=%s::regclass', (f'{schema}.{table}',)).fetchone()['name']
        if owner == runtime_role:
            raise RuntimeError('Backend must not own application tables')
        raw.execute(sql.SQL('ALTER TABLE {} ENABLE ROW LEVEL SECURITY').format(target))
        # Reject unknown pre-existing policies rather than silently retaining a leak.
        policies = raw.execute('SELECT policyname FROM pg_policies WHERE schemaname=%s AND tablename=%s', (schema, table)).fetchall()
        allowed = {'requests':('scene_backend','scene_receipt'),
                   'stations':('scene_backend','scene_capability'),
                   'invites':('scene_backend','scene_capability'),
                   'audit_events':('scene_backend','scene_audit_insert'),
                   'billing_accounts':('scene_backend','scene_billing_lookup'),
                   'auth_identities':('scene_backend','scene_identity_insert'),
                   'mail_outbox':('scene_backend','scene_mail_lookup')}.get(table,('scene_backend',))
        if any(p['policyname'] not in allowed for p in policies):
            raise RuntimeError('Review existing policies before hardening')
        raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_backend ON {}').format(target))
        predicate = sql.SQL("business_id::text = current_setting('scene.tenant_id', true)") if table in ('requests', 'products', 'stations', 'scans', 'invites', 'audit_events', *TENANT_TABLES,'growth_jobs','growth_settings') else sql.SQL('true')
        if table == 'auth_identities':
            raw.execute(sql.SQL('CREATE POLICY scene_backend ON {} FOR SELECT TO {} USING (true)').format(target, sql.Identifier(runtime_role)))
            raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_identity_insert ON {}').format(target))
            raw.execute(sql.SQL("CREATE POLICY scene_identity_insert ON {} FOR INSERT TO {} WITH CHECK (subject = current_setting('scene.auth_subject',true))").format(target, sql.Identifier(runtime_role)))
            raw.execute(sql.SQL('REVOKE UPDATE,DELETE,TRUNCATE ON {} FROM {}').format(target, sql.Identifier(runtime_role)))
        elif table == 'audit_events':
            raw.execute(sql.SQL('CREATE POLICY scene_backend ON {} FOR SELECT TO {} USING ({})').format(target, sql.Identifier(runtime_role), predicate))
            raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_audit_insert ON {}').format(target))
            raw.execute(sql.SQL('CREATE POLICY scene_audit_insert ON {} FOR INSERT TO {} WITH CHECK ({})').format(target, sql.Identifier(runtime_role), predicate))
        else:
            raw.execute(sql.SQL('CREATE POLICY scene_backend ON {} TO {} USING ({}) WITH CHECK ({})').format(target, sql.Identifier(runtime_role), predicate, predicate))
        if table == 'mail_outbox':
            raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_mail_lookup ON {}').format(target))
            raw.execute(sql.SQL("CREATE POLICY scene_mail_lookup ON {} FOR SELECT TO {} USING (current_setting('scene.mail_worker',true)='1')").format(target,sql.Identifier(runtime_role)))
        if table == 'billing_accounts':
            raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_billing_lookup ON {}').format(target))
            raw.execute(sql.SQL("CREATE POLICY scene_billing_lookup ON {} FOR SELECT TO {} USING (customer_id=current_setting('scene.billing_customer',true))").format(target,sql.Identifier(runtime_role)))
        if table in ('stations', 'invites'):
            field, setting = ('token', 'scene.qr_token') if table == 'stations' else ('token_hash', 'scene.invite_hash')
            raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_capability ON {}').format(target))
            raw.execute(sql.SQL("CREATE POLICY scene_capability ON {} FOR SELECT TO {} USING ({} = current_setting({}, true))").format(target, sql.Identifier(runtime_role), sql.Identifier(field), sql.Literal(setting)))
        if table == 'audit_events':
            raw.execute(sql.SQL('REVOKE UPDATE,DELETE,TRUNCATE ON {} FROM {}').format(target, sql.Identifier(runtime_role)))
        if table == 'requests':
            raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_receipt ON {}').format(target))
            raw.execute(sql.SQL("CREATE POLICY scene_receipt ON {} FOR SELECT TO {} USING (receipt_hash = current_setting('scene.receipt_hash', true))").format(target, sql.Identifier(runtime_role)))
        raw.execute(sql.SQL('REVOKE ALL ON {} FROM PUBLIC').format(target))
        for browser_role in ('anon', 'authenticated'):
            if raw.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (browser_role,)).fetchone():
                raw.execute(sql.SQL('REVOKE ALL ON {} FROM {}').format(target, sql.Identifier(browser_role)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-role', required=True)
    args = parser.parse_args()
    try:
        with connect(os.environ['SCENE_MIGRATION_DATABASE_URL']) as raw:
            harden(raw, args.runtime_role)
    except Exception:
        raise SystemExit('Hardening failed; transaction rolled back. Review roles and policies privately.') from None
    print('Database hardening completed.')
