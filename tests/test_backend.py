"""Backend contracts and tenant workflows, using isolated synthetic fixtures only."""
import json
import secrets
import sqlite3
import pytest
from fastapi.testclient import TestClient
from test_api import registration
import server


def account(label):
    c=TestClient(server.app)
    slug,headers=registration(c,label+'@example.invalid',label)
    board=c.get('/api/admin/'+slug).json()
    return c,slug,headers,board


def test_organizations_locations_qr_guest_customer_end_to_end(monkeypatch):
    a,slug,headers,board=account('extended-tenant-a')
    b,foreign,bheaders,_=account('extended-tenant-b')
    guest=TestClient(server.app)
    org=a.post('/api/organizations',json={'name':'Another organization','industry':'auto'},headers=headers)
    assert org.status_code==201,org.text
    assert len(a.get('/api/organizations').json()['organizations'])==2
    location=a.post(f'/api/admin/{slug}/locations',json={'name':'Synthetic East','address':'Synthetic test address'},headers=headers)
    assert location.status_code==201,location.text
    lid=location.json()['id'];sid=board['stations'][0]['id'];token=board['stations'][0]['token']
    assert b.patch(f'/api/admin/{foreign}/qr/{sid}',json={'location_id':lid},headers=bheaders).status_code==404
    assert a.patch(f'/api/admin/{slug}/qr/{sid}',json={'location_id':lid,'destination':'service','title':'Hello','message':'Test content'},headers=headers).status_code==200
    scanned=guest.get('/api/q/'+token)
    assert scanned.status_code==200,scanned.text
    data=scanned.json()
    assert data['location_id']==lid and data['content']['title']=='Hello'
    monkeypatch.setenv('SCENE_REQUIRE_GUEST_SESSION','1')
    body={'kind':'question','message':'Synthetic inquiry','client_key':secrets.token_hex(16),
          'customer_name':'Synthetic Guest','customer_contact':'synthetic@example.invalid','reply_consent':True}
    assert guest.post('/api/q/'+token+'/requests',json=body).status_code==401
    issued=guest.post('/api/q/'+token+'/session').json()
    request=guest.post('/api/q/'+token+'/requests',json=body,headers={'x-scene-guest':issued['guest_token']})
    assert request.status_code==200,request.text
    rid=request.json()['request_id'];receipt=request.json()['ticket']
    customers=a.get(f'/api/admin/{slug}/customers').json()['customers']
    assert len(customers)==1
    assert b.get(f'/api/admin/{slug}/customers').status_code==404
    assert guest.get(f'/api/admin/{slug}/customers').status_code==401
    public=guest.get('/api/businesses/'+slug).json()
    assert 'synthetic@example.invalid' not in json.dumps(public) and 'owner_id' not in public
    assert a.post(f'/api/admin/{slug}/customers/{customers[0]["id"]}/redact',headers=headers,json={}).status_code==200
    assert a.get(f'/api/admin/{slug}').json()['requests'][0]['customer_contact'] is None
    assert a.patch(f'/api/admin/{slug}/requests/{rid}',json={'status':'completed'},headers=headers).status_code==200
    assert guest.get(f'/api/guest/requests/{rid}',headers={'x-scene-ticket':receipt}).json()['status']=='completed'
    assert a.patch(f'/api/admin/{slug}/locations/{lid}',json={'name':'Synthetic East','active':False},headers=headers).status_code==200
    assert guest.get('/api/q/'+token).status_code==404
    assert guest.post('/api/q/'+token+'/session').status_code==404
    assert guest.get(f'/api/guest/requests/{rid}',headers={'x-scene-ticket':receipt}).status_code==200
    assert a.get(f'/api/admin/{slug}/reports').json()['statuses']==[{'status':'completed','count':1}]
    assert a.get(f'/api/admin/{slug}/reports?start=2&end=1').status_code==400


def test_guest_tokens_station_binding_expiry_and_info_destination(monkeypatch):
    a,slug,headers,board=account('guest-scope-fixture')
    monkeypatch.setenv('SCENE_REQUIRE_GUEST_SESSION','1')
    guest=TestClient(server.app)
    token,other=board['stations'][0]['token'],board['stations'][1]['token']
    value=guest.post('/api/q/'+token+'/session').json()['guest_token']
    body={'kind':'service','client_key':secrets.token_hex(16)}
    assert guest.post('/api/q/'+other+'/requests',json=body,headers={'x-scene-guest':value}).status_code==401
    with server.db() as c:
        server.scope(c,'scene.tenant_id',board['id'])
        c.execute('UPDATE guest_sessions SET expires_at=1 WHERE token_hash=?',(server.sha(value),))
    assert guest.post('/api/q/'+token+'/requests',json=body,headers={'x-scene-guest':value}).status_code==401
    assert a.patch(f'/api/admin/{slug}/qr/{board["stations"][0]["id"]}',headers=headers,json={'destination':'info'}).status_code==200
    value=guest.post('/api/q/'+token+'/session').json()['guest_token']
    assert guest.post('/api/q/'+token+'/requests',json=body,headers={'x-scene-guest':value}).status_code==409


