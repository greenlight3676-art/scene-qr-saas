"""Synthetic Stripe signatures, API results and subscriptions; no external calls."""
import hashlib
import hmac
import json
import secrets
import pytest
from fastapi.testclient import TestClient
from test_api import registration
import server
import billing

SECRET='whsec_synthetic_never_real'


def signed(event,stamp=None):
    stamp=server.ts() if stamp is None else stamp
    body=json.dumps(event,sort_keys=True).encode()
    signature=hmac.new(SECRET.encode(),str(stamp).encode()+b'.'+body,hashlib.sha256).hexdigest()
    return body,{'stripe-signature':f't={stamp},v1={signature}','content-type':'application/json'}


def fixture(monkeypatch,label):
    monkeypatch.setenv('SCENE_STRIPE_WEBHOOK_SECRETS',SECRET)
    monkeypatch.setenv('SCENE_STRIPE_PRICES','{"standard":"price_Synthetic"}')
    owner=TestClient(server.app)
    slug,headers=registration(owner,label+'@example.invalid',label)
    board=owner.get('/api/admin/'+slug).json()
    with server.db() as c:
        server.scope(c,'scene.tenant_id',board['id'])
        c.execute('INSERT INTO billing_accounts(business_id,customer_id,updated_at) VALUES(?,?,?)',(board['id'],'cus_'+str(board['id']),server.ts()))
    return owner,slug,headers,board


def event(board,identifier='evt_Synthetic',kind='customer.subscription.updated',created=None):
    return {'id':identifier,'type':kind,'livemode':False,'created':server.ts() if created is None else created,
            'data':{'object':{'id':'sub_Synthetic','customer':'cus_'+str(board['id'])}}}


def subscription(board,status='active'):
    return {'id':'sub_Synthetic','customer':'cus_'+str(board['id']),'status':status,'livemode':False,
            'items':{'data':[{'price':{'id':'price_Synthetic'},'current_period_end':server.ts()+3600}]}}


def test_signature_replay_tampering_rotation_and_live_mode(monkeypatch):
    monkeypatch.setenv('SCENE_STRIPE_WEBHOOK_SECRETS',SECRET)
    body,headers=signed({'id':'evt_Signature','type':'unknown','created':server.ts(),'livemode':False})
    client=TestClient(server.app)
    assert client.post('/api/billing/webhook',content=body,headers=headers).status_code==200
    assert client.post('/api/billing/webhook',content=body+b' ',headers=headers).status_code==400
    expired,eh=signed({'id':'evt_Expired'},stamp=server.ts()-301)
    assert client.post('/api/billing/webhook',content=expired,headers=eh).status_code==400
    future,fh=signed({'id':'evt_Future'},stamp=server.ts()+301)
    assert client.post('/api/billing/webhook',content=future,headers=fh).status_code==400
    live,lh=signed({'id':'evt_Live','type':'unknown','created':server.ts(),'livemode':True})
    assert client.post('/api/billing/webhook',content=live,headers=lh).status_code==400
    monkeypatch.setenv('SCENE_STRIPE_WEBHOOK_SECRETS','whsec_rotated_synthetic,'+SECRET)
    assert client.post('/api/billing/webhook',content=body,headers=headers).json()['duplicate'] is True
    monkeypatch.setenv('SCENE_STRIPE_SECRET_KEY','sk_live_synthetic')
    with pytest.raises(billing.BillingError):billing.configuration()


def test_webhook_canonical_state_idempotency_outage_and_entitlements(monkeypatch):
    owner,slug,csrf,board=fixture(monkeypatch,'billing-contract')
    client=TestClient(server.app)
    monkeypatch.setenv('SCENE_REQUIRE_SUBSCRIPTION','1')
    token=board['stations'][0]['token']
    request={'kind':'service','client_key':secrets.token_hex(16)}
    assert client.post('/api/q/'+token+'/requests',json=request).status_code==402
    calls=[]
    monkeypatch.setattr(billing,'call',lambda *args,**kwargs:calls.append(args) or subscription(board))
    payload,headers=signed(event(board))
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==200
    assert client.post('/api/billing/webhook',content=payload,headers=headers).json()['duplicate'] is True
    assert len(calls)==1
    assert client.post('/api/q/'+token+'/requests',json=request).status_code==200
    # The redirect and event's old snapshot do not authorize access: canonical state wins.
    monkeypatch.setattr(billing,'call',lambda *args,**kwargs:subscription(board,'canceled'))
    payload,headers=signed(event(board,'evt_Delayed',created=1))
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==200
    request['client_key']=secrets.token_hex(16)
    assert client.post('/api/q/'+token+'/requests',json=request).status_code==402
    assert owner.get(f'/api/admin/{slug}/billing').json()['subscription']['status']=='canceled'
    # Provider outages roll back dedupe state; retries remain possible.
    def outage(*args,**kwargs):raise billing.BillingError()
    monkeypatch.setattr(billing,'call',outage)
    payload,headers=signed(event(board,'evt_Retry'))
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==503
    with server.db() as c: assert not c.execute('SELECT 1 FROM billing_events WHERE event_id=?',('evt_Retry',)).fetchone()
    monkeypatch.setattr(billing,'call',lambda *args,**kwargs:subscription(board,'past_due'))
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==200
    changed=event(board,'evt_Retry');changed['created']=123
    payload,headers=signed(changed)
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==409


