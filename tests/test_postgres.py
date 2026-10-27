"""Requires a disposable PostgreSQL database; never point at business data."""
import os
import pytest
from migrate import migrate
from storage import connect, Connection

URL = os.getenv('SCENE_TEST_POSTGRES_URL')
pytestmark = pytest.mark.skipif(not URL, reason='Disposable PostgreSQL URL not configured')


def test_postgres_migration_adapter_and_tenant_constraints():
    import psycopg
    with connect(URL) as raw:
        assert raw.prepare_threshold is None  # Supavisor transaction-pooler compatibility.
        # Isolated schema, rolled back after test including all fixtures.
        try:
            raw.execute('CREATE SCHEMA scene_test')
            raw.execute('SET LOCAL search_path TO scene_test')
            migrate(raw)
            migrate(raw)  # repeatable migration
            c = Connection(raw)
            uid = c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)', ('fixture@example.invalid', 'not-a-password-hash', 1)).lastrowid
            businesses = [c.execute('INSERT INTO businesses(owner_id,name,slug,industry,created_at) VALUES(?,?,?,?,?)', (uid, name, name, 'auto', 1)).lastrowid for name in ('a', 'b')]
            a, b = businesses
            station = c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)', (b, 'Desk', 'desk', 'sample-token', 1)).lastrowid
            product = c.execute('INSERT INTO products(business_id,name) VALUES(?,?)', (b, 'Sample')).lastrowid
            local = c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)', (a, 'Desk', 'desk', 'sample-token-a', 1)).lastrowid
            for station_id, product_id in ((station, None), (local, product)):
                with pytest.raises(psycopg.errors.ForeignKeyViolation):
                    with raw.transaction():
                        c.execute('INSERT INTO requests(business_id,station_id,product_id,kind,receipt_hash,client_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)', (a, station_id, product_id, 'service', 'sample-hash', 'sample-key', 1, 1))
            result = c.execute('INSERT INTO requests(business_id,station_id,kind,receipt_hash,client_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?)', (a, local, 'service', 'sample-hash', 'valid-key', 1, 1))
            assert result.lastrowid
            row = c.execute('SELECT id,status FROM requests WHERE business_id=?', (a,)).fetchone()
            assert row[0] == row['id'] and dict(row)['status'] == 'open'
            raw.execute((__import__('pathlib').Path(__file__).resolve().parents[1] / 'migrations/001_down.sql').read_text())
            migrate(raw)  # empty-schema down/up
        finally:
            raw.rollback()


def test_import_preserves_data_sequences_and_source(postgres_schema, sqlite_snapshot):
    import hashlib
    import sqlite3
    from migrate import import_sqlite, TABLES, GROWTH_TABLES
    url, _ = postgres_schema
    original = hashlib.sha256(sqlite_snapshot.read_bytes()).hexdigest()
    with connect(url) as raw:
        migrate(raw)
        import_sqlite(raw, sqlite_snapshot)
        with sqlite3.connect(sqlite_snapshot) as old:
            for table in (*TABLES, *GROWTH_TABLES):
                cursor = old.execute(f'SELECT * FROM {table}')
                names = [col[0] for col in cursor.description]
                expected = [dict(zip(names, row)) for row in cursor]
                assert raw.execute(f'SELECT * FROM {table}').fetchall() == expected
        c = Connection(raw)
        assert c.execute('INSERT INTO products(business_id,name) VALUES(?,?)', (1, 'Next sample')).lastrowid == 3
        with pytest.raises(RuntimeError, match='empty PostgreSQL target'):
            import_sqlite(raw, sqlite_snapshot)
    assert hashlib.sha256(sqlite_snapshot.read_bytes()).hexdigest() == original


def test_existing_v4_adds_growth_without_changing_requests(postgres_schema):
    url, _ = postgres_schema
    with connect(url) as raw:
        migrate(raw)
        # Reproduce v4 databases created before the additive growth release.
        raw.execute('DROP TABLE growth_jobs, growth_settings')
        before = raw.execute('SELECT * FROM requests').fetchall()
        migrate(raw)
        raw.execute("INSERT INTO users(email,password,created_at) VALUES('growth@example.invalid','synthetic',1)")
        raw.execute("INSERT INTO businesses(owner_id,name,slug,industry,created_at) VALUES(1,'Synthetic','growth','auto',1)")
        raw.execute("INSERT INTO growth_settings(business_id,profile,updated_at) VALUES(1,'tint',1)")
        migrate(raw)
        assert raw.execute('SELECT * FROM requests').fetchall() == before
        assert raw.execute('SELECT profile FROM growth_settings').fetchone()['profile'] == 'tint'
        assert raw.execute('SELECT version FROM scene_migrations').fetchone()['version'] == 4


