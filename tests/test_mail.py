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
