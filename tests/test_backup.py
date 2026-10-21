import hashlib
import sqlite3
import pytest
from backup import backup_sqlite


def test_backup_restore_preserves_committed_wal_and_source(sqlite_snapshot, tmp_path):
    before = hashlib.sha256(sqlite_snapshot.read_bytes()).hexdigest()
    backup = tmp_path / 'backup.sqlite'
    backup_sqlite(sqlite_snapshot, backup)
    assert hashlib.sha256(sqlite_snapshot.read_bytes()).hexdigest() == before
    assert backup.stat().st_mode & 0o777 == 0o600
    # A backup is independent of later source writes and can be restored.
    with sqlite3.connect(sqlite_snapshot) as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute("UPDATE requests SET status='completed'")
        c.commit()
        live_backup = tmp_path / 'wal-backup.sqlite'
        backup_sqlite(sqlite_snapshot, live_backup)
        with sqlite3.connect(live_backup) as restored:
            assert restored.execute('SELECT status FROM requests').fetchone()[0] == 'completed'
    restored_path = tmp_path / 'restored.sqlite'
    backup_sqlite(backup, restored_path)
    with sqlite3.connect(restored_path) as c:
        assert c.execute('SELECT status FROM requests').fetchone()[0] == 'open'
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert c.execute('PRAGMA foreign_key_check').fetchall() == []


def test_backup_refuses_overwrite_or_missing_source(sqlite_snapshot, tmp_path):
    backup = tmp_path / 'backup.sqlite'
    backup.write_bytes(b'existing private backup')
    with pytest.raises(FileExistsError):
        backup_sqlite(sqlite_snapshot, backup)
    assert backup.read_bytes() == b'existing private backup'
    missing_target = tmp_path / 'failed.sqlite'
    with pytest.raises(sqlite3.OperationalError):
        backup_sqlite(tmp_path / 'absent.sqlite', missing_target)
    assert not missing_target.exists()
