"""Opt-in PostgreSQL adapter; SQLite remains the default backend.

SQL uses the application's fixed queries only, never client-supplied identifiers.
The transaction advisory lock preserves beta read/check/write semantics across
connections until finer-grained concurrency is implemented in Task 3.
"""
from contextlib import contextmanager
import re

IDENTITY_TABLES = {'users', 'businesses', 'stations', 'products', 'requests', 'scans'}


def connect(url):
    if not (url.startswith(('postgresql://', 'postgres://'))):
        raise RuntimeError('SCENE_DATABASE_URL must be a PostgreSQL URL')
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=10)


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Result:
    def __init__(self, cursor, identity=False):
        self.cursor = cursor
        self.rowcount = cursor.rowcount
        self.lastrowid = cursor.fetchone()['id'] if identity else None

    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return [Row(row) for row in self.cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class Connection:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, parameters=()):
        match = re.match(r'\s*INSERT INTO (\w+)', sql, re.I)
        identity = bool(match and match[1].lower() in IDENTITY_TABLES)
        # Existing SQL contains no question marks in literals or user identifiers.
        sql = sql.replace('?', '%s')
        if identity:
            sql += ' RETURNING id'
        return Result(self.raw.execute(sql, parameters), identity)


@contextmanager
def postgres_db(url):
    with connect(url) as raw:
        raw.execute('SET LOCAL lock_timeout = \'15s\'')
        raw.execute('SET LOCAL statement_timeout = \'30s\'')
        raw.execute('SELECT pg_advisory_xact_lock(73623601)')
        yield Connection(raw)


def verify_postgres(url):
    with connect(url) as raw:
        role = raw.execute('SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        if any(role.values()):
            raise RuntimeError('Use a restricted PostgreSQL runtime role')
        permissions = raw.execute('''SELECT
            has_schema_privilege(current_schema(), 'CREATE') AS schema_create,
            EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=current_schema()
                    AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)) AS owns_objects
        ''').fetchone()
        if any(permissions.values()):
            raise RuntimeError('Runtime role must not own schema objects or create in the application schema')
        version = raw.execute('SELECT version FROM scene_migrations').fetchall()
        if version != [{'version': 1}]:
            raise RuntimeError('Apply PostgreSQL migration 001 before starting SCENE')
