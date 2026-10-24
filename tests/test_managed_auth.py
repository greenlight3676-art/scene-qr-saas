"""Synthetic provider responses only; these tests never send email or call Supabase."""
from unittest.mock import patch
import pytest
import managed_auth

SUBJECT = '12345678-1234-4567-8901-123456789012'
TOKEN = 'synthetic-access-token-for-tests'


def test_identity_requires_provider_verified_email_and_nonanonymous_subject():
    for user in ({'id': SUBJECT}, {'id': SUBJECT, 'email_confirmed_at': 'synthetic', 'is_anonymous': True},
                 {'id': 'malformed', 'email_confirmed_at': 'synthetic'}):
        with patch.object(managed_auth, 'call', return_value=user):
            with pytest.raises(managed_auth.AuthError):
                managed_auth.verified_user(TOKEN)
    with patch.object(managed_auth, 'call', return_value={'id': SUBJECT, 'email_confirmed_at': 'synthetic',
                                                      'user_metadata': {'role': 'owner'}}):
        assert managed_auth.verified_user(TOKEN) == SUBJECT


def test_managed_config_rejects_secret_keys_insecure_cookies_and_demo(monkeypatch):
    monkeypatch.setenv('SCENE_AUTH_MODE', 'supabase')
    monkeypatch.setenv('SCENE_SUPABASE_PUBLISHABLE_KEY', 'sb_secret_synthetic-never-valid')
    with pytest.raises(RuntimeError, match='publishable'):
        managed_auth.validate_config()
    monkeypatch.setenv('SCENE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_synthetic-never-valid')
    monkeypatch.setenv('SCENE_SECURE_COOKIE', '0')
    with pytest.raises(RuntimeError, match='secure cookies'):
        managed_auth.validate_config()
    monkeypatch.setenv('SCENE_SECURE_COOKIE', '1')
    monkeypatch.setenv('SCENE_DEMO', '0')
    managed_auth.validate_config()


def test_provider_error_does_not_expose_secrets(monkeypatch):
    from urllib.error import URLError
    monkeypatch.setenv('SCENE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_synthetic-never-valid')
    with patch.object(managed_auth, 'urlopen', side_effect=URLError('sensitive-provider-body')):
        with pytest.raises(managed_auth.AuthError) as error:
            managed_auth.call('token?grant_type=password', {'password': 'synthetic-secret'})
    assert 'sensitive' not in str(error.value)
    assert 'synthetic-secret' not in str(error.value)


def test_managed_session_mapping_revocation_and_recovery(monkeypatch):
    from fastapi.testclient import TestClient
    from test_api import registration
    import server
    c = TestClient(server.app)
    slug, headers = registration(c, 'managed-fixture@example.invalid', 'Managed fixture')
    uid = None
    with server.db() as db:
        uid = db.execute('SELECT id FROM users WHERE email=?', ('managed-fixture@example.invalid',)).fetchone()['id']
    monkeypatch.setenv('SCENE_AUTH_MODE', 'supabase')
    monkeypatch.setattr(managed_auth, 'password_login', lambda *args: (SUBJECT, TOKEN, 300))
    monkeypatch.setattr(managed_auth, 'verified_user', lambda token: SUBJECT if token == TOKEN else (_ for _ in ()).throw(managed_auth.AuthError()))
    # A beta session and an email match grant no managed identity.
    assert c.get('/api/me').status_code == 401
    assert c.post('/api/auth/login', json={'email':'managed-fixture@example.invalid','password':'synthetic'}).status_code == 403
    with server.db() as db:
        server.scope(db,'scene.auth_subject',SUBJECT)
        db.execute('INSERT INTO auth_identities(subject,user_id) VALUES(?,?)', (SUBJECT, uid))
    with patch.object(managed_auth, 'call', return_value={'id':SUBJECT,
            'email':'managed-fixture@example.invalid','email_confirmed_at':'synthetic'}):
        assert c.post('/api/auth/login', json={'email':'managed-fixture@example.invalid','password':'synthetic'}).status_code == 200
    assert c.get('/api/me').status_code == 200
    assert c.patch('/api/admin/'+slug+'/settings', json={'name':'Test','tagline':'','accent':'#ffffff'}, headers=headers).status_code == 403
    assert c.post('/api/auth/signup', json={'email':'new@example.invalid','password':'ExampleStrong123!','name':'New'}).status_code == 503
    # Provider outage/revocation fails closed on every private operation.
    with patch.object(managed_auth, 'verified_user', side_effect=managed_auth.AuthError()):
        assert c.get('/api/admin/'+slug).status_code == 401
    calls = []
    monkeypatch.setattr(managed_auth, 'call', lambda *args, **kwargs: calls.append((args,kwargs)) or {})
    assert c.post('/api/auth/reset-password', json={'access_token':TOKEN,'password':'SyntheticNewPassword123!'}).status_code == 200
    assert calls[0][0][0] == 'user' and calls[0][1]['method'] == 'PUT'
    assert c.get('/api/me').status_code == 401
    with server.db() as db:
        assert not db.execute('SELECT * FROM sessions WHERE user_id=?', (uid,)).fetchall()
    with patch.object(managed_auth, 'call', side_effect=managed_auth.AuthError()):
        assert c.post('/api/auth/recover', json={'email':'absent@example.invalid'}).status_code == 200


def test_audit_is_private_tenant_scoped_and_has_no_contact_payload():
    from fastapi.testclient import TestClient
    from test_api import registration
    import server
    a, b, guest = TestClient(server.app), TestClient(server.app), TestClient(server.app)
    slug, headers = registration(a, 'audit-a@example.invalid', 'Audit Tenant A')
    registration(b, 'audit-b@example.invalid', 'Audit Tenant B')
    token = a.get('/api/admin/'+slug).json()['stations'][0]['token']
    result = guest.post('/api/q/'+token+'/requests', json={'kind':'question', 'message':'Synthetic private inquiry',
        'client_key':'synthetic-audit-client-key', 'customer_contact':'private@example.invalid', 'reply_consent':True})
    assert result.status_code == 200, result.text
    rid = result.json()['request_id']
    assert a.patch(f'/api/admin/{slug}/requests/{rid}/lead', json={'status':'qualified'}, headers=headers).status_code == 200
    events = a.get('/api/admin/'+slug+'/audit').json()['events']
    assert {'request.created','lead.qualified'} <= {event['action'] for event in events}
    assert 'private@example.invalid' not in str(events) and 'Synthetic private inquiry' not in str(events)
    assert b.get('/api/admin/'+slug+'/audit').status_code == 404
    assert guest.get('/api/admin/'+slug+'/audit').status_code == 401


def test_provider_confirmation_policy_fails_closed():
    for settings in ({}, {'mailer_autoconfirm':True,'external':{'email':True}},
                     {'mailer_autoconfirm':False,'external':{'email':False}}):
        with patch.object(managed_auth,'call',return_value=settings):
            with pytest.raises(managed_auth.AuthError):managed_auth.require_email_confirmation()
    with patch.object(managed_auth,'call',return_value={'mailer_autoconfirm':False,'external':{'email':True}}):
        managed_auth.require_email_confirmation()