def test_durable_rate_limits_body_limits_and_private_validation():
    guest=TestClient(server.app)
    for _ in range(12): assert guest.post('/api/auth/login',json={'email':'absent@example.invalid','password':'synthetic'}).status_code==401
    server.RATES.clear()  # Clearing process memory must not reset the persisted limit.
    assert guest.post('/api/auth/login',json={'email':'absent@example.invalid','password':'synthetic'}).status_code==429
    assert guest.post('/api/auth/login',content=b'x'*65537).status_code==413
    bad=guest.post('/api/auth/login',json={'password':'private-synthetic-value'*10})
    assert bad.status_code==422 and 'private-synthetic-value' not in bad.text
    assert len(bad.headers['x-request-id'])==32
    assert guest.get('/readyz').json()=={'ok':True}


def test_new_permissions_and_invitation_email_binding():
    owner,slug,headers,board=account('new-permissions')
    staff=TestClient(server.app)
    invite=owner.post(f'/api/admin/{slug}/invites',headers=headers,json={'role':'staff','email':'staff-right@example.invalid'}).json()
    token=invite['join_url'].split('invite=')[1]
    payload={'email':'staff-wrong@example.invalid','password':'SyntheticPassword123!','token':token}
    assert staff.post('/api/auth/join',json=payload).status_code==403
    payload['email']='staff-right@example.invalid'
    assert staff.post('/api/auth/join',json=payload).status_code==200
    csrf={'x-scene-csrf':staff.get('/api/me').json()['csrf']}
    assert staff.get(f'/api/admin/{slug}/customers').status_code==403
    assert staff.get(f'/api/admin/{slug}/reports').status_code==403
    assert staff.get(f'/api/admin/{slug}/audit').status_code==403
    assert staff.post(f'/api/admin/{slug}/locations',json={'name':'Denied'},headers=csrf).status_code==403
    assert staff.post('/api/auth/accept-invite',json={'token':token},headers=csrf).status_code==410


def test_sqlite_constraints_reject_cross_tenant_location_and_customer():
    if server.DATABASE_URL: pytest.skip('SQLite trigger regression; PostgreSQL constraints tested separately')
    a,slug,headers,board=account('constraint-owner-a')
    b,foreign,_,other=account('constraint-owner-b')
    lid=a.post(f'/api/admin/{slug}/locations',json={'name':'Constraint location'},headers=headers).json()['id']
    cid=a.post(f'/api/admin/{slug}/customers',json={'name':'Synthetic','contact':'synthetic@example.invalid','consent':True},headers=headers).json()['id']
    with server.db() as c:
        with pytest.raises(sqlite3.IntegrityError):
            c.execute('UPDATE stations SET location_id=? WHERE id=?',(lid,other['stations'][0]['id']))
        with pytest.raises(sqlite3.IntegrityError):
            c.execute('INSERT INTO requests(business_id,station_id,kind,receipt_hash,client_key,created_at,updated_at,customer_id) VALUES(?,?,?,?,?,?,?,?)',
                      (other['id'],other['stations'][0]['id'],'question','synthetic-hash','synthetic-cross-tenant-key',1,1,cid))


def test_concurrent_request_status_transition_has_one_winner():
    from concurrent.futures import ThreadPoolExecutor
    owner,slug,headers,board=account('concurrent-status-fixture')
    token=board['stations'][0]['token']
    result=TestClient(server.app).post('/api/q/'+token+'/requests',json={'kind':'service','client_key':secrets.token_hex(16)})
    rid=result.json()['request_id']
    cookie=owner.cookies.get('scene_session')
    def complete(_):
        c=TestClient(server.app);c.cookies.set('scene_session',cookie)
        return c.patch(f'/api/admin/{slug}/requests/{rid}',json={'status':'completed'},headers=headers).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(complete,range(2)))==[200,409]


def test_report_time_bounds_reject_database_integer_overflow():
    owner,slug,_,_=account('report-time-bounds')
    for key in ('start','end'):
        response=owner.get(f'/api/admin/{slug}/reports?{key}={2**63}')
        assert response.status_code==422
    assert owner.get(f'/api/admin/{slug}/reports?start=0&end={2**63-1}').status_code==200
