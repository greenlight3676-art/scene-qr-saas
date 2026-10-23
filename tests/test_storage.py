"""Adapter regressions that also run without third-party dependencies."""
import unittest
from storage import Connection, Row, connect


class Cursor:
    rowcount = 1

    def fetchone(self):
        return {'id': 7}

    def fetchall(self):
        return [{'id': 7}]


class Raw:
    def execute(self, sql, parameters):
        self.sql, self.parameters = sql, parameters
        return Cursor()


class StorageTests(unittest.TestCase):
    def test_identity_and_parameters(self):
        raw = Raw()
        result = Connection(raw).execute('INSERT INTO products(business_id,name) VALUES(?,?)', (2, "guest's ? input"))
        self.assertEqual(result.lastrowid, 7)
        self.assertTrue(raw.sql.endswith('VALUES(%s,%s) RETURNING id'))
        self.assertEqual(raw.parameters, (2, "guest's ? input"))

    def test_scoped_update_rowcount_and_rows(self):
        raw = Raw()
        result = Connection(raw).execute('UPDATE requests SET status=? WHERE id=? AND business_id=?', ('completed', 7, 2))
        self.assertEqual(result.rowcount, 1)
        self.assertIsNone(result.lastrowid)
        self.assertEqual(result.fetchone()[0], 7)
        self.assertEqual(list(result), [{'id': 7}])
        self.assertEqual(Row({'count': 0})[0], 0)

    def test_no_fallback_for_invalid_database_url(self):
        with self.assertRaises(RuntimeError):
            connect('sqlite:///should-not-fall-back')


class SchemaUpgradeTests(unittest.TestCase):
    def test_existing_request_data_is_preserved_and_unknown_fields_stay_null(self):
        import sqlite3
        from request_schema import upgrade_sqlite
        with sqlite3.connect(':memory:') as c:
            c.execute('CREATE TABLE requests(id INTEGER PRIMARY KEY,message TEXT)')
            c.execute("INSERT INTO requests VALUES(1,'Historical synthetic request')")
            upgrade_sqlite(c)
            upgrade_sqlite(c)
            row=c.execute('SELECT message,quantity,customer_contact,reply_consent_at FROM requests').fetchone()
            self.assertEqual(row,('Historical synthetic request',None,None,None))


def test_remote_runtime_requires_verified_tls_before_connecting():
    from storage import verify_postgres
    import pytest
    for url in ('postgresql://runtime@db.example.invalid/scene',
                'postgresql://runtime@db.example.invalid/scene?sslmode=require',
                'postgresql://runtime@localhost/scene?host=db.example.invalid',
                'postgresql://runtime@localhost/scene?hostaddr=192.0.2.1'):
        with pytest.raises(RuntimeError, match='verify-full'):
            verify_postgres(url)


def test_sqlite_security_upgrade_preserves_legacy_sessions():
    import sqlite3
    from security_schema import upgrade_sqlite
    with sqlite3.connect(':memory:') as c:
        c.executescript("CREATE TABLE users(id INTEGER PRIMARY KEY); CREATE TABLE businesses(id INTEGER PRIMARY KEY); CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER,csrf TEXT,expires_at INTEGER);")
        c.execute("INSERT INTO sessions VALUES('synthetic-session',1,'synthetic-csrf',2000000000)")
        upgrade_sqlite(c)
        upgrade_sqlite(c)
        assert c.execute('SELECT * FROM sessions').fetchone() == ('synthetic-session',1,'synthetic-csrf',2000000000,None)
