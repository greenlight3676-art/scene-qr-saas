"""SCENE beta end-to-end security and workflow tests; isolated temp SQLite DB."""
import os
import sys
import tempfile
import pytest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEMP=tempfile.TemporaryDirectory()
os.environ['SCENE_DB']=str(Path(TEMP.name)/'scene-test.sqlite')
os.environ['SCENE_DEMO']='1'
os.environ['SCENE_DATABASE_URL']=''
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from server import app, db, sha, ts, RATES


@pytest.fixture(autouse=True)
def reset_rate_limits():
    RATES.clear()


def registration(client,email,name):
    response=client.post('/api/auth/signup',json={'email':email,'password':'ExampleStrongPassword123!', 'name':name,'industry':'auto'})
    assert response.status_code==200,response.text
    csrf=client.get('/api/me').json()['csrf']
    return response.json()['slug'],{'x-scene-csrf':csrf}


def test_demo_scan_customer_request_staff_queue_and_private_receipt():
    with TestClient(app) as owner, TestClient(app) as guest:
        health=guest.get('/healthz');assert health.json()['mode']=='demo'
        demo=guest.get('/api/demo/trio-demo'); assert demo.status_code==200
        token=demo.json()['q']
        qr=guest.get(f'/api/qr/{token}.png')
        assert qr.status_code==200 and qr.content.startswith(b'\x89PNG')
        assert guest.get('/q/'+token,follow_redirects=False).status_code==302
        catalog=guest.get('/api/q/'+token)
        assert catalog.status_code==200
        assert catalog.json()['slug']=='trio-demo'
        assert len(catalog.json()['stations'])==1
        assert 'token' not in str(catalog.json())
        product=catalog.json()['products'][0]['id']
        assert guest.post(f'/api/q/{token}/requests',json={'kind':'checkin','client_key':'test-checkin-too-long'}).status_code==400
        assert guest.post(f'/api/q/{token}/requests',json={'kind':'order','product_id':999999,'client_key':'test-bad-product-1-1-1'}).status_code==400
        r=guest.post(f'/api/q/{token}/requests',json={'kind':'order','product_id':product,'client_key':'e2e-order-1-nonrepeating'})
        assert r.status_code==200,r.text
        rid=r.json()['request_id'];ticket=r.json()['ticket']
        duplicate=guest.post(f'/api/q/{token}/requests',headers={'x-scene-ticket':ticket},json={'kind':'order','product_id':product,'client_key':'e2e-order-1-nonrepeating'})
        assert duplicate.json()['already_sent'] is True
        assert duplicate.json()['request_id']==rid
        assert guest.get('/api/guest/requests/'+str(rid)).status_code==401
        assert guest.get('/api/guest/requests/'+str(rid),headers={'x-scene-ticket':'z'*44}).status_code==404
        assert guest.get('/api/guest/requests/'+str(rid),headers={'x-scene-ticket':ticket}).json()['status']=='open'
        assert owner.post('/api/auth/login',json={'email':'demo@scene.local','password':'SceneDemo2026!'}).status_code==200
        csrf={'x-scene-csrf':owner.get('/api/me').json()['csrf']}
        board=owner.get('/api/admin/trio-demo')
        assert board.status_code==200 and board.json()['analytics']['scans']>=1
        assert board.json()['requests'][0]['id']==rid
        assert owner.patch(f'/api/admin/trio-demo/requests/{rid}',json={'status':'in_progress'}).status_code==403
        assert owner.patch(f'/api/admin/trio-demo/requests/{rid}',json={'status':'in_progress'},headers=csrf).status_code==200
        assert guest.get('/api/guest/requests/'+str(rid),headers={'x-scene-ticket':ticket}).json()['status']=='in_progress'
        assert owner.patch(f'/api/admin/trio-demo/requests/{rid}',json={'status':'completed'},headers=csrf).status_code==200
        assert owner.patch(f'/api/admin/trio-demo/requests/{rid}',json={'status':'in_progress'},headers=csrf).status_code==409
        assert guest.get('/api/guest/requests/'+str(rid),headers={'x-scene-ticket':ticket}).json()['status']=='completed'


