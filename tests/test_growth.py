"""Real API tests: new data stays private, durable and revision guarded."""
import uuid
from fastapi.testclient import TestClient
from server import app, ts, db, RATES
from tests.test_api import registration


def setup(client):
    RATES.clear()
    slug,headers=registration(client,str(uuid.uuid4())+'@example.invalid','Growth '+uuid.uuid4().hex[:8])
    board=client.get('/api/admin/'+slug).json()
    token=board['stations'][0]['token']
    r=client.post('/api/q/'+token+'/requests',json={'kind':'question','message':'Tint quote','customer_name':'Sample','customer_contact':'sample@example.invalid','reply_consent':True,'client_key':uuid.uuid4().hex}).json()
    return slug,headers,r,token


def quote(**kw):
    return dict(revision=0,stage='quoted',quote_cents=35000,quote_description='Ceramic tint; excludes windshield',quote_expires=ts()+3600,**kw)


def test_quote_acceptance_revisions_outcomes_and_placement_report():
    with TestClient(app) as owner, TestClient(app) as guest:
        slug,h,r,token=setup(owner);rid=r['request_id'];base=f'/api/admin/{slug}/growth'
        owner.get('/api/q/'+token)
        saved=owner.put(base+'/config',headers=h,json={'profile':'tint','review_url':'https://example.com/reviews','booking_url':'https://example.com/book','setup_complete':True})
        assert saved.status_code==200,saved.text
        q=quote()
        assert owner.put(base+f'/jobs/{rid}',headers=h,json=q).status_code==200
        assert owner.put(base+f'/jobs/{rid}',headers=h,json=q).status_code==409
        receipt=f'/api/guest/requests/{rid}/journey';ticket={'x-scene-ticket':r['ticket']}
        public=guest.get(receipt,headers=ticket).json()
        assert public['quote_cents']==35000 and public['quote_revision']==1
        assert 'note' not in public and 'customer_contact' not in public and not public['return_links']
        assert guest.post(receipt,headers=ticket,json={'quote_revision':9,'decision':'accept'}).status_code==409
        assert guest.post(receipt,headers=ticket,json={'quote_revision':1,'decision':'accept'}).status_code==200
        accepted=owner.get(base+'/jobs').json()['jobs'][0]
        assert accepted['accepted_revision']==1 and accepted['stage']=='contacted'
        q.update(revision=accepted['revision'],stage='booked',appointment_at=ts()+86400)
        assert owner.put(base+f'/jobs/{rid}',headers=h,json=q).status_code==200
        q.update(revision=q['revision']+1,stage='won',revenue_cents=35000)
        assert owner.put(base+f'/jobs/{rid}',headers=h,json=q).status_code==200
        report=owner.get(base).json()
        assert report['stages']['won']==1 and report['placements'][0]['revenue_cents']==35000
        owner.patch(f'/api/admin/{slug}/requests/{rid}',headers=h,json={'status':'completed'})
        assert guest.get(receipt,headers=ticket).json()['return_links']['review_url']=='https://example.com/reviews'
        # Request/receipt remains operationally separate from job outcome.
        assert guest.get(f'/api/guest/requests/{rid}',headers=ticket).json()['status']=='completed'


