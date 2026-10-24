"""Preflight never writes/sends or mistakes configuration for real acceptance."""
import json
import pytest
import backend_preflight as p
import managed_auth
import storage


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in ('SCENE_DATABASE_URL', 'SCENE_AUTH_MODE', 'SCENE_SUPABASE_PUBLISHABLE_KEY',
                 'SCENE_SECURE_COOKIE', 'SCENE_DEMO', 'SCENE_MAIL_FROM', 'SCENE_RESEND_API_KEY'):
        monkeypatch.delenv(name, raising=False)


def configured(monkeypatch):
    monkeypatch.setenv('SCENE_DATABASE_URL', 'postgresql://runtime:synthetic-private-password@db.example.invalid/postgres?sslmode=verify-full')
    monkeypatch.setenv('SCENE_AUTH_MODE', 'supabase')
    monkeypatch.setenv('SCENE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_synthetic-private-key')
    monkeypatch.setenv('SCENE_SECURE_COOKIE', '1')
    monkeypatch.setenv('SCENE_DEMO', '0')


def test_missing_credentials_are_blocked_without_network(monkeypatch):
    monkeypatch.setattr(storage, 'verify_postgres', lambda *a: pytest.fail('Unexpected connection'))
    monkeypatch.setattr(managed_auth, 'call', lambda *a: pytest.fail('Unexpected provider request'))
    assert [r['status'] for r in p.run()] == ['blocked', 'blocked', 'blocked']


def test_offline_configured_checks_do_not_connect_or_claim_acceptance(monkeypatch):
    configured(monkeypatch)
    monkeypatch.setattr(storage, 'verify_postgres', lambda *a: pytest.fail('Unexpected connection'))
    monkeypatch.setattr(managed_auth, 'call', lambda *a: pytest.fail('Unexpected provider request'))
    assert [r['status'] for r in p.run()] == ['not_run', 'not_run', 'blocked']


def test_explicit_online_checks_use_read_only_validators(monkeypatch):
    configured(monkeypatch)
    seen=[]
    monkeypatch.setattr(storage, 'verify_postgres', lambda url: seen.append('database'))
    def provider(path):
        assert path=='settings'  # No signup, user mutation, recovery or send.
        seen.append('auth')
        return {'mailer_autoconfirm':False, 'external':{'email':True}}
    monkeypatch.setattr(managed_auth, 'call', provider)
    assert p.run('database', True)[0]['status']=='verified_read_only'
    assert p.run('auth', True)[0]['status']=='verified_read_only'
    assert seen==['database','auth']


@pytest.mark.parametrize('check', ['database','auth'])
def test_provider_and_database_errors_never_expose_secrets(monkeypatch,check,capsys):
    configured(monkeypatch)
    def fail(*args):raise RuntimeError('synthetic-private-password sb_publishable_synthetic-private-key')
    monkeypatch.setattr(storage,'verify_postgres',fail)
    monkeypatch.setattr(managed_auth,'require_email_confirmation',fail)
    assert p.main(['--check',check,'--online'])==2
    output=capsys.readouterr().out
    assert json.loads(output)['checks'][0]['status']=='blocked'
    assert 'synthetic-private' not in output and 'postgresql://' not in output


def test_mail_configuration_is_never_reported_as_delivery(monkeypatch):
    monkeypatch.setenv('SCENE_MAIL_FROM','sender@example.invalid')
    monkeypatch.setenv('SCENE_RESEND_API_KEY','re_synthetic-private-key')
    assert p.run('mail',True)[0]['status']=='not_run'


def test_unsafe_auth_configuration_is_blocked(monkeypatch):
    configured(monkeypatch)
    monkeypatch.setenv('SCENE_SECURE_COOKIE','0')
    assert p.run('auth',True)[0]['status']=='blocked'