def test_tenant_isolation_invitations_permissions_and_qr_rotation():
    with TestClient(app) as a, TestClient(app) as b, TestClient(app) as staff:
        slug_a,headers_a=registration(a,'business-a@example.com','Company Alpha')
        slug_b,headers_b=registration(b,'business-b@example.com','Company Beta')
        assert a.get('/api/admin/'+slug_b).status_code==404
        assert b.get('/api/admin/'+slug_a).status_code==404
        board_a=a.get('/api/admin/'+slug_a).json()
        token=board_a['stations'][0]['token']
        station_id=board_a['stations'][0]['id']
        assert a.get('/api/q/'+token).status_code==200
        wrong=b.post(f'/api/admin/{slug_a}/stations/{station_id}/rotate',headers=headers_b)
        assert wrong.status_code==404
        rot=a.post(f'/api/admin/{slug_a}/stations/{station_id}/rotate',headers=headers_a)
        assert rot.status_code==200
        assert a.get('/api/q/'+token).status_code==404
        newtoken=a.get('/api/admin/'+slug_a).json()['stations'][0]['token']
        assert token!=newtoken
        assert a.get('/api/q/'+newtoken).status_code==200
        invitation=a.post(f'/api/admin/{slug_a}/invites',headers=headers_a,json={'role':'staff'})
        assert invitation.status_code==200
        from urllib.parse import parse_qs,urlsplit
        invtoken=parse_qs(urlsplit(invitation.json()['join_url']).query)['invite'][0]
        joined=staff.post('/api/auth/join',json={'token':invtoken,'email':'assistant@example.com','password':'StrongAssistantPass12!'})
        assert joined.status_code==200,joined.text
        assert staff.post('/api/auth/join',json={'token':invtoken,'email':'another@example.com','password':'AnotherStrongPass12!'}).status_code==410
        mem=staff.get('/api/me').json()
        assert mem['businesses'][0]['role']=='staff'
        team_board=staff.get('/api/admin/'+slug_a)
        assert team_board.status_code==200
        assert team_board.json()['role']=='staff'
        assert staff.get('/api/admin/'+slug_b).status_code==404
        csrf_staff={'x-scene-csrf':mem['csrf']}
        assert staff.post('/api/admin/'+slug_a+'/products',headers=csrf_staff,json={'name':'Not allowed','price_cents':500}).status_code==403
        assert staff.post('/api/admin/'+slug_a+'/stations',headers=csrf_staff,json={'label':'not allowed'}).status_code==403
        assert staff.post('/api/admin/'+slug_a+'/invites',headers=csrf_staff,json={'role':'manager'}).status_code==403
        assert staff.patch('/api/admin/'+slug_a+'/settings',headers=csrf_staff,json={'name':'X','accent':'#aabbcc'}).status_code==422
        guest=staff.post('/api/q/'+newtoken+'/requests',json={'kind':'service','client_key':'req-team-perms-2201010001'})
        assert guest.status_code==200
        rid=guest.json()['request_id']
        assert staff.patch(f'/api/admin/{slug_a}/requests/{rid}',headers=csrf_staff,json={'status':'completed'}).status_code==200
        assert b.patch(f'/api/admin/{slug_a}/requests/{rid}',headers=headers_b,json={'status':'completed'}).status_code==404
        assert a.get('/api/admin/'+slug_a).json()['analytics']['resolved']==1


