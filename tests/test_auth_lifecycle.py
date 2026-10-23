"""Provider-isolated verification, recovery and onboarding contracts."""
import base64
import json
import secrets
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from test_api import registration
import server
import managed_auth
import auth_backend


def fake_token(iat):
    body=base64.urlsafe_b64encode(json.dumps({'iat':iat}).encode()).decode().rstrip('=')
    return 'synthetic.'+body+'.signature'


def provider(monkeypatch,email,subject):
    token=fake_token(server.ts()+1)
    user={'id':subject,'email':email,'email_confirmed_at':'synthetic-confirmation','is_anonymous':False}
    calls=[]
    def call(path,payload=None,**kwargs):
        calls.append((path,payload,kwargs))
        if path=='verify' or path.startswith('token?'):return {'access_token':token,'expires_in':900}
        if path=='user':return user
        return {}
    monkeypatch.setenv('SCENE_AUTH_MODE','supabase')
    monkeypatch.setattr(managed_auth,'call',call)
    return token,calls


def test_managed_registration_verification_onboarding_invitation_and_logout(monkeypatch):
    email='managed-new-owner@example.invalid';subject='11111111-1111-4111-8111-111111111111'
    token,calls=provider(monkeypatch,email,subject)
    owner=TestClient(server.app)
    result=owner.post('/api/auth/signup',json={'email':email,'password':'SyntheticPassword123!','name':'Verified onboarding','industry':'auto'})
    assert result.status_code==202 and result.json()['verification_required']
    assert owner.get('/api/me').status_code==401
    assert TestClient(server.app).post('/api/auth/verify',json={'token':'123456'}).status_code==410
    result=owner.post('/api/auth/verify',json={'token':'123456'})
    assert result.status_code==200,result.text
    slug=result.json()['organization']['slug']
    assert owner.post('/api/auth/verify',json={'token':'123456'}).status_code==410
    me=owner.get('/api/me').json();csrf={'x-scene-csrf':me['csrf']}
    assert me['businesses'][0]['role']=='owner'
    invite=owner.post(f'/api/admin/{slug}/invites',headers=csrf,json={'email':'managed-staff@example.invalid','role':'staff'})
    assert invite.status_code==200 and invite.json()['delivery']=='queued'
    link=invite.json()['join_url'].split('invite=')[1]
    staff=TestClient(server.app)
    provider(monkeypatch,'managed-staff@example.invalid','22222222-2222-4222-8222-222222222222')
    assert staff.post('/api/auth/join',json={'email':'managed-staff@example.invalid','password':'SyntheticPassword123!','token':link}).status_code==200
    # Restore the owner's exact provider identity before authorizing owner operations.
    provider(monkeypatch,email,subject)
    assert owner.post('/api/auth/logout-all',headers=csrf,json={}).status_code==200
    assert owner.get('/api/me').status_code==401