def test_checkout_is_owner_only_idempotent_and_server_priced(monkeypatch):
    owner,slug,csrf,board=fixture(monkeypatch,'checkout-contract')
    other=TestClient(server.app)
    _,other_headers=registration(other,'billing-foreign@example.invalid','billing-foreign')
    monkeypatch.setenv('SCENE_STRIPE_SECRET_KEY','sk_test_synthetic')
    monkeypatch.setattr(server,'PUBLIC_URL','https://scene.example.invalid')
    received=[]
    def call(path,fields=None,idempotency=None):
        received.append((path,fields,idempotency));return {'url':'https://checkout.stripe.com/c/pay/synthetic','livemode':False}
    monkeypatch.setattr(billing,'call',call)
    headers={**csrf,'Idempotency-Key':'synthetic-checkout-retry-key'}
    path=f'/api/admin/{slug}/billing/checkout'
    assert other.post(path,json={'plan':'standard'},headers=other_headers).status_code==400
    assert other.post(path,json={'plan':'standard'},headers={**other_headers,'Idempotency-Key':'synthetic-foreign-key'}).status_code==404
    assert owner.post(path,json={'plan':'attacker-price'},headers=headers).status_code==400
    assert owner.post(path,json={'plan':'standard','price_id':'price_Attacker'},headers=headers).status_code==200
    assert received[0][1]['line_items[0][price]']=='price_Synthetic'
    assert received[0][2].startswith('scene-checkout-'+str(board['id']))
    assert owner.post(path,json={'plan':'standard'},headers=headers).status_code==200
    assert received[0][2]==received[1][2]
    assert TestClient(server.app).get(f'/api/admin/{slug}/billing').status_code==401


def test_reconciliation_runs_off_event_loop_and_malformed_provider_state_retries(monkeypatch):
    import asyncio
    _,_,_,board=fixture(monkeypatch,'webhook-worker-contract')
    client=TestClient(server.app)
    worker_event=event(board,'evt_WorkerRetry')
    worker_event['data']['object']['id']='sub_WorkerRetry'
    payload,headers=signed(worker_event)
    def malformed(*args,**kwargs):
        # A synchronous provider/DB transaction must never run on an ASGI loop.
        with pytest.raises(RuntimeError):asyncio.get_running_loop()
        result=subscription(board);result['id']='sub_WorkerRetry'
        result['items']={'data':{'unexpected':'mapping'}}
        return result
    monkeypatch.setattr(billing,'call',malformed)
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==503
    with server.db() as c:
        assert not c.execute('SELECT 1 FROM billing_events WHERE event_id=?',('evt_WorkerRetry',)).fetchone()
        server.scope(c,'scene.tenant_id',board['id'])
        assert c.execute('SELECT status FROM billing_accounts WHERE business_id=?',(board['id'],)).fetchone()['status']=='unconfigured'
    def recovered(*args,**kwargs):
        result=subscription(board);result['id']='sub_WorkerRetry'
        return result
    monkeypatch.setattr(billing,'call',recovered)
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==200


@pytest.mark.parametrize('invalid', ['customer-object','timestamp-overflow'])
def test_malformed_signed_event_is_rejected_without_consuming_id(monkeypatch,invalid):
    _,_,_,board=fixture(monkeypatch,'malformed-event-'+invalid)
    value=event(board,'evt_Invalid'+invalid.replace('-',''))
    if invalid=='customer-object':value['data']['object']['customer']={'id':'cus_Attacker'}
    else:value['created']=2**63
    payload,headers=signed(value)
    response=TestClient(server.app).post('/api/billing/webhook',content=payload,headers=headers)
    assert response.status_code==400
    with server.db() as c:assert not c.execute('SELECT 1 FROM billing_events WHERE event_id=?',(value['id'],)).fetchone()


def test_live_mode_is_explicit_and_never_accepts_test_events_or_credentials(monkeypatch):
    _,_,_,board=fixture(monkeypatch,'live-mode-contract')
    monkeypatch.setenv('SCENE_STRIPE_SECRET_KEY','sk_live_synthetic_never_real')
    with pytest.raises(billing.BillingError):billing.configuration()
    monkeypatch.setenv('SCENE_BILLING_MODE','live')
    assert billing.configuration()=='sk_live_synthetic_never_real'
    client=TestClient(server.app)
    value=event(board,'evt_LiveModeContract')
    value['data']['object']['id']='sub_LiveSynthetic'
    payload,headers=signed(value)
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==400
    value['livemode']=True
    payload,headers=signed(value)
    # A live event cannot activate a subscription from a test-mode provider reply.
    monkeypatch.setattr(billing,'call',lambda *a,**k:subscription(board))
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==503
    def live_subscription(*a,**k):
        result=subscription(board);result['id']='sub_LiveSynthetic';result['livemode']=True;return result
    monkeypatch.setattr(billing,'call',live_subscription)
    assert client.post('/api/billing/webhook',content=payload,headers=headers).status_code==200
    monkeypatch.setenv('SCENE_STRIPE_SECRET_KEY','sk_test_synthetic_never_real')
    with pytest.raises(billing.BillingError):billing.configuration()


def test_billing_configuration_status_never_leaks_secrets_or_claims_payment(monkeypatch):
    owner,slug,_,_=fixture(monkeypatch,'billing-status-contract')
    monkeypatch.setenv('SCENE_STRIPE_SECRET_KEY','sk_test_synthetic_private')
    monkeypatch.setenv('SCENE_STRIPE_API_VERSION','2026-01-28.clover')
    value=owner.get(f'/api/admin/{slug}/billing')
    assert value.status_code==200
    assert value.json()['configured'] and value.json()['plans']==['standard']
    assert value.json()['mode']=='test' and value.json()['test_mode']
    assert 'synthetic_private' not in value.text and SECRET not in value.text
    monkeypatch.setenv('SCENE_STRIPE_API_VERSION','')
    assert not owner.get(f'/api/admin/{slug}/billing').json()['configured']
