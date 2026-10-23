"""Version 4 additive backend schema. New IDs are opaque strings on both backends."""
VERSION = 4
TABLES = ('locations', 'customers', 'guest_sessions', 'rate_buckets', 'auth_flows',
          'auth_blocks', 'billing_accounts', 'billing_events', 'mail_outbox')
TENANT_TABLES = ('locations', 'customers', 'guest_sessions', 'billing_accounts', 'mail_outbox')

DEFINITIONS = (
    '''CREATE TABLE mail_outbox(id TEXT PRIMARY KEY,business_id BIGINT NOT NULL REFERENCES businesses(id),
       invite_hash TEXT NOT NULL,recipient TEXT NOT NULL,payload TEXT NOT NULL,
       state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','review')),
       attempts BIGINT NOT NULL DEFAULT 0,created_at BIGINT NOT NULL,next_attempt BIGINT NOT NULL,provider_id TEXT,
       FOREIGN KEY(business_id,invite_hash) REFERENCES invites(business_id,token_hash))''',
    '''CREATE TABLE locations(id TEXT PRIMARY KEY, business_id BIGINT NOT NULL REFERENCES businesses(id),
       name TEXT NOT NULL, address TEXT NOT NULL DEFAULT '', active BIGINT NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
       created_at BIGINT NOT NULL, UNIQUE(business_id,id))''',
    '''CREATE TABLE customers(id TEXT PRIMARY KEY, business_id BIGINT NOT NULL REFERENCES businesses(id),
       name TEXT NOT NULL, contact TEXT NOT NULL, consent_at BIGINT NOT NULL,
       created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL, UNIQUE(business_id,id))''',
    '''CREATE TABLE guest_sessions(token_hash TEXT PRIMARY KEY, business_id BIGINT NOT NULL REFERENCES businesses(id),
       station_id BIGINT NOT NULL REFERENCES stations(id), created_at BIGINT NOT NULL, expires_at BIGINT NOT NULL,
       FOREIGN KEY(business_id,station_id) REFERENCES stations(business_id,id))''',
    '''CREATE TABLE rate_buckets(bucket TEXT PRIMARY KEY, hits BIGINT NOT NULL CHECK(hits>0), expires_at BIGINT NOT NULL)''',
    '''CREATE TABLE auth_flows(flow_hash TEXT PRIMARY KEY, email TEXT NOT NULL, purpose TEXT NOT NULL CHECK(purpose IN ('signup','recovery')),
       name TEXT NOT NULL DEFAULT '', industry TEXT NOT NULL DEFAULT '', expires_at BIGINT NOT NULL)''',
    '''CREATE TABLE auth_blocks(subject TEXT PRIMARY KEY, revoked_before BIGINT NOT NULL)''',
    '''CREATE TABLE billing_accounts(business_id BIGINT PRIMARY KEY REFERENCES businesses(id), customer_id TEXT UNIQUE,
       subscription_id TEXT UNIQUE, status TEXT NOT NULL DEFAULT 'unconfigured', price_id TEXT,
       valid_until BIGINT NOT NULL DEFAULT 0, event_created BIGINT NOT NULL DEFAULT 0, updated_at BIGINT NOT NULL)''',
    '''CREATE TABLE billing_events(event_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, event_type TEXT NOT NULL,
       created_at BIGINT NOT NULL, processed_at BIGINT NOT NULL)''',
)
COLUMNS = {
    'stations': {'location_id': 'TEXT', 'destination': "TEXT NOT NULL DEFAULT 'menu' CHECK(destination IN ('menu','service','info'))",
                 'content_title': "TEXT NOT NULL DEFAULT ''", 'content_message': "TEXT NOT NULL DEFAULT ''"},
    'invites': {'email': 'TEXT'},
    'requests': {'customer_id': 'TEXT'},
    'sessions': {'purpose': "TEXT NOT NULL DEFAULT 'login' CHECK(purpose IN ('login','recovery'))"},
}
INDEXES = (
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_station_tenant ON stations(business_id,id)',
    'CREATE INDEX IF NOT EXISTS idx_locations_tenant ON locations(business_id,active)',
    'CREATE INDEX IF NOT EXISTS idx_customers_tenant ON customers(business_id,created_at,id)',
    'CREATE INDEX IF NOT EXISTS idx_guest_expiry ON guest_sessions(expires_at)',
    'CREATE INDEX IF NOT EXISTS idx_rate_expiry ON rate_buckets(expires_at)',
    "CREATE INDEX IF NOT EXISTS idx_mail_queue ON mail_outbox(state,next_attempt)",
    'CREATE INDEX IF NOT EXISTS idx_flow_expiry ON auth_flows(expires_at)',
    'CREATE INDEX IF NOT EXISTS idx_station_location ON stations(business_id,location_id)',
    'CREATE INDEX IF NOT EXISTS idx_membership_user ON memberships(user_id,business_id)',
    'CREATE INDEX IF NOT EXISTS idx_request_history ON requests(business_id,id)',
)


def upgrade(c, sqlite=False):
    # Must precede guest_sessions composite foreign key on legacy SQLite databases.
    c.execute(INDEXES[0])
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_invite_tenant ON invites(business_id,token_hash)')
    for definition in DEFINITIONS:
        c.execute(definition.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1) if sqlite else definition)
    for table, columns in COLUMNS.items():
        present = {row[1] for row in c.execute(f'PRAGMA table_info({table})')} if sqlite else set()
        for name, declaration in columns.items():
            if name not in present:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {declaration}')
    for statement in INDEXES[1:]:
        c.execute(statement)
    if sqlite:
        for operation in ('INSERT', 'UPDATE'):
            c.execute(f'''CREATE TRIGGER IF NOT EXISTS station_location_{operation.lower()}
                BEFORE {operation} ON stations WHEN NEW.location_id IS NOT NULL AND NOT EXISTS
                (SELECT 1 FROM locations WHERE id=NEW.location_id AND business_id=NEW.business_id)
                BEGIN SELECT RAISE(ABORT,'Location must belong to station tenant'); END''')
        for operation in ('INSERT', 'UPDATE'):
            c.execute(f'''CREATE TRIGGER IF NOT EXISTS request_customer_{operation.lower()} BEFORE {operation} ON requests
                WHEN NEW.customer_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM customers WHERE id=NEW.customer_id AND business_id=NEW.business_id)
                BEGIN SELECT RAISE(ABORT,'Customer must belong to request tenant'); END''')
        c.execute('''CREATE TRIGGER IF NOT EXISTS prevent_customer_tenant_change BEFORE UPDATE OF business_id ON customers
            WHEN EXISTS(SELECT 1 FROM requests WHERE customer_id=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Referenced customer tenant is immutable'); END''')
        c.execute('''CREATE TRIGGER IF NOT EXISTS prevent_location_tenant_change BEFORE UPDATE OF business_id ON locations
            WHEN EXISTS(SELECT 1 FROM stations WHERE location_id=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Referenced location tenant is immutable'); END''')
    else:
        c.execute('ALTER TABLE requests ADD CONSTRAINT request_customer_tenant FOREIGN KEY(business_id,customer_id) REFERENCES customers(business_id,id)')
        c.execute('ALTER TABLE stations ADD CONSTRAINT station_location_tenant FOREIGN KEY(business_id,location_id) REFERENCES locations(business_id,id)')