def test_signup_login_logout_and_validation():
    with TestClient(app) as c:
        slug,headers=registration(c,'single-owner@example.com','Solo Studio')
        bad=c.patch(f'/api/admin/{slug}/settings',headers=headers,json={'name':'Solo Studio','tagline':'x','accent':'blue'})
        assert bad.status_code==400
        good=c.patch(f'/api/admin/{slug}/settings',headers=headers,json={'name':'Solo Studio','tagline':'Built for guests','accent':'#aabbcc'})
        assert good.status_code==200
        assert c.get('/api/admin/'+slug).json()['accent']=='#aabbcc'
        assert c.post('/api/auth/logout',headers=headers).status_code==200
        assert c.get('/api/admin/'+slug).status_code==401
        assert c.post('/api/auth/login',json={'email':'single-owner@example.com','password':'bad-password'}).status_code==401
        assert c.post('/api/auth/login',json={'email':'single-owner@example.com','password':'ExampleStrongPassword123!'}).status_code==200
        assert c.get('/api/admin/'+slug).status_code==200


@pytest.mark.parametrize('origin', ['https://testserver', 'http://evil.example', 'null', 'http://[broken'])
def test_cross_origin_auth_is_rejected(origin):
    with TestClient(app) as c:
        result=c.post('/api/auth/login',headers={'origin':origin},json={
            'email':'demo@scene.local','password':'SceneDemo2026!'})
        assert result.status_code==403
        assert 'scene_session' not in c.cookies


def test_same_origin_and_fetch_metadata():
    with TestClient(app) as c:
        body={'email':'demo@scene.local','password':'SceneDemo2026!'}
        assert c.post('/api/auth/login',headers={'sec-fetch-site':'cross-site'},json=body).status_code==403
        assert c.post('/api/auth/login',headers={'origin':'http://testserver:80'},json=body).status_code==200
        csrf=c.get('/api/me').json()['csrf']
        assert c.post('/api/auth/logout',headers={
            'origin':'https://testserver','x-scene-csrf':csrf}).status_code==403
        assert c.get('/api/me').status_code==200


def test_duplicate_key_does_not_expose_another_guests_status():
    with TestClient(app) as c:
        c.post('/api/auth/login',json={'email':'demo@scene.local','password':'SceneDemo2026!'})
        spots=c.get('/api/admin/trio-demo').json()['stations']
        token=spots[0]['token']
        body={'kind':'service','client_key':'private-dedup-regression-01'}
        created=c.post(f'/api/q/{token}/requests',json=body).json()
        for headers in ({}, {'x-scene-ticket':'wrong-receipt'}):
            denied=c.post(f'/api/q/{token}/requests',json=body,headers=headers)
            assert denied.status_code==409
            assert set(denied.json())=={'detail'}
        receipt={'x-scene-ticket':created['ticket']}
        assert c.post(f"/api/q/{spots[1]['token']}/requests",json=body,headers=receipt).status_code==409
        repeated=c.post(f'/api/q/{token}/requests',json=body,headers=receipt).json()
        assert repeated['request_id']==created['request_id']
        assert repeated['ticket']==created['ticket']
        assert repeated['already_sent'] is True


@pytest.mark.parametrize('slug', ['velvet-demo', 'apex-demo'])
def test_service_catalog_selections_validate_product_tenant(slug):
    with TestClient(app) as c:
        token=c.get('/api/demo/'+slug).json()['q']
        product=c.get('/api/q/'+token).json()['products'][0]['id']
        other_token=c.get('/api/demo/muse-demo').json()['q']
        other_product=c.get('/api/q/'+other_token).json()['products'][0]['id']
        body={'kind':'service','product_id':other_product,'client_key':'service-product-'+slug+'-001'}
        assert c.post(f'/api/q/{token}/requests',json=body).status_code==400
        body['product_id']=product
        response=c.post(f'/api/q/{token}/requests',json=body)
        assert response.status_code==200
        with db() as connection:
            row=connection.execute('SELECT product_id,message FROM requests WHERE id=?',
                                   (response.json()['request_id'],)).fetchone()
            assert row['product_id']==product
            assert row['message'].startswith('Interested in: ')


