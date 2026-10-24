"""Tenant-scoped organization, location, QR, customer and reporting APIs."""
import os
import secrets
from typing import Literal
from fastapi import Request, Query, Path
from pydantic import BaseModel, Field, field_validator


class CleanModel(BaseModel):
    @field_validator('name', 'address', 'title', 'message', 'contact', mode='before', check_fields=False)
    @classmethod
    def trim(cls, value): return value.strip() if isinstance(value, str) else value


class Organization(CleanModel):
    name: str = Field(min_length=2, max_length=80)
    industry: Literal['restaurant','barber','auto','retail']


class Location(CleanModel):
    name: str = Field(min_length=2, max_length=80)
    address: str = Field(default='', max_length=240)
    active: bool = Field(default=True, strict=True)


class QRSettings(CleanModel):
    location_id: str | None = Field(default=None, min_length=16, max_length=64)
    destination: Literal['menu','service','info'] = 'menu'
    title: str = Field(default='', max_length=100)
    message: str = Field(default='', max_length=500)


class Customer(CleanModel):
    name: str = Field(min_length=1, max_length=80)
    contact: str = Field(min_length=3, max_length=120)
    consent: bool = Field(strict=True)


def create_business(s, c, uid, name, industry):
    slug = s.slugify(name)
    if not slug: s.fail(400, 'Choose a business name')
    if c.execute('SELECT id FROM businesses WHERE slug=?', (slug,)).fetchone(): slug += '-' + secrets.token_hex(4)
    bid = c.execute('INSERT INTO businesses(owner_id,name,slug,industry,created_at) VALUES(?,?,?,?,?)',
                    (uid, name, slug, industry, s.ts())).lastrowid
    c.execute('INSERT INTO memberships VALUES(?,?,?)', (bid, uid, 'owner'))
    s.scope(c, 'scene.tenant_id', bid)
    c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)',
              (bid,'Front Desk','front-desk',secrets.token_urlsafe(32),s.ts()))
    s.audit(c, bid, uid, 'organization.created', bid)
    return {'id':bid, 'slug':slug}


def save_customer(s, c, bid, name, contact):
    cid = secrets.token_hex(16)
    c.execute('INSERT INTO customers VALUES(?,?,?,?,?,?,?)', (cid,bid,name,contact,s.ts(),s.ts(),s.ts()))
    return cid


def guest_scope(s, c, q, request):
    token = request.headers.get('x-scene-guest','')
    if not token and os.getenv('SCENE_REQUIRE_GUEST_SESSION','0') != '1': return
    if not 25 <= len(token) <= 100: s.fail(401, 'Start a guest session at this QR location')
    row = c.execute('SELECT station_id FROM guest_sessions WHERE token_hash=? AND business_id=? AND expires_at>?',
                    (s.sha(token),q['business_id'],s.ts())).fetchone()
    if not row or row['station_id'] != q['station_id']: s.fail(401, 'Guest session expired or belongs to another location')


