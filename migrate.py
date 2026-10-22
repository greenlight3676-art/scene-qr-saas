"""Explicit migration/import CLI. URLs are read from secure environment only."""
import argparse
import os
from pathlib import Path
import sqlite3
from storage import connect, IDENTITY_TABLES
from request_schema import FIELDS

ROOT = Path(__file__).resolve().parent
TABLES = ('users', 'businesses', 'memberships', 'stations', 'products', 'requests', 'sessions', 'invites', 'scans')


def migrate(raw):
    raw.execute('SELECT pg_advisory_xact_lock(73623601)')
    raw.execute('CREATE TABLE IF NOT EXISTS scene_migrations(version BIGINT PRIMARY KEY)')
    versions = raw.execute('SELECT version FROM scene_migrations').fetchall()
    if versions and versions not in ([{'version': 1}], [{'version': 2}]):
        raise RuntimeError('Unknown database migration version')
    if versions == [{'version': 2}]:
        return
    if versions == [{'version': 1}]:
        for name, declaration in FIELDS.items():
            raw.execute(f'ALTER TABLE requests ADD COLUMN {name} {declaration}')
        raw.execute('UPDATE scene_migrations SET version=2')
        return
    if any(raw.execute('SELECT to_regclass(%s) AS name', (table,)).fetchone()['name'] for table in TABLES):
        raise RuntimeError('First migration requires an empty application schema')
    raw.execute((ROOT / 'migrations/001_postgres.sql').read_text())
    raw.execute('INSERT INTO scene_migrations VALUES (1)')
    migrate(raw)


def import_sqlite(raw, source):
    from psycopg import sql
    # Caller must stop writes and provide a consistent backup. Never modify source.
    with sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True) as old:
        old.execute('BEGIN')  # One consistent source snapshot across all tables.
        if old.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('SQLite integrity check failed')
        if old.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('SQLite foreign key check failed')
        raw.execute('SELECT pg_advisory_xact_lock(73623601)')
        for table in TABLES:
            if raw.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone():
                raise RuntimeError('Import requires an empty PostgreSQL target')
        for table in TABLES:
            cursor = old.execute(f'SELECT * FROM {table}')
            columns = [item[0] for item in cursor.description]
            insert = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                sql.Identifier(table),
                sql.SQL(',').join(map(sql.Identifier, columns)),
                sql.SQL(',').join(sql.Placeholder() for _ in columns))
            for row in cursor:
                raw.execute(insert, row)
            count = raw.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n']
            if count != old.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:
                raise RuntimeError('Import count mismatch')
        for table in sorted(IDENTITY_TABLES):
            raw.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM {table}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['up', 'import'])
    parser.add_argument('--sqlite', help='Consistent SQLite backup, opened read-only')
    args = parser.parse_args()
    if args.operation == 'import' and not args.sqlite:
        parser.error('import requires --sqlite')
    # Failures roll back the entire operation. Do not print connection strings/data.
    try:
        with connect(os.environ['SCENE_MIGRATION_DATABASE_URL']) as raw:
            migrate(raw)
            if args.operation == 'import':
                import_sqlite(raw, args.sqlite)
    except Exception:
        raise SystemExit('Migration failed; transaction rolled back. Check configuration and schema privately.') from None
    print('Migration completed.')