def test_private_cache_session_expiry_and_membership_revocation():
    with TestClient(app) as c:
        slug,headers=registration(c,'revocation@example.com','Revocation Studio')
        response=c.get('/api/me')
        assert response.headers['cache-control']=='no-store'
        token_hash=sha(c.cookies.get('scene_session'))
        with db() as connection:
            uid=connection.execute('SELECT user_id FROM sessions WHERE token_hash=?',(token_hash,)).fetchone()[0]
            connection.execute('DELETE FROM memberships WHERE user_id=?',(uid,))
        assert c.get('/api/admin/'+slug).status_code==404
        assert c.post(f'/api/admin/{slug}/stations',headers=headers,json={'label':'Denied station'}).status_code==404
        with db() as connection:
            connection.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?',(ts()-1,token_hash))
        assert c.get('/api/me').status_code==401


def test_cross_tenant_resource_ids_and_blank_names_are_rejected():
    with TestClient(app) as a, TestClient(app) as b:
        slug_a,headers_a=registration(a,'resource-a@example.com','Resource Alpha')
        slug_b,headers_b=registration(b,'resource-b@example.com','Resource Beta')
        product=b.post(f'/api/admin/{slug_b}/products',headers=headers_b,
                       json={'name':'Sample item','price_cents':100}).json()['id']
        station=b.get('/api/admin/'+slug_b).json()['stations'][0]
        assert a.delete(f'/api/admin/{slug_a}/products/{product}',headers=headers_a).status_code==404
        assert a.post(f"/api/admin/{slug_a}/stations/{station['id']}/rotate",headers=headers_a).status_code==404
        assert b.get('/api/admin/'+slug_b).json()['stations'][0]['token']==station['token']
        assert a.get(f'/api/admin/{slug_b}/members').status_code==404
        for path,method,body in [
            ('products','post',{'name':'   ','price_cents':0}),
            ('stations','post',{'label':'   '}),
            ('settings','patch',{'name':'   ','accent':'#aabbcc'}),
        ]:
            assert getattr(a,method)(f'/api/admin/{slug_a}/{path}',headers=headers_a,json=body).status_code==422


@pytest.mark.parametrize('route', ['login', 'join'])
def test_authentication_input_lengths_are_bounded(route):
    with TestClient(app) as c:
        body={'email':'a@example.com','password':'x'*129,'token':'x'*32}
        assert c.post('/api/auth/'+route,json=body).status_code==422


def test_owner_can_change_and_revoke_scoped_team_access():
    from urllib.parse import parse_qs, urlsplit
    with TestClient(app) as owner, TestClient(app) as teammate, TestClient(app) as other:
        slug, headers = registration(owner, 'team-owner@example.invalid', 'Team lifecycle')
        other_slug, other_headers = registration(other, 'team-other@example.invalid', 'Other lifecycle')
        invitation = owner.post(f'/api/admin/{slug}/invites', headers=headers, json={'role':'manager'}).json()
        token = parse_qs(urlsplit(invitation['join_url']).query)['invite'][0]
        assert teammate.post('/api/auth/join', json={'token':token,'email':'team-member@example.invalid','password':'SyntheticTeamPass123!'}).status_code == 200
        team_headers = {'x-scene-csrf':teammate.get('/api/me').json()['csrf']}
        members = owner.get(f'/api/admin/{slug}/members').json()['members']
        uid = next(m['id'] for m in members if m['role']=='manager')
        owner_id = next(m['id'] for m in members if m['role']=='owner')
        path = f'/api/admin/{slug}/members/{uid}'
        assert teammate.patch(path, headers=team_headers, json={'role':'staff'}).status_code == 403
        assert other.delete(path, headers=other_headers).status_code == 404
        assert owner.delete(f'/api/admin/{other_slug}/members/{uid}', headers=headers).status_code == 404
        assert owner.patch(path, json={'role':'staff'}).status_code == 403
        assert owner.patch(path, headers=headers, json={'role':'owner'}).status_code == 422
        for method in ('patch', 'delete'):
            kwargs = {'headers':headers}
            if method=='patch': kwargs['json']={'role':'staff'}
            assert getattr(owner,method)(f'/api/admin/{slug}/members/{owner_id}', **kwargs).status_code == 409
        assert owner.patch(path, headers=headers, json={'role':'staff'}).status_code == 200
        assert teammate.post(f'/api/admin/{slug}/products', headers=team_headers, json={'name':'Denied','price_cents':0}).status_code == 403
        assert owner.delete(path, headers=headers).status_code == 200
        assert teammate.get(f'/api/admin/{slug}').status_code == 404
        assert teammate.post(f'/api/admin/{slug}/stations', headers=team_headers, json={'label':'Denied'}).status_code == 404
        assert teammate.get('/api/me').json()['businesses'] == []
        assert owner.delete(path, headers=headers).status_code == 404