def test_growth_tenant_csrf_staff_and_receipt_boundaries():
    with TestClient(app) as a, TestClient(app) as b, TestClient(app) as guest:
        sa,ha,ra,ta=setup(a);sb,hb,rb,tb=setup(b)
        base=f'/api/admin/{sa}/growth';rid=ra['request_id']
        assert guest.get(base).status_code==401
        assert b.get(base).status_code==404
        assert b.put(base+f'/jobs/{rid}',headers=hb,json=quote()).status_code==404
        assert a.put(base+f"/jobs/{rb['request_id']}",headers=ha,json=quote()).status_code==404
        assert a.put(base+f'/jobs/{rid}',json=quote()).status_code==403
        assert guest.get(f'/api/guest/requests/{rid}/journey').status_code==401
        assert guest.get(f'/api/guest/requests/{rid}/journey',headers={'x-scene-ticket':rb['ticket']}).status_code==404
        inv=a.post(f'/api/admin/{sa}/invites',headers=ha,json={'role':'staff'}).json()
        from urllib.parse import urlsplit,parse_qs
        token=parse_qs(urlsplit(inv['join_url']).query)['invite'][0]
        guest.post('/api/auth/join',json={'token':token,'email':uuid.uuid4().hex+'@example.invalid','password':'StrongAssistantPass12!'})
        hs={'x-scene-csrf':guest.get('/api/me').json()['csrf']}
        assert guest.get(base).status_code==403
        assert guest.get(base+'/jobs').status_code==403
        assert guest.put(base+'/config',headers=hs,json={}).status_code==403
        assert guest.put(base+f'/jobs/{rid}',headers=hs,json=quote()).status_code==403


def test_invalid_booking_revenue_expired_quote_and_followup_filters():
    with TestClient(app) as c:
        slug,h,r,_=setup(c);base=f'/api/admin/{slug}/growth';rid=r['request_id']
        assert c.put(base+'/config',headers=h,json={'review_url':'javascript:alert(1)'}).status_code==422
        assert c.put(base+f'/jobs/{rid}',headers=h,json={'revision':0,'stage':'booked'}).status_code==400
        assert c.put(base+f'/jobs/{rid}',headers=h,json={'revision':0,'stage':'new','revenue_cents':100}).status_code==400
        q=quote(followup_at=ts()-1)
        assert c.put(base+f'/jobs/{rid}',headers=h,json=q).status_code==200
        assert c.get(base).json()['due']==1
        assert len(c.get(base+'/jobs?due=true').json()['jobs'])==1
        assert len(c.get(base+'/jobs?search=nonexistent').json()['jobs'])==0
        assert c.get(base+'/jobs?stage=garbage').status_code==400
        with db() as con:
            # The expiry fixture must obey the same tenant scope as production.
            from server import scope
            bid=con.execute('SELECT id FROM businesses WHERE slug=?',(slug,)).fetchone()['id']
            scope(con,'scene.tenant_id',bid)
            con.execute('UPDATE growth_jobs SET quote_expires=? WHERE request_id=?',(ts()-10,rid))
        res=c.post(f'/api/guest/requests/{rid}/journey',headers={'x-scene-ticket':r['ticket']},json={'quote_revision':1,'decision':'accept'})
        assert res.status_code==409


def test_growth_never_nests_session_or_rate_limit_database_transactions(monkeypatch):
    # postgres_db takes a transaction advisory lock. A nested connection would block itself.
    import server as s
    import threading
    from contextlib import contextmanager
    with TestClient(app) as owner:
        slug,h,r,_=setup(owner);base=f'/api/admin/{slug}/growth';rid=r['request_id']
        original=s.db;local=threading.local()
        @contextmanager
        def guarded_db():
            assert not getattr(local,'inside',False),'Nested database transaction would deadlock PostgreSQL'
            local.inside=True
            try:
                with original() as c:yield c
            finally:local.inside=False
        original_limit=s.rate_limit
        def guarded_limit(*args,**kwargs):
            assert not getattr(local,'inside',False),'Durable rate limiter must run before opening database'
            return original_limit(*args,**kwargs)
        monkeypatch.setattr(s,'db',guarded_db);monkeypatch.setattr(s,'rate_limit',guarded_limit)
        assert owner.get(base).status_code==200
        assert owner.get(base+'/jobs').status_code==200
        assert owner.put(base+'/config',headers=h,json={}).status_code==200
        assert owner.put(base+f'/jobs/{rid}',headers=h,json=quote()).status_code==200
        ticket={'x-scene-ticket':r['ticket']}
        assert owner.get(f'/api/guest/requests/{rid}/journey',headers=ticket).status_code==200
        assert owner.post(f'/api/guest/requests/{rid}/journey',headers=ticket,json={'quote_revision':1,'decision':'accept'}).status_code==200
