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
