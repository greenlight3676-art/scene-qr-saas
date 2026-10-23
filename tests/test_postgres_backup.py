"""Real pg_dump/pg_restore drill on a separate disposable local CI database."""
import os
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
        counts={t:raw.execute(f'SELECT count(*) AS n FROM {t}').fetchone()['n'] for t in (*TABLES,*SECURITY_TABLES,*BACKEND_TABLES)}
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
            for table,count in counts.items():assert raw.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n']==count
            assert raw.execute('SELECT station_id,status FROM requests WHERE id=1').fetchone()=={'station_id':1,'status':'open'}
    finally:
        # Only this test-created, random disposable database is removed.
        with connect(base) as raw:
            raw.autocommit=True
            raw.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(restored)))
