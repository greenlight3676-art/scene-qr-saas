"""Opt-in PostgreSQL adapter; SQLite remains the default backend.

SQL uses the application's fixed queries only, never client-supplied identifiers.
The transaction advisory lock preserves beta read/check/write semantics across
connections until finer-grained concurrency is implemented in Task 3.
"""
from contextlib import contextmanager
import re
from backend_schema import TABLES as BACKEND_TABLES, VERSION

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

    def scope(self, name, value):
        if name not in ("scene.tenant_id", "scene.receipt_hash", "scene.qr_token", "scene.invite_hash", "scene.auth_subject", "scene.billing_customer", "scene.mail_worker"):
            raise ValueError("Unsupported transaction scope")
        self.raw.execute("SELECT set_config(%s, %s, true)", (name, str(value)))

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


def verify_runtime_role(raw, role):
    """Reject direct privileges and roles reachable through SET ROLE."""
    privileges = raw.execute('''SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls
        FROM pg_roles WHERE pg_has_role(%s,oid,'MEMBER')''', (role,)).fetchall()
    if not privileges or any(any(row.values()) for row in privileges):
        raise RuntimeError('Use a restricted PostgreSQL runtime role')
    permissions = raw.execute('''SELECT
        has_schema_privilege(%s,current_schema(),'CREATE') AS schema_create,
        EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=current_schema()
                AND pg_has_role(%s,c.relowner,'MEMBER')) AS owns_objects
        ''', (role, role)).fetchone()
    if any(permissions.values()):
        raise RuntimeError('Runtime role must not own schema objects or create in the application schema, directly or through membership')


def verify_postgres(url):
    from urllib.parse import urlsplit, parse_qs
    parsed = urlsplit(url)
    options = parse_qs(parsed.query)
    hosts = options.get('host', [parsed.hostname]) + options.get('hostaddr', [])
    local = all(host is None or host in ('localhost', '127.0.0.1', '::1')
                or host.startswith('/') for host in hosts)
    if not local and options.get('sslmode') != ['verify-full']:
        raise RuntimeError('Remote runtime database connections require sslmode=verify-full')
    with connect(url) as raw:
        identity = raw.execute('SELECT current_user AS name, session_user AS login').fetchone()
        verify_runtime_role(raw, identity['login'])
        verify_runtime_role(raw, identity['name'])
        expected = ('users','businesses','memberships','stations','products','requests','sessions','invites','scans','auth_identities','audit_events','scene_migrations',*BACKEND_TABLES)
        protected = raw.execute('''SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=current_schema() AND c.relrowsecurity AND c.relname=ANY(%s)''', (list(expected),)).fetchall()
        if {r['relname'] for r in protected} != set(expected):
            raise RuntimeError('Run database_security.py with the dedicated runtime role before starting SCENE')
        version = raw.execute('SELECT version FROM scene_migrations').fetchall()
        if version != [{'version': VERSION}]:
            raise RuntimeError('Apply PostgreSQL current schema version before starting SCENE')
