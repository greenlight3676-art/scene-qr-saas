"""Create a private SQLite backup without overwriting an existing path."""
import argparse
import os
from pathlib import Path
import sqlite3


def backup_sqlite(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    # Reserve the destination exclusively with owner-only permissions.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as old:
            with sqlite3.connect(destination) as new:
                old.backup(new)
                if new.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Backup integrity check failed')
                if new.execute('PRAGMA foreign_key_check').fetchall():
                    raise RuntimeError('Backup foreign key check failed')
    except Exception:
        destination.unlink()  # Only the new file reserved above, never an existing backup.
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    backup_sqlite(args.source, args.destination)
    print('SQLite backup created and checked.')
