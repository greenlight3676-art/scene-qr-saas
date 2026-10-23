"""Additive security schema shared by SQLite and PostgreSQL migrations."""

def upgrade(c):
    c.execute('''CREATE TABLE IF NOT EXISTS auth_identities(
        subject TEXT PRIMARY KEY, user_id BIGINT UNIQUE NOT NULL REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_events(
        event_id TEXT PRIMARY KEY, business_id BIGINT NOT NULL REFERENCES businesses(id),
        actor_id BIGINT REFERENCES users(id), action TEXT NOT NULL,
        resource_id BIGINT NOT NULL, created_at BIGINT NOT NULL)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_events(business_id,created_at)')


def upgrade_sqlite(c):
    upgrade(c)
    columns = {row[1] for row in c.execute('PRAGMA table_info(sessions)')}
    if 'managed_token' not in columns:
        c.execute('ALTER TABLE sessions ADD COLUMN managed_token TEXT')