def test_invalid_import_rolls_back_all_rows(postgres_schema, sqlite_snapshot):
    import sqlite3
    import psycopg
    from migrate import import_sqlite, TABLES
    url, _ = postgres_schema
    # SQLite beta permits this legacy cross-business station reference.
    with sqlite3.connect(sqlite_snapshot) as old:
        old.execute('UPDATE requests SET station_id=2 WHERE id=1')
    with connect(url) as raw:
        migrate(raw)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with connect(url) as raw:
            import_sqlite(raw, sqlite_snapshot)
    with connect(url) as raw:
        for table in TABLES:
            assert raw.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n'] == 0
    # Rollback preserves the retained SQLite source, including the rejected row.
    with sqlite3.connect(sqlite_snapshot) as old:
        assert old.execute('SELECT station_id FROM requests WHERE id=1').fetchone()[0] == 2


def test_import_missing_source_and_nonempty_schema_are_safe(postgres_schema, tmp_path):
    import sqlite3
    from migrate import import_sqlite
    url, _ = postgres_schema
    with connect(url) as raw:
        raw.execute('CREATE TABLE users(id BIGINT PRIMARY KEY)')
        with pytest.raises(RuntimeError, match='empty application schema'):
            with raw.transaction():
                migrate(raw)
        assert raw.execute("SELECT to_regclass('scene_migrations') AS name").fetchone()['name'] is None
        assert raw.execute("SELECT to_regclass('users') AS name").fetchone()['name'] == 'users'
        with pytest.raises(sqlite3.OperationalError):
            import_sqlite(raw, tmp_path / 'missing.sqlite')
    assert not (tmp_path / 'missing.sqlite').exists()


