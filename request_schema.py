"""Additive request fields; NULL means unknown for historical records."""
FIELDS = {
    'quantity': 'INTEGER CHECK(quantity BETWEEN 1 AND 99)',
    'product_name': 'TEXT',
    'unit_price_cents': 'INTEGER CHECK(unit_price_cents >= 0)',
    'customer_name': 'TEXT',
    'customer_contact': 'TEXT',
    'reply_consent_at': 'BIGINT',
    'lead_status': "TEXT CHECK(lead_status IN ('new','qualified','closed'))",
}
PRIVATE_FIELDS = ',r.quantity,r.product_name,r.unit_price_cents,r.customer_name,r.customer_contact,r.reply_consent_at,r.lead_status'


def upgrade_sqlite(c):
    present = {r[1] for r in c.execute('PRAGMA table_info(requests)')}
    for name, declaration in FIELDS.items():
        if name not in present:
            c.execute(f'ALTER TABLE requests ADD COLUMN {name} {declaration}')
