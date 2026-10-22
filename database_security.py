"""Explicit database-owner hardening; no hosted changes run on application startup.

Run with SCENE_MIGRATION_DATABASE_URL and --runtime-role after reviewing the plan.
The backend role is trusted to authenticate users; browser roles get no policies.
"""
import argparse
import os
from storage import connect, verify_runtime_role
from migrate import TABLES


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
    for table in (*TABLES, 'scene_migrations'):
        target = sql.Identifier(schema, table)
        owner = raw.execute('SELECT pg_get_userbyid(relowner) AS name FROM pg_class WHERE oid=%s::regclass', (f'{schema}.{table}',)).fetchone()['name']
        if owner == runtime_role:
            raise RuntimeError('Backend must not own application tables')
        raw.execute(sql.SQL('ALTER TABLE {} ENABLE ROW LEVEL SECURITY').format(target))
        # Reject unknown pre-existing policies rather than silently retaining a leak.
        policies = raw.execute('SELECT policyname FROM pg_policies WHERE schemaname=%s AND tablename=%s', (schema, table)).fetchall()
        allowed = ('scene_backend', 'scene_receipt') if table == 'requests' else ('scene_backend',)
        if any(p['policyname'] not in allowed for p in policies):
            raise RuntimeError('Review existing policies before hardening')
        raw.execute(sql.SQL('DROP POLICY IF EXISTS scene_backend ON {}').format(target))
        predicate = sql.SQL("business_id::text = current_setting('scene.tenant_id', true)") if table == 'requests' else sql.SQL('true')
        raw.execute(sql.SQL('CREATE POLICY scene_backend ON {} TO {} USING ({}) WITH CHECK ({})').format(target, sql.Identifier(runtime_role), predicate, predicate))
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