def test_runtime_role_rejects_ddl_and_metadata_changes(postgres_schema):
    import psycopg
    from psycopg import sql
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote
    from storage import verify_postgres
    url, schema = postgres_schema
    role = schema + '_runtime'
    with connect(url) as raw:
        migrate(raw)
        raw.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(
            sql.Identifier(role), sql.Literal('disposable-runtime-only')))
        raw.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
        raw.execute(sql.SQL('GRANT SELECT ON scene_migrations TO {}').format(sql.Identifier(role)))
        from database_security import harden
        harden(raw, role)
    parsed = urlsplit(url)
    options = dict(parse_qsl(parsed.query))
    authority = quote(role, safe='') + ':disposable-runtime-only@' + parsed.netloc.rsplit('@', 1)[-1]
    runtime_url = urlunsplit(parsed._replace(netloc=authority, query=urlencode(options)))
    try:
        with connect(runtime_url) as raw:
            identity = raw.execute('SELECT current_user AS effective, session_user AS authenticated').fetchone()
            assert identity == {'effective':role, 'authenticated':role}
        verify_postgres(runtime_url)
        with connect(runtime_url) as raw:
            for statement in ('CREATE TABLE forbidden(id BIGINT)', 'DELETE FROM scene_migrations',
                              'ALTER TABLE requests ADD COLUMN forbidden TEXT', 'SELECT * FROM users'):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with raw.transaction():
                        raw.execute(statement)
        with connect(url) as raw:
            raw.execute(sql.SQL('GRANT CREATE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
        with pytest.raises(RuntimeError, match='must not own schema objects or create'):
            verify_postgres(runtime_url)
    finally:
        with connect(url) as raw:
            raw.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
            raw.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def test_rls_denies_unscoped_reads_cross_tenant_writes_and_browser_roles(postgres_schema):
    import psycopg
    from psycopg import sql
    from database_security import harden
    url,schema=postgres_schema
    role=schema+'_backend'
    browser=schema+'_browser'
    with connect(url) as raw:
        try:
            migrate(raw)
            raw.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
            raw.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(browser)))
            for name in (role,browser):
                raw.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(name)))
                raw.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(name)))
                raw.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(name)))
            c=Connection(raw)
            uid=c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)',('synthetic@example.invalid','synthetic-hash',1)).lastrowid
            for bid in (1,2):
                raw.execute('INSERT INTO businesses(id,owner_id,name,slug,industry,created_at) VALUES(%s,%s,%s,%s,%s,1)',(bid,uid,'Sample',str(bid),'auto'))
                raw.execute('INSERT INTO stations(id,business_id,label,code,token,created_at) VALUES(%s,%s,%s,%s,%s,1)',(bid,bid,'Desk','desk',str(bid)))
                raw.execute("INSERT INTO requests(business_id,station_id,kind,receipt_hash,client_key,created_at,updated_at) VALUES(%s,%s,'service',%s,%s,1,1)",(bid,bid,'synthetic-receipt-'+str(bid),str(bid)))
                raw.execute("INSERT INTO products(business_id,name) VALUES(%s,'Synthetic item')", (bid,))
                raw.execute('INSERT INTO scans(station_id,business_id,created_at) VALUES(%s,%s,1)', (bid,bid))
                raw.execute("INSERT INTO invites(token_hash,business_id,role,expires_at,used_at) VALUES(%s,%s,'staff',2000000000,NULL)", ('synthetic-invite-'+str(bid),bid))
                raw.execute("INSERT INTO locations VALUES(%s,%s,'Synthetic location','',1,1)",('location-'+str(bid),bid))
                raw.execute("INSERT INTO customers VALUES(%s,%s,'Synthetic','fixture@example.invalid',1,1,1)",('customer-'+str(bid),bid))
                raw.execute('INSERT INTO guest_sessions VALUES(%s,%s,%s,1,2000000000)',('guest-'+str(bid),bid,bid))
                raw.execute('INSERT INTO billing_accounts(business_id,customer_id,updated_at) VALUES(%s,%s,1)',(bid,'cus_'+str(bid)))
                raw.execute("INSERT INTO mail_outbox(id,business_id,invite_hash,recipient,payload,created_at,next_attempt) VALUES(%s,%s,%s,'fixture@example.invalid','{}',1,1)",('mail-'+str(bid),bid,'synthetic-invite-'+str(bid)))
                raw.execute("INSERT INTO growth_settings(business_id,updated_at) VALUES(%s,1)",(bid,))
                raw.execute("INSERT INTO growth_jobs(request_id,business_id,stage,updated_at) SELECT id,business_id,'new',1 FROM requests WHERE business_id=%s",(bid,))
            harden(raw,role)
            harden(raw,role)
            raw.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            assert raw.execute('SELECT id FROM requests').fetchall()==[]
            for table in ('products','stations','scans','invites','audit_events','locations','customers','guest_sessions','billing_accounts','mail_outbox','growth_jobs','growth_settings'):
                assert raw.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table))).fetchall() == []
            c.scope('scene.tenant_id',1)
            assert len(raw.execute('SELECT id FROM requests').fetchall())==1
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with raw.transaction():
                    raw.execute('UPDATE requests SET business_id=2,station_id=2 WHERE business_id=1')
            for table in ('stations','products','scans','invites','locations','customers','guest_sessions','billing_accounts','mail_outbox','growth_jobs','growth_settings'):
                rows = raw.execute(sql.SQL('SELECT business_id FROM {}').format(sql.Identifier(table))).fetchall()
                assert [r['business_id'] for r in rows] == [1]
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with raw.transaction():
                        raw.execute(sql.SQL('UPDATE {} SET business_id=2 WHERE business_id=1').format(sql.Identifier(table)))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with raw.transaction():
                    raw.execute("INSERT INTO audit_events VALUES('synthetic-event',2,NULL,'request.created',1,1)")
            raw.execute("INSERT INTO audit_events VALUES('synthetic-event',1,NULL,'request.created',1,1)")
            for statement in ('UPDATE audit_events SET resource_id=2', 'DELETE FROM audit_events', 'TRUNCATE audit_events'):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with raw.transaction():
                        raw.execute(statement)
            c.scope('scene.tenant_id','')
            c.scope('scene.receipt_hash','synthetic-receipt-2')
            assert len(raw.execute('SELECT id FROM requests').fetchall())==1
            raw.execute('RESET ROLE')
            raw.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(browser)))
            for table in ('users','sessions','requests','invites','auth_identities','audit_events','customers','guest_sessions','billing_accounts','billing_events','mail_outbox','growth_jobs','growth_settings'):
                assert raw.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table))).fetchall()==[]
        finally:
            raw.rollback()  # roles, schema contents and synthetic data never persist


