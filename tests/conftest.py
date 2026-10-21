"""Disposable database fixtures: never use a business database URL for tests."""
import ast
from pathlib import Path
import sqlite3
import uuid

import pytest


@pytest.fixture
def sqlite_snapshot(tmp_path):
    source = tmp_path / 'source.sqlite'
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'server.py').read_text())
    schema = next(node.args[0].value for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == 'executescript')
    with sqlite3.connect(source) as c:
        c.executescript(schema)
        c.execute("INSERT INTO users VALUES(1,'fixture@example.invalid','synthetic-hash',1)")
        for bid in (1, 2):
            c.execute('INSERT INTO businesses(id,owner_id,name,slug,industry,created_at) VALUES(?,1,?,?,?,1)',
                      (bid, f'Sample {bid}', f'sample-{bid}', 'auto'))
            c.execute("INSERT INTO memberships VALUES(?,1,'owner')", (bid,))
            c.execute('INSERT INTO stations(id,business_id,label,code,token,created_at) VALUES(?,?,?,?,?,1)',
                      (bid, bid, 'Desk', 'desk', f'synthetic-token-{bid}'))
            c.execute('INSERT INTO products(id,business_id,name) VALUES(?,?,?)', (bid, bid, 'Sample service'))
        c.execute("INSERT INTO requests VALUES(1,1,1,'service','Sample request',1,'open','synthetic-receipt-hash','synthetic-client-key',1,1)")
        c.execute("INSERT INTO sessions VALUES('synthetic-session',1,'synthetic-csrf',2000000000)")
        c.execute("INSERT INTO invites VALUES('synthetic-invite',1,'staff',2000000000,NULL)")
        c.execute('INSERT INTO scans VALUES(1,1,1,1)')
    return source


@pytest.fixture
def postgres_schema():
    import os
    from storage import connect
    url = os.getenv('SCENE_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('Disposable PostgreSQL URL not configured')
    from psycopg import sql
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    name = 'scene_test_' + uuid.uuid4().hex
    with connect(url) as raw:
        raw.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
    # Connection options keep every transaction in this test's isolated schema.
    parsed = urlsplit(url)
    options = dict(parse_qsl(parsed.query))
    options['options'] = f'-csearch_path={name}'
    scoped_url = urlunsplit(parsed._replace(query=urlencode(options)))
    try:
        yield scoped_url, name
    finally:
        with connect(url) as raw:
            raw.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(name)))


@pytest.fixture(scope='session', autouse=True)
def api_postgres_backend():
    """Run the unchanged SQLite API regressions on imported PG data when requested.

    Only test code switches the imported module after its local SQLite demo seed.
    PostgreSQL demo startup remains forbidden in the actual application.
    """
    import os
    if os.getenv('SCENE_TEST_API_BACKEND') != 'postgres':
        yield
        return
    url = os.getenv('SCENE_TEST_POSTGRES_URL')
    if not url:
        pytest.fail('PostgreSQL API tests require SCENE_TEST_POSTGRES_URL')
    import server
    from migrate import migrate, import_sqlite
    from storage import connect, verify_postgres
    from psycopg import sql
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    name = 'scene_api_' + uuid.uuid4().hex
    role = name + '_runtime'
    parsed = urlsplit(url)
    options = dict(parse_qsl(parsed.query))
    options['options'] = f'-csearch_path={name}'
    owner_url = urlunsplit(parsed._replace(query=urlencode(options)))
    with connect(url) as raw:
        raw.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
        raw.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    try:
        with connect(owner_url) as raw:
            migrate(raw)
            import_sqlite(raw, server.DB_PATH)
            raw.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(name), sql.Identifier(role)))
            raw.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(name), sql.Identifier(role)))
            raw.execute(sql.SQL('REVOKE INSERT,UPDATE,DELETE ON scene_migrations FROM {}').format(sql.Identifier(role)))
            raw.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}').format(sql.Identifier(name), sql.Identifier(role)))
        # connect() uses the owner DSN but drops privileges at session startup.
        # The connection URL carries only the isolated test role, never user data.
        options['options'] = f'-csearch_path={name} -crole={role}'
        runtime_url = urlunsplit(parsed._replace(query=urlencode(options)))
        verify_postgres(runtime_url)
        previous = server.DATABASE_URL
        server.DATABASE_URL = runtime_url
        try:
            yield
        finally:
            server.DATABASE_URL = previous
    finally:
        with connect(url) as raw:
            raw.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(name)))
            raw.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