def install(s):
    @s.app.get('/api/organizations')
    def organizations(request: Request):
        session = s.user_session(request)
        with s.db() as c:
            rows = c.execute('SELECT b.id,b.slug,b.name,b.industry,m.role FROM businesses b JOIN memberships m ON m.business_id=b.id WHERE m.user_id=? ORDER BY b.id', (session['user_id'],)).fetchall()
            return {'organizations':[dict(row) for row in rows]}

    @s.app.post('/api/organizations', status_code=201)
    def organization(body: Organization, request: Request):
        session = s.user_session(request, True); s.rate_limit(request, 'organization-create', 10, 3600)
        with s.db() as c:
            return create_business(s,c,session['user_id'],body.name,body.industry)

    @s.app.get('/api/businesses/{slug}')
    def public_business(slug: str, request: Request):
        s.rate_limit(request,'public-business',120,60)
        with s.db() as c:
            b = c.execute('SELECT id,name,slug,industry,accent,tagline FROM businesses WHERE slug=?',(slug,)).fetchone()
            if not b: s.fail(404, 'Business not found')
            s.scope(c,'scene.tenant_id',b['id'])
            result = {k:b[k] for k in ('name','slug','industry','accent','tagline')}
            result['locations'] = [dict(row) for row in c.execute('SELECT id,name,address FROM locations WHERE business_id=? AND active=1 ORDER BY id',(b['id'],))]
            result['products'] = [dict(row) for row in c.execute('SELECT id,name,description,category,price_cents FROM products WHERE business_id=? AND active=1 ORDER BY id',(b['id'],))]
            return result

    @s.app.get('/api/admin/{slug}/locations')
    def locations(slug: str, request: Request):
        session = s.user_session(request)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'])
            return {'locations':[dict(row) for row in c.execute('SELECT id,name,address,active,created_at FROM locations WHERE business_id=? ORDER BY id',(b['id'],))]}

    @s.app.post('/api/admin/{slug}/locations', status_code=201)
    def add_location(slug: str, body: Location, request: Request):
        session=s.user_session(request,True)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],s.EDIT_ROLES)
            lid=secrets.token_hex(16)
            c.execute('INSERT INTO locations VALUES(?,?,?,?,?,?)',(lid,b['id'],body.name,body.address,int(body.active),s.ts()))
            s.audit(c,b['id'],session['user_id'],'location.created',b['id'])
            return {'id':lid}

    @s.app.patch('/api/admin/{slug}/locations/{lid}')
    def edit_location(slug: str, lid: str, body: Location, request: Request):
        session=s.user_session(request,True)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],s.EDIT_ROLES)
            changed=c.execute('UPDATE locations SET name=?,address=?,active=? WHERE business_id=? AND id=?',(body.name,body.address,int(body.active),b['id'],lid))
            if not changed.rowcount: s.fail(404,'Location not found')
            s.audit(c,b['id'],session['user_id'],'location.updated',b['id'])
        return {'ok':True}

    @s.app.get('/api/admin/{slug}/qr')
    def qr_list(slug: str, request: Request):
        session=s.user_session(request)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'])
            return {'codes':[dict(row) for row in c.execute('SELECT id,label,code,token,active,location_id,destination,content_title,content_message FROM stations WHERE business_id=? ORDER BY id',(b['id'],))]}

    @s.app.patch('/api/admin/{slug}/qr/{sid}')
    def configure_qr(slug: str, body: QRSettings, request: Request, sid: int=Path(gt=0,le=9223372036854775807)):
        session=s.user_session(request,True)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],s.EDIT_ROLES)
            if body.location_id and not c.execute('SELECT 1 FROM locations WHERE business_id=? AND id=?',(b['id'],body.location_id)).fetchone(): s.fail(404,'Location not found')
            changed=c.execute('UPDATE stations SET location_id=?,destination=?,content_title=?,content_message=? WHERE business_id=? AND id=?',(body.location_id,body.destination,body.title,body.message,b['id'],sid))
            if not changed.rowcount: s.fail(404,'QR code not found')
            s.audit(c,b['id'],session['user_id'],'qr.configured',sid)
        return {'ok':True}

    @s.app.post('/api/q/{token}/session', status_code=201)
    def guest_session(token: str, request: Request):
        s.same_origin(request);s.rate_limit(request,'guest-session',30,60)
        with s.db() as c:
            q=s.resolve_q(c,token)
            value=secrets.token_urlsafe(40)
            c.execute('DELETE FROM guest_sessions WHERE business_id=? AND expires_at<=?',(q['business_id'],s.ts()))
            c.execute('INSERT INTO guest_sessions VALUES(?,?,?,?,?)',(s.sha(value),q['business_id'],q['station_id'],s.ts(),s.ts()+7200))
            return {'guest_token':value,'expires_in':7200,'location_id':q['location_id'],'station_id':q['station_id']}

    @s.app.get('/api/admin/{slug}/customers')
    def customers(slug: str, request: Request, before: str='', limit: int=Query(default=25,ge=1,le=100)):
        session=s.user_session(request)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],s.EDIT_ROLES)
            rows=c.execute('SELECT id,name,contact,consent_at,created_at,updated_at FROM customers WHERE business_id=? AND id>? ORDER BY id LIMIT ?', (b['id'],before,limit+1)).fetchall()
            more=len(rows)>limit;rows=rows[:limit]
            return {'customers':[dict(row) for row in rows], 'next':rows[-1]['id'] if more else None}

    @s.app.post('/api/admin/{slug}/customers',status_code=201)
    def add_customer(slug: str, body: Customer, request: Request):
        session=s.user_session(request,True)
        if not body.consent:s.fail(400,'Recorded customer consent is required')
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],s.EDIT_ROLES)
            cid=save_customer(s,c,b['id'],body.name,body.contact)
            s.audit(c,b['id'],session['user_id'],'customer.created',b['id'])
            return {'id':cid}

    @s.app.post('/api/admin/{slug}/customers/{cid}/redact')
    def redact_customer(slug: str,cid: str,request: Request):
        session=s.user_session(request,True)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],{'owner'})
            changed=c.execute("UPDATE customers SET name='[redacted]',contact='[redacted]',updated_at=? WHERE business_id=? AND id=?",(s.ts(),b['id'],cid))
            if not changed.rowcount:s.fail(404,'Customer not found')
            c.execute('UPDATE requests SET customer_name=NULL,customer_contact=NULL,reply_consent_at=NULL WHERE business_id=? AND customer_id=?',(b['id'],cid))
            s.audit(c,b['id'],session['user_id'],'customer.redacted',b['id'])
        return {'ok':True,'note':'Structured contact fields redacted; review free-text and backup retention separately.'}

    @s.app.get('/api/admin/{slug}/reports')
    def report(slug: str,request: Request, start: int=Query(default=0,ge=0,le=9223372036854775807),end: int=Query(default=9223372036854775807,ge=0,le=9223372036854775807)):
        session=s.user_session(request)
        if start>=end:s.fail(400,'Report start must precede end')
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],s.EDIT_ROLES)
            statuses=c.execute('SELECT status,count(*) AS count FROM requests WHERE business_id=? AND created_at>=? AND created_at<? GROUP BY status',(b['id'],start,end)).fetchall()
            scans=c.execute('SELECT count(*) AS count FROM scans WHERE business_id=? AND created_at>=? AND created_at<?',(b['id'],start,end)).fetchone()['count']
            return {'start':start,'end':end,'statuses':[dict(row) for row in statuses],'page_loads':scans,'note':'Requests and page loads do not establish orders, unique visitors or revenue.'}