def test_version_one_upgrade_preserves_historical_requests(postgres_schema):
    from pathlib import Path
    from request_schema import FIELDS
    url,_=postgres_schema
    with connect(url) as raw:
        raw.execute((Path(__file__).resolve().parents[1]/'migrations/001_postgres.sql').read_text())
        raw.execute('CREATE TABLE scene_migrations(version BIGINT PRIMARY KEY)')
        raw.execute('INSERT INTO scene_migrations VALUES(1)')
        c=Connection(raw)
        uid=c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)',('upgrade@example.invalid','synthetic-hash',1)).lastrowid
        bid=c.execute('INSERT INTO businesses(owner_id,name,slug,industry,created_at) VALUES(?,?,?,?,?)',(uid,'Synthetic','upgrade','auto',1)).lastrowid
        sid=c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)',(bid,'Desk','desk','synthetic-upgrade-qr',1)).lastrowid
        rid=c.execute('INSERT INTO requests(business_id,station_id,kind,message,receipt_hash,client_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(bid,sid,'question','Historical synthetic inquiry','synthetic-receipt','synthetic-key',1,1)).lastrowid
        migrate(raw)
        migrate(raw)
        row=raw.execute('SELECT * FROM requests WHERE id=%s',(rid,)).fetchone()
        assert row['message']=='Historical synthetic inquiry'
        assert all(row[name] is None for name in FIELDS)
        assert raw.execute('SELECT version FROM scene_migrations').fetchone()['version']==4


def test_hardening_rejects_inherited_table_ownership(postgres_schema):
    from psycopg import sql
    from database_security import harden
    from storage import verify_runtime_role
    url,schema=postgres_schema
    with connect(url) as raw:
        try:
            migrate(raw)
            parent,backend=schema+'_owner',schema+'_backend'
            for role in (parent,backend):
                raw.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
                raw.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
            raw.execute(sql.SQL('ALTER TABLE users OWNER TO {}').format(sql.Identifier(parent)))
            raw.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(parent),sql.Identifier(backend)))
            with pytest.raises(RuntimeError,match='through membership'):
                verify_runtime_role(raw,backend)
            with pytest.raises(RuntimeError,match='through membership'):
                harden(raw,backend)
            assert not raw.execute("SELECT relrowsecurity AS enabled FROM pg_class WHERE oid='requests'::regclass").fetchone()['enabled']
        finally:
            raw.rollback()


def test_legacy_version_two_import_and_scope_lifetime(postgres_schema, sqlite_snapshot):
    import sqlite3
    from migrate import import_sqlite
    from storage import postgres_db
    url, _ = postgres_schema
    # Emulate a retained pre-security beta snapshot without modifying real data.
    with sqlite3.connect(sqlite_snapshot) as old:
        for trigger in ('station_location_insert','station_location_update','request_customer_insert','request_customer_update'):
            old.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        for table in ('mail_outbox','guest_sessions','customers','locations','rate_buckets','auth_flows','auth_blocks','billing_accounts','billing_events'):
            old.execute(f'DROP TABLE {table}')
        old.execute('DROP TABLE auth_identities')
        old.execute('DROP TABLE audit_events')
        old.execute('ALTER TABLE sessions DROP COLUMN managed_token')
    with connect(url) as raw:
        migrate(raw)
        import_sqlite(raw, sqlite_snapshot)
        assert raw.execute('SELECT count(*) AS n FROM requests').fetchone()['n'] == 1
        assert raw.execute('SELECT managed_token FROM sessions').fetchone()['managed_token'] is None
    with postgres_db(url) as c:
        c.scope('scene.tenant_id', 123)
        c.scope('scene.receipt_hash', 'synthetic-receipt')
    with postgres_db(url) as c:
        row = c.raw.execute("SELECT current_setting('scene.tenant_id', true) AS tenant, current_setting('scene.receipt_hash',true) AS receipt").fetchone()
        assert not row['tenant'] and not row['receipt']


def test_import_restores_new_location_customer_and_outbox_dependencies(postgres_schema, sqlite_snapshot):
    import sqlite3
    from migrate import import_sqlite, BACKEND_TABLES
    url,_=postgres_schema
    with sqlite3.connect(sqlite_snapshot) as old:
        old.execute("INSERT INTO locations VALUES('synthetic-location',1,'Fixture','',1,1)")
        old.execute("UPDATE stations SET location_id='synthetic-location' WHERE id=1")
        old.execute("INSERT INTO customers VALUES('synthetic-customer',1,'Synthetic','fixture@example.invalid',1,1,1)")
        old.execute("UPDATE requests SET customer_id='synthetic-customer' WHERE id=1")
        old.execute("INSERT INTO mail_outbox(id,business_id,invite_hash,recipient,payload,created_at,next_attempt) VALUES('synthetic-mail',1,'synthetic-invite','fixture@example.invalid','{}',1,1)")
    with connect(url) as raw:
        migrate(raw)
        import_sqlite(raw,sqlite_snapshot)
        for table in BACKEND_TABLES:
            with sqlite3.connect(sqlite_snapshot) as old:
                assert raw.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n']==old.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        assert raw.execute('SELECT customer_id FROM requests WHERE id=1').fetchone()['customer_id']=='synthetic-customer'
        assert raw.execute('SELECT location_id FROM stations WHERE id=1').fetchone()['location_id']=='synthetic-location'
