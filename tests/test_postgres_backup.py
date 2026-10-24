"""Real pg_dump/pg_restore drill on a separate disposable local CI database."""
import os
import json
import shutil
import subprocess
import uuid
from urllib.parse import urlsplit,urlunsplit
import pytest
from storage import connect
from migrate import migrate,import_sqlite,TABLES,SECURITY_TABLES,BACKEND_TABLES

pytestmark=pytest.mark.skipif(not os.getenv('SCENE_TEST_POSTGRES_URL'),reason='Disposable PostgreSQL URL not configured')


def client_env(url,database=None):
    from psycopg.conninfo import conninfo_to_dict
    values=conninfo_to_dict(url)
    result={k:v for k,v in os.environ.items() if not k.startswith('PG')}
    for key,target in (('host','PGHOST'),('port','PGPORT'),('user','PGUSER'),('password','PGPASSWORD'),('dbname','PGDATABASE')):
        if key in values:result[target]=values[key]
    if database:result['PGDATABASE']=database
    return result


def test_disposable_dump_restore_preserves_application_rows(postgres_schema,sqlite_snapshot,tmp_path):
    container=os.getenv('SCENE_TEST_PG_CONTAINER')
    if not container and (not shutil.which('pg_dump') or not shutil.which('pg_restore')):
        pytest.skip('PostgreSQL dump/restore tools not installed')
    from psycopg import sql
    url,schema=postgres_schema
    base=os.environ['SCENE_TEST_POSTGRES_URL']
    restored='scene_test_restore_'+uuid.uuid4().hex
    backup=tmp_path/'synthetic-backup.dump'
    with connect(url) as raw:
        migrate(raw);import_sqlite(raw,sqlite_snapshot)
        tables=(*TABLES,*SECURITY_TABLES,*BACKEND_TABLES,'scene_migrations')
        # Counts alone miss changed statuses, contacts, receipts and QR tokens.
        expected={t:sorted(json.dumps(dict(row),sort_keys=True) for row in
                           raw.execute(f'SELECT * FROM {t}').fetchall()) for t in tables}
    # No password/URL is put in a command argument or printed in captured output.
    if container:
        result=subprocess.run(['docker','exec',container,'pg_dump','-U','scene_test','-d','scene_test',
                               '--format=custom','--no-owner','--no-privileges','--schema='+schema],
                              check=True,capture_output=True,timeout=60)
        with os.fdopen(os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as stream:
            stream.write(result.stdout)
    else:
        with os.fdopen(os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb'):
            pass
        subprocess.run(['pg_dump','--format=custom','--no-owner','--no-privileges','--schema='+schema,'--file='+str(backup)],
                       env=client_env(base),check=True,capture_output=True,timeout=60)
    with connect(base) as raw:
        raw.autocommit=True
        raw.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restored)))
    try:
        if container:
            subprocess.run(['docker','exec','-i',container,'pg_restore','-U','scene_test','--dbname='+restored,
                            '--exit-on-error','--no-owner','--no-privileges'],input=backup.read_bytes(),
                           check=True,capture_output=True,timeout=60)
        else:
            subprocess.run(['pg_restore','--dbname='+restored,'--exit-on-error','--no-owner','--no-privileges',str(backup)],
                           env=client_env(base,restored),check=True,capture_output=True,timeout=60)
        parsed=urlsplit(url)
        restore_url=urlunsplit(parsed._replace(path='/'+restored))
        with connect(restore_url) as raw:
            for table,rows in expected.items():
                actual=sorted(json.dumps(dict(row),sort_keys=True) for row in
                              raw.execute(f'SELECT * FROM {table}').fetchall())
                assert actual==rows, f'Restored rows differ in {table}'
            assert raw.execute('SELECT station_id,status FROM requests WHERE id=1').fetchone()=={'station_id':1,'status':'open'}
            assert raw.execute('SELECT version FROM scene_migrations').fetchone()['version']==4
            for table in ('users','businesses','stations','products','requests','scans'):
                maximum=raw.execute(f'SELECT COALESCE(MAX(id),0) AS n FROM {table}').fetchone()['n']
                next_id=raw.execute("SELECT nextval(pg_get_serial_sequence(%s,'id')) AS n",(table,)).fetchone()['n']
                assert next_id>maximum, f'Restored identity sequence collides in {table}'
    finally:
        # Only this test-created, random disposable database is removed.
        with connect(base) as raw:
            raw.autocommit=True
            raw.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(restored)))
