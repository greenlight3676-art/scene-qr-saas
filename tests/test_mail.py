"""No mail is sent: injected transports prove outbox retries and revocation."""
from fastapi.testclient import TestClient
from test_api import registration
import server
import mail_delivery


def test_invitation_outbox_retry_acceptance_idempotency_and_revoke():
    c=TestClient(server.app)
    slug,headers=registration(c,'outbox-owner@example.invalid','Outbox fixture')
    result=c.post(f'/api/admin/{slug}/invites',headers=headers,json={'email':'outbox-staff@example.invalid','role':'staff'})
    assert result.json()['delivery']=='queued'
    bid=c.get('/api/admin/'+slug).json()['id']
    def outage(*args):raise mail_delivery.DeliveryError()
    assert mail_delivery.process_one(server,outage,bid)=='retry'
    listing=c.get(f'/api/admin/{slug}/mail').json()['messages']
    assert listing[0]['attempts']==1 and listing[0]['state']=='pending'
    assert 'payload' not in listing[0]
    bid=c.get('/api/admin/'+slug).json()['id']
    with server.db() as db:
        server.scope(db,'scene.tenant_id',bid)
        db.execute('UPDATE mail_outbox SET next_attempt=0 WHERE business_id=?',(bid,))
    calls=[]
    assert mail_delivery.process_one(server,lambda payload,key:calls.append((payload,key)) or 'synthetic-provider-id',bid)=='accepted'
    assert mail_delivery.process_one(server,lambda *args:(_ for _ in ()).throw(AssertionError('Duplicate send')),bid)=='empty'
    assert len(calls)==1
    c.post(f'/api/admin/{slug}/invites',headers=headers,json={'email':'revoked-staff@example.invalid','role':'staff'})
    invite_id=c.get(f'/api/admin/{slug}/invites').json()['invites'][-1]['id']
    assert c.post(f'/api/admin/{slug}/invites/{invite_id}/revoke',headers=headers,json={}).status_code==200
    # Revoke all queued invitations for deterministic synthetic fixture verification.
    for invite in c.get(f'/api/admin/{slug}/invites').json()['invites']:
        c.post(f'/api/admin/{slug}/invites/{invite["id"]}/revoke',headers=headers,json={})
    assert mail_delivery.process_one(server,lambda *args:(_ for _ in ()).throw(AssertionError('Revoked invitation sent')),bid)=='review'


def test_configured_invitation_sends_after_commit_and_delivery_is_provider_checked(monkeypatch):
    import json
    monkeypatch.setenv('SCENE_RESEND_API_KEY','re_synthetic_never_real')
    monkeypatch.setenv('SCENE_MAIL_FROM','sender@example.invalid')
    monkeypatch.setenv('SCENE_MAIL_SEND','1')
    owner=TestClient(server.app);other=TestClient(server.app)
    slug,headers=registration(owner,'delivery-owner@example.invalid','Delivery fixture')
    registration(other,'delivery-other@example.invalid','Another delivery tenant')
    calls=[]
    def transport(payload,key):
        # Reading the durable record here would deadlock on PostgreSQL if the
        # invitation transaction were still open when the background task ran.
        calls.append(json.loads(payload));return 'synthetic-provider-id'
    monkeypatch.setattr(mail_delivery,'send',transport)
    result=owner.post(f'/api/admin/{slug}/invites',headers=headers,json={'email':'staff@example.invalid','role':'staff'})
    assert result.status_code==200 and len(calls)==1
    listing=owner.get(f'/api/admin/{slug}/mail').json()
    assert listing['enabled'] and listing['scope']=='team_invitations' and not listing['sms_enabled']
    msg=listing['messages'][0];assert msg['state']=='accepted'
    path=f'/api/admin/{slug}/mail/{msg["id"]}/delivery'
    monkeypatch.setattr(mail_delivery,'delivery_status',lambda _: 'bounced')
    assert owner.get(path).json()['delivered'] is False
    monkeypatch.setattr(mail_delivery,'delivery_status',lambda _: 'delivered')
    assert owner.get(path).json()['delivered'] is True
    assert other.get(path).status_code==404
    assert TestClient(server.app).get(path).status_code==401
    assert owner.post(f'/api/admin/{slug}/mail/process',json={}).status_code==403
    assert owner.post(f'/api/admin/{slug}/mail/process',json={},headers=headers).json()['result']=='empty'
    assert len(calls)==1


def test_delivery_transport_filters_provider_data_and_sanitizes_errors(monkeypatch):
    import io
    import json
    from urllib.error import URLError
    monkeypatch.setenv('SCENE_RESEND_API_KEY','re_synthetic_never_real')
    monkeypatch.setenv('SCENE_MAIL_FROM','sender@example.invalid')
    def response(request,timeout):
        assert request.full_url=='https://api.resend.com/emails/synthetic-id'
        return io.BytesIO(json.dumps({'id':'synthetic-id','last_event':'delivered','text':'private content'}).encode())
    monkeypatch.setattr(mail_delivery,'urlopen',response)
    assert mail_delivery.delivery_status('synthetic-id')=='delivered'
    def unavailable(*a,**k):raise URLError('private provider response')
    monkeypatch.setattr(mail_delivery,'urlopen',unavailable)
    import pytest
    with pytest.raises(mail_delivery.DeliveryError) as error:mail_delivery.delivery_status('synthetic-id')
    assert 'private' not in str(error.value)
