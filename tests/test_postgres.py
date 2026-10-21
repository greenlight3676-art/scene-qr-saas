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
    from migrate import import_sqlite, TABLES
    url, _ = postgres_schema
    original = hashlib.sha256(sqlite_snapshot.read_bytes()).hexdigest()
    with connect(url) as raw:
        migrate(raw)
        import_sqlite(raw, sqlite_snapshot)
        with sqlite3.connect(sqlite_snapshot) as old:
            for table in TABLES:
                cursor = old.execute(f'SELECT * FROM {table}')
                names = [col[0] for col in cursor.description]
                expected = [dict(zip(names, row)) for row in cursor]
                assert raw.execute(f'SELECT * FROM {table}').fetchall() == expected
        c = Connection(raw)
        assert c.execute('INSERT INTO products(business_id,name) VALUES(?,?)', (1, 'Next sample')).lastrowid == 3
        with pytest.raises(RuntimeError, match='empty PostgreSQL target'):
            import_sqlite(raw, sqlite_snapshot)
    assert hashlib.sha256(sqlite_snapshot.read_bytes()).hexdigest() == original


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
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    from storage import verify_postgres
    url, schema = postgres_schema
    role = schema + '_runtime'
    with connect(url) as raw:
        migrate(raw)
        raw.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
        raw.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
        raw.execute(sql.SQL('GRANT SELECT ON scene_migrations TO {}').format(sql.Identifier(role)))
    parsed = urlsplit(url)
    options = dict(parse_qsl(parsed.query))
    options['options'] += f' -crole={role}'
    runtime_url = urlunsplit(parsed._replace(query=urlencode(options)))
    try:
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