def test_analytics_cover_full_history_and_keep_old_open_requests_visible():
    with TestClient(app) as owner, TestClient(app) as other:
        slug, headers = registration(owner, 'analytics-owner@example.invalid', 'Analytics fixture')
        foreign_slug, _ = registration(other, 'analytics-other@example.invalid', 'Foreign analytics')
        board = owner.get('/api/admin/'+slug).json()
        bid, station = board['id'], board['stations'][0]['id']
        today = (ts()//86400)*86400
        with db() as c:
            for i in range(260):
                c.execute('INSERT INTO requests(business_id,station_id,kind,status,receipt_hash,client_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                          (bid,station,'service','open' if i==0 else 'completed','fixture-hash',f'analytics-fixture-{i}',today-86400*10 if i==0 else today,today))
            c.execute('INSERT INTO scans(station_id,business_id,created_at) VALUES(?,?,?)',(station,bid,today))
        board = owner.get('/api/admin/'+slug).json()
        assert len(board['requests']) == 250
        assert board['requests'][0]['status'] == 'open'
        analytics = board['analytics']
        assert analytics['total'] == 260
        assert analytics['request_kinds'] == {'service':260}
        assert analytics['open'] == 1
        assert analytics['stations'][0]['requests'] == 260
        assert analytics['stations'][0]['scans'] == 1
        assert len(analytics['daily']) == 7
        assert analytics['daily'][-1] == {'day':today,'requests':259,'scans':1}
        assert sum(day['requests'] for day in analytics['daily']) == 259
        assert other.get('/api/admin/'+slug).status_code == 404
        assert other.get('/api/admin/'+foreign_slug).json()['analytics']['total'] == 0


def test_guest_question_validation_and_contact_privacy():
    with TestClient(app) as owner, TestClient(app) as guest:
        slug, headers = registration(owner, 'contact-owner@example.invalid', 'Contact privacy')
        token = owner.get('/api/admin/'+slug).json()['stations'][0]['token']
        path = f'/api/q/{token}/requests'
        assert guest.post(path, json={'kind':'question','message':'   ','client_key':'empty-question-fixture-01'}).status_code == 400
        message = 'Synthetic inquiry · Name: Sample · Contact (reply consent): guest@example.invalid'
        result = guest.post(path, json={'kind':'question','message':message,'client_key':'contact-question-fixture-01'})
        assert result.status_code == 200
        receipt = result.json()
        assert 'guest@example.invalid' not in result.text
        assert 'guest@example.invalid' not in guest.get('/api/q/'+token).text
        status = guest.get(f"/api/guest/requests/{receipt['request_id']}", headers={'x-scene-ticket':receipt['ticket']})
        assert set(status.json()) == {'status','updated_at'}
        assert owner.get('/api/admin/'+slug).json()['requests'][0]['message'] == message
        assert guest.post(path, json={'kind':'question','message':'x'*401,'client_key':'long-question-fixture-01'}).status_code == 422