def test_recovery_is_restricted_csrf_bound_and_revokes_before_external_write(monkeypatch):
    email='managed-recovery@example.invalid';subject='33333333-3333-4333-8333-333333333333'
    token,calls=provider(monkeypatch,email,subject)
    client=TestClient(server.app)
    assert client.post('/api/auth/login',json={'email':email,'password':'SyntheticPassword123!'}).status_code==200
    assert client.post('/api/auth/recover',json={'email':email}).status_code==200
    assert client.post('/api/auth/verify',json={'token_hash':'synthetic-recovery-hash'}).json()['recovery'] is True
    assert client.get('/api/me').status_code==401
    csrf=client.get('/api/auth/recovery-session').json()['csrf']
    assert client.post('/api/auth/complete-recovery',json={'password':'SyntheticNewPassword123!'}).status_code==403
    # Simulate provider failure after the local revoke committed.
    real=managed_auth.call
    def fail_password(path,payload=None,**kwargs):
        if kwargs.get('method')=='PUT':raise managed_auth.AuthError()
        return real(path,payload,**kwargs)
    monkeypatch.setattr(managed_auth,'call',fail_password)
    result=client.post('/api/auth/complete-recovery',json={'password':'SyntheticNewPassword123!'},headers={'x-scene-csrf':csrf})
    assert result.status_code==503
    assert client.get('/api/auth/recovery-session').status_code==401
    with server.db() as c:
        assert c.execute('SELECT revoked_before FROM auth_blocks WHERE subject=?',(subject,)).fetchone()
        uid=c.execute('SELECT user_id FROM auth_identities WHERE subject=?',(subject,)).fetchone()['user_id']
        assert not c.execute('SELECT 1 FROM sessions WHERE user_id=?',(uid,)).fetchone()
    assert client.post('/api/auth/login',json={'email':email,'password':'SyntheticPassword123!'}).status_code==401
    # A fresh provider-verified recovery code is the only way out of pending reset.
    monkeypatch.setattr(managed_auth,'call',real)
    assert client.post('/api/auth/recover',json={'email':email}).status_code==200
    assert client.post('/api/auth/verify',json={'token':'654321'}).status_code==200
    csrf=client.get('/api/auth/recovery-session').json()['csrf']
    assert client.post('/api/auth/complete-recovery',json={'password':'SyntheticNewPassword123!'},headers={'x-scene-csrf':csrf}).status_code==200
    assert client.post('/api/auth/reset-password',json={'access_token':token,'password':'AnotherSyntheticPassword123!'}).status_code==401


def test_verification_mismatch_does_not_provision_account(monkeypatch):
    _,calls=provider(monkeypatch,'different@example.invalid','44444444-4444-4444-8444-444444444444')
    client=TestClient(server.app)
    assert client.post('/api/auth/signup',json={'email':'expected@example.invalid','password':'SyntheticPassword123!','name':'Expected','industry':'auto'}).status_code==202
    assert client.post('/api/auth/verify',json={'token':'123456'}).status_code==401
    with server.db() as c:assert not c.execute('SELECT id FROM users WHERE email=?',('expected@example.invalid',)).fetchone()


def test_logout_can_revoke_local_cookie_during_provider_outage(monkeypatch):
    email='managed-outage-logout@example.invalid';subject='55555555-5555-4555-8555-555555555555'
    provider(monkeypatch,email,subject)
    client=TestClient(server.app)
    assert client.post('/api/auth/login',json={'email':email,'password':'SyntheticPassword123!'}).status_code==200
    csrf=client.get('/api/me').json()['csrf']
    with patch.object(managed_auth,'verified_user',side_effect=managed_auth.AuthError()):
        assert client.get('/api/me').status_code==401
        assert client.post('/api/auth/logout',json={},headers={'x-scene-csrf':csrf}).status_code==200
    assert not client.cookies.get('scene_session')


def test_legacy_identity_migration_requires_both_credentials_and_never_reassigns(monkeypatch):
    client=TestClient(server.app)
    slug,_=registration(client,'legacy-dual-proof@example.invalid','Legacy dual proof')
    token,_=provider(monkeypatch,'legacy-dual-proof@example.invalid','66666666-6666-4666-8666-666666666666')
    body={'access_token':token,'legacy_password':'WrongSyntheticPassword!'}
    assert client.post('/api/auth/migrate-identity',json=body).status_code==401
    body['legacy_password']='ExampleStrongPassword123!'
    assert client.post('/api/auth/migrate-identity',json=body).status_code==200
    me=client.get('/api/me').json()
    assert me['businesses'][0]['slug']==slug and me['businesses'][0]['role']=='owner'
    assert client.post('/api/auth/migrate-identity',json=body).status_code==409
    provider(monkeypatch,'unrelated-provider@example.invalid','77777777-7777-4777-8777-777777777777')
    assert TestClient(server.app).post('/api/auth/migrate-identity',json=body).status_code==401
