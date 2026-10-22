"""SCENE QR beta: multi-tenant, shared-state QR service app (FastAPI + SQLite).

Run one Uvicorn worker with a persistent SCENE_DB volume. Demo seed is *off* by default.
This is a pilot backend, not a substitute for hardened hosted PostgreSQL and billing.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import io
import os
import re
import secrets
import sqlite3
from storage import postgres_db, verify_postgres
from request_schema import upgrade_sqlite, PRIVATE_FIELDS
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlsplit

import qrcode
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('SCENE_DB', str(ROOT / 'scene.db')))
DATABASE_URL = os.getenv('SCENE_DATABASE_URL', '')
DEMO = os.getenv('SCENE_DEMO', '0') == '1'
SECURE_COOKIE = os.getenv('SCENE_SECURE_COOKIE', '0') == '1'
PUBLIC_URL = os.getenv('SCENE_PUBLIC_URL', '').rstrip('/')
INDUSTRIES = {'restaurant', 'barber', 'auto', 'retail'}
ALLOWED_KINDS = {
    'restaurant': {'service', 'water', 'check', 'order', 'question'},
    'barber': {'checkin', 'appointment', 'service', 'question'},
    'auto': {'estimate', 'dropoff', 'service', 'question'},
    'retail': {'assistance', 'size', 'checkout', 'question', 'order'},
}
ROLES = {'owner', 'manager', 'staff'}
EDIT_ROLES = {'owner', 'manager'}
DB_LOCK = threading.RLock()
RATE_LOCK = threading.Lock()
RATES: dict[str,list[float]] = {}
app = FastAPI(title='SCENE QR Live MVP', version='0.2.0', docs_url=None if not DEMO else '/docs')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

@contextmanager
def db():
    if DATABASE_URL:
        with postgres_db(DATABASE_URL) as c:
            yield c
        return
    with DB_LOCK:
        c = sqlite3.connect(DB_PATH, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA busy_timeout=15000')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

def ts(): return int(time.time())
def slugify(v: str): return re.sub('-+', '-', re.sub('[^a-z0-9]+', '-', v.lower())).strip('-')[:38]
def sha(v: str): return hashlib.sha256(v.encode()).hexdigest()
def password_hash(p: str, salt: bytes|None=None):
    salt = salt or os.urandom(16)
    key = hashlib.scrypt(p.encode(), salt=salt, n=16384, r=8, p=1)
    return f'{base64.b64encode(salt).decode()}:{base64.b64encode(key).decode()}'
def password_ok(p: str, stored: str):
    try:
        salt, key = stored.split(':', 1)
        return hmac.compare_digest(password_hash(p, base64.b64decode(salt)).split(':',1)[1], key)
    except (ValueError, TypeError): return False

def fail(status: int, message: str): raise HTTPException(status_code=status, detail=message)
def rate_limit(request: Request, operation: str, limit=25, window=60):
    ip = request.client.host if request.client else 'unknown'
    k = f'{operation}:{ip}'
    now = time.monotonic()
    with RATE_LOCK:
        active = [v for v in RATES.get(k, []) if now-v < window]
        if len(active) >= limit: fail(429, 'Too many requests. Try again shortly.')
        active.append(now); RATES[k] = active
        if len(RATES)>5000: RATES.clear()

def same_origin(request: Request):
    origin = request.headers.get('origin')
    if origin is not None:
        def origin_tuple(value):
            parsed = urlsplit(value)
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None
                    or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
                raise ValueError('Invalid origin')
            return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)
        try:
            matches = origin_tuple(origin) == origin_tuple(str(request.base_url))
        except ValueError:
            matches = False
        if not matches:
            fail(403, 'Cross-site requests are not allowed')
    elif request.headers.get('sec-fetch-site') == 'cross-site':
        fail(403, 'Cross-site requests are not allowed')

def init():
    if DATABASE_URL:
        if DEMO:
            raise RuntimeError('PostgreSQL requires SCENE_DEMO=0')
        verify_postgres(DATABASE_URL)
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS businesses(id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, industry TEXT NOT NULL, accent TEXT NOT NULL DEFAULT '#dba76b', tagline TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS memberships(business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,role TEXT NOT NULL CHECK(role IN ('owner','manager','staff')),PRIMARY KEY (business_id,user_id));
        CREATE TABLE IF NOT EXISTS stations(id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE, label TEXT NOT NULL, code TEXT NOT NULL, token TEXT UNIQUE NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, UNIQUE(business_id,code));
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT 'Featured', price_cents INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE, station_id INTEGER NOT NULL REFERENCES stations(id), kind TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', product_id INTEGER REFERENCES products(id), status TEXT NOT NULL DEFAULT 'open', receipt_hash TEXT NOT NULL, client_key TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, UNIQUE(business_id,client_key));
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS invites(token_hash TEXT PRIMARY KEY,business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,role TEXT NOT NULL,expires_at INTEGER NOT NULL,used_at INTEGER);
        CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY,station_id INTEGER NOT NULL REFERENCES stations(id),business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,created_at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_requests ON requests(business_id,status,created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sessions ON sessions(expires_at);
        CREATE INDEX IF NOT EXISTS idx_scans ON scans(business_id,created_at DESC);
        ''')
        upgrade_sqlite(c)
        if DEMO and c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0:
            c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)', ('demo@scene.local',password_hash('SceneDemo2026!'),ts()))
            uid = c.execute('SELECT id FROM users WHERE email=?',('demo@scene.local',)).fetchone()[0]
            fixtures = [
                ('TRIO Social Club','trio-demo','restaurant','#dba76b','A richer way to gather.', ['Table 01','Table 02','Table 03','Patio 04'], [('Truffle Fries','Parmesan · herb aioli','Small plates',1400),('House Burger','Double smash patty · secret sauce','Mains',2300),('Steak Frites','Peppercorn sauce · hand-cut fries','Mains',3600),('Golden Hour','Citrus · ginger · soda','Drinks',1200)]),
                ('VELVET Studio','velvet-demo','barber','#ba94e9','Your next look starts here.', ['Chair 01','Chair 02','Front Desk'], [('Signature Cut','Precision cut and finish','Services',3500),('Beard Sculpt','Lineup and hot towel','Services',2000)]),
                ('APEX Motor Studio','apex-demo','auto','#8cd6c1','Precision care, without the guesswork.', ['Bay 01','Reception'], [('Exterior Detail','Wash · decontamination · finish','Detailing',9000),('Interior Revival','Deep clean · conditioning','Detailing',14000)]),
                ('MUSE Supply','muse-demo','retail','#eec9a2','Find something unforgettable.', ['Entrance','Fitting Room'], [('Essential Jacket','Relaxed fit · brushed cotton','New Arrivals',12500),('Everyday Tote','Heavyweight canvas','Accessories',3200)])
            ]
            for name,slug,industry,accent,tagline,spots,items in fixtures:
                bid = c.execute('INSERT INTO businesses(owner_id,name,slug,industry,accent,tagline,created_at) VALUES(?,?,?,?,?,?,?)',(uid,name,slug,industry,accent,tagline,ts())).lastrowid
                c.execute('INSERT INTO memberships VALUES(?,?,?)',(bid,uid,'owner'))
                for spot in spots:
                    c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)',(bid,spot,slugify(spot),secrets.token_urlsafe(24),ts()))
                for n,desc,category,price in items:
                    c.execute('INSERT INTO products(business_id,name,description,category,price_cents) VALUES(?,?,?,?,?)',(bid,n,desc,category,price))

init()

class NamedInput(BaseModel):
    @field_validator('name', 'label', 'category', mode='before', check_fields=False)
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

class Signup(NamedInput):
    email: str = Field(min_length=5,max_length=200)
    password: str = Field(min_length=10,max_length=128)
    name: str = Field(min_length=2,max_length=80)
    industry: str = 'restaurant'
class Credentials(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=128)
class NewRequest(BaseModel):
    kind: str = Field(min_length=1,max_length=30)
    message: str = Field(default='',max_length=400)
    product_id: int|None = Field(default=None,gt=0,le=9223372036854775807,strict=True)
    quantity: int = Field(default=1,ge=1,le=99,strict=True)
    client_key: str = Field(min_length=20,max_length=100)
    customer_name: str = Field(default='',max_length=50)
    customer_contact: str = Field(default='',max_length=100)
    reply_consent: bool = Field(default=False,strict=True)
class ChangeStatus(BaseModel):
    status: Literal['in_progress','completed']
class LeadStatus(BaseModel):
    status: Literal['new','qualified','closed']

class Product(NamedInput):
    name: str = Field(min_length=1,max_length=90)
    description: str = Field(default='',max_length=250)
    category: str = Field(default='Featured',max_length=40)
    price_cents: int = Field(ge=0,le=10000000,strict=True)
class Spot(NamedInput):
    label: str = Field(min_length=2,max_length=70)
class StationSettings(Spot):
    active: bool = Field(strict=True)

class Settings(NamedInput):
    name: str = Field(min_length=2,max_length=80)
    tagline: str = Field(default='',max_length=120)
    accent: str
class InviteRequest(BaseModel):
    role: Literal['staff','manager'] = 'staff'
class MemberRole(BaseModel):
    role: Literal['staff','manager']
class Join(Credentials):
    token: str = Field(min_length=20, max_length=100)

def user_session(request: Request, mutate=False):
    token = request.cookies.get('scene_session','')
    if not token: fail(401,'Sign in to continue')
    with db() as c:
        session = c.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?',(sha(token),ts())).fetchone()
        if session is None: fail(401,'Please sign in again')
        if mutate:
            same_origin(request)
            if not hmac.compare_digest(request.headers.get('x-scene-csrf',''),session['csrf']):
                fail(403,'Invalid session token')
        return session

def scope(c, name, value):
    if hasattr(c, "scope"):
        c.scope(name, value)

def grant(c, slug, uid, roles=None):
    row = c.execute('''SELECT b.*,m.role FROM businesses b JOIN memberships m ON m.business_id=b.id WHERE b.slug=? AND m.user_id=?''',(slug,uid)).fetchone()
    if row is None: fail(404,'Business not found')
    if roles and row['role'] not in roles: fail(403,'Insufficient permissions')
    scope(c, 'scene.tenant_id', row['id'])
    return row

def signin(response, uid):
    session = secrets.token_urlsafe(40)
    csrf = secrets.token_urlsafe(24)
    with db() as c:
        c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(sha(session),uid,csrf,ts()+604800))
    response.set_cookie('scene_session',session,max_age=604800,secure=SECURE_COOKIE,httponly=True,samesite='lax',path='/')

def public_bundle(c, b, spot):
    return {'name':b['name'],'slug':b['slug'],'industry':b['industry'],'accent':b['accent'],'tagline':b['tagline'],
            'stations':[{'label':spot['label'],'code':spot['code']}],
            'products':[dict(p) for p in c.execute('SELECT id,name,description,category,price_cents,active FROM products WHERE business_id=? AND active=1 ORDER BY id',(b['id'],))]}

def resolve_q(c, token):
    row=c.execute('''SELECT s.id station_id,s.label,s.code,s.business_id,b.id,b.name,b.slug,b.industry,b.accent,b.tagline FROM stations s JOIN businesses b ON b.id=s.business_id WHERE s.token=? AND s.active=1''',(token,)).fetchone()
    if not row: fail(404,'QR location is unavailable')
    scope(c, 'scene.tenant_id', row['business_id'])
    return row

@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
async def index(): return FileResponse(ROOT/'static'/'index.html')

@app.get('/q/{token}')
async def q_redirect(token:str):
    with db() as c: resolve_q(c,token)
    return RedirectResponse(url='/?q='+quote(token,safe=''),status_code=302)

@app.post('/api/auth/signup')
async def signup(body: Signup, request: Request):
    same_origin(request);rate_limit(request,'signup',7,3600)
    if body.industry not in INDUSTRIES: fail(400,'Unsupported industry')
    email=body.email.lower().strip();slug=slugify(body.name)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not slug: fail(400,'Invalid email or business name')
    with db() as c:
        if c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone(): fail(409,'Email is already registered')
        if c.execute('SELECT id FROM businesses WHERE slug=?',(slug,)).fetchone(): slug += '-'+secrets.token_hex(3)
        uid=c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)',(email,password_hash(body.password),ts())).lastrowid
        bid=c.execute('INSERT INTO businesses(owner_id,name,slug,industry,created_at) VALUES(?,?,?,?,?)',(uid,body.name.strip(),slug,body.industry,ts())).lastrowid
        c.execute('INSERT INTO memberships VALUES(?,?,?)',(bid,uid,'owner'))
        spots = ['Table 01','Table 02','Table 03'] if body.industry=='restaurant' else ['Front Desk','Station 01']
        for label in spots:
            c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)',(bid,label,slugify(label),secrets.token_urlsafe(24),ts()))
    response=JSONResponse({'ok':True,'slug':slug});signin(response,uid);return response

@app.post('/api/auth/login')
async def login(body: Credentials, request: Request):
    same_origin(request);rate_limit(request,'login',12,300)
    with db() as c:
        row=c.execute('SELECT id,password FROM users WHERE email=?',(body.email.lower().strip(),)).fetchone()
        if not row or not password_ok(body.password,row['password']): fail(401,'Incorrect email or password')
        uid=row['id']
    response=JSONResponse({'ok':True});signin(response,uid);return response

@app.post('/api/auth/join')
async def join(body: Join, request: Request):
    same_origin(request);rate_limit(request,'join',10,3600)
    email=body.email.lower().strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(body.password)<10: fail(400,'Enter a valid email and password')
    with db() as c:
        invitation=c.execute('SELECT * FROM invites WHERE token_hash=? AND used_at IS NULL AND expires_at>?',(sha(body.token),ts())).fetchone()
        if not invitation: fail(410,'Invitation expired or already used')
        user=c.execute('SELECT id,password FROM users WHERE email=?',(email,)).fetchone()
        if user:
            if not password_ok(body.password,user['password']): fail(401,'Incorrect account password')
            uid=user['id']
        else:
            uid=c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)',(email,password_hash(body.password),ts())).lastrowid
        if c.execute('SELECT 1 FROM memberships WHERE business_id=? AND user_id=?',(invitation['business_id'],uid)).fetchone(): fail(409,'Already on this business team')
        c.execute('INSERT INTO memberships VALUES(?,?,?)',(invitation['business_id'],uid,invitation['role']))
        c.execute('UPDATE invites SET used_at=? WHERE token_hash=? AND used_at IS NULL',(ts(),sha(body.token)))
    response=JSONResponse({'ok':True});signin(response,uid);return response

@app.post('/api/auth/logout')
async def logout(request: Request):
    s=user_session(request,True)
    with db() as c: c.execute('DELETE FROM sessions WHERE token_hash=?',(s['token_hash'],))
    response=JSONResponse({'ok':True});response.delete_cookie('scene_session',path='/');return response

@app.get('/api/me')
async def me(request: Request):
    s=user_session(request)
    with db() as c:
        u=c.execute('SELECT email FROM users WHERE id=?',(s['user_id'],)).fetchone()
        b=c.execute('''SELECT b.slug,b.name,b.industry,b.accent,m.role FROM businesses b JOIN memberships m ON m.business_id=b.id WHERE m.user_id=? ORDER BY b.id''',(s['user_id'],)).fetchall()
        return {'email':u['email'],'csrf':s['csrf'],'businesses':[dict(v) for v in b]}

@app.get('/api/demo/{slug}')
async def demo_entry(slug: str):
    if not DEMO or slug not in ('trio-demo','velvet-demo','apex-demo','muse-demo'): fail(404,'Demo unavailable')
    with db() as c:
        r=c.execute('''SELECT s.token FROM stations s JOIN businesses b ON b.id=s.business_id WHERE b.slug=? AND s.active=1 ORDER BY s.id LIMIT 1''',(slug,)).fetchone()
        if not r: fail(404,'Demo unavailable')
        return {'q':r['token']}

@app.get('/api/q/{token}')
async def scanned_q(token: str, request: Request):
    rate_limit(request,'scan',120,60)
    with db() as c:
        q=resolve_q(c,token)
        b=c.execute('SELECT * FROM businesses WHERE id=?',(q['business_id'],)).fetchone()
        c.execute('INSERT INTO scans(station_id,business_id,created_at) VALUES(?,?,?)',(q['station_id'],q['business_id'],ts()))
        spot={'label':q['label'],'code':q['code']}
        return public_bundle(c,b,spot)

@app.post('/api/q/{token}/requests')
async def guest_request(token: str, body: NewRequest, request: Request):
    same_origin(request);rate_limit(request,'submit:'+token[:12],12,60)
    with db() as c:
        q=resolve_q(c,token)
        if body.customer_contact.strip() and not body.reply_consent: fail(400,'Reply consent is required for contact details')
        if body.kind != 'question' and (body.customer_name.strip() or body.customer_contact.strip() or body.reply_consent): fail(400,'Contact details belong on inquiries')
        if body.kind not in ALLOWED_KINDS[q['industry']]: fail(400,'Request not supported here')
        prior=c.execute('SELECT id,station_id,receipt_hash,status FROM requests WHERE business_id=? AND client_key=?',(q['business_id'],body.client_key)).fetchone()
        if prior:
            ticket=request.headers.get('x-scene-ticket','')
            if prior['station_id'] != q['station_id'] or not hmac.compare_digest(sha(ticket),prior['receipt_hash']):
                fail(409,'Request key already used. Use your private receipt to check its status.')
            return {'ok':True,'request_id':prior['id'],'ticket':ticket,'status':prior['status'],'already_sent':True,'note':'Request already received.'}
        item=None
        if body.kind=='order' or body.product_id is not None:
            item=c.execute('SELECT id,name,price_cents FROM products WHERE business_id=? AND id=? AND active=1',(q['business_id'],body.product_id)).fetchone()
            if not item: fail(400,'Select a valid item')
        message=body.message.strip()
        if body.kind=='question' and not message: fail(400,'Enter a message for the team')
        if not item and body.quantity!=1: fail(400,'Quantities require a catalog item')
        if item: message='Interested in: '+item['name']+(' · '+message if message else '')
        if item and body.quantity!=1: message+=f' · Quantity {body.quantity}'
        receipt=secrets.token_urlsafe(32)
        rid=c.execute('''INSERT INTO requests(business_id,station_id,kind,message,product_id,receipt_hash,client_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)''',(q['business_id'],q['station_id'],body.kind,message,item['id'] if item else None,sha(receipt),body.client_key,ts(),ts())).lastrowid
        c.execute('UPDATE requests SET quantity=?,product_name=?,unit_price_cents=?,customer_name=?,customer_contact=?,reply_consent_at=?,lead_status=? WHERE id=? AND business_id=?', (body.quantity if item else None,item['name'] if item else None,item['price_cents'] if item else None,body.customer_name.strip() or None,body.customer_contact.strip() or None,ts() if body.reply_consent and body.customer_contact.strip() else None,'new' if body.kind=='question' else None,rid,q['business_id']))
        return {'ok':True,'request_id':rid,'ticket':receipt,'status':'open','note':'Staff received your service request. This is not a paid order or confirmed booking.'}

@app.get('/api/guest/requests/{rid}')
async def guest_status(rid:int,request:Request):
    ticket=request.headers.get('x-scene-ticket','')
    if len(ticket)<25: fail(401,'Request receipt required')
    with db() as c:
        scope(c, 'scene.receipt_hash', sha(ticket))
        row=c.execute('SELECT status,receipt_hash,updated_at FROM requests WHERE id=?',(rid,)).fetchone()
        if row is None or not hmac.compare_digest(sha(ticket),row['receipt_hash']): fail(404,'Request not found')
        return {'status':row['status'],'updated_at':row['updated_at']}

@app.get('/api/admin/{slug}')
async def admin(slug:str,request:Request):
    user=user_session(request)
    with db() as c:
        b=grant(c,slug,user['user_id'])
        spots=[dict(v) for v in c.execute('SELECT id,label,code,token,active FROM stations WHERE business_id=? ORDER BY id',(b['id'],))]
        products=[dict(v) for v in c.execute('SELECT id,name,description,category,price_cents,active FROM products WHERE business_id=? AND active=1 ORDER BY id',(b['id'],))]
        reqs=[dict(v) for v in c.execute('''SELECT r.id,r.kind,r.message,r.status,r.created_at,r.updated_at'''+PRIVATE_FIELDS+''',s.label AS station FROM requests r JOIN stations s ON s.id=r.station_id WHERE r.business_id=? ORDER BY CASE WHEN r.status='completed' THEN 1 ELSE 0 END,r.id DESC LIMIT 250''',(b['id'],))]
        counts=c.execute('''SELECT count(*) total,sum(CASE WHEN status='open' THEN 1 ELSE 0 END) open,sum(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed FROM requests WHERE business_id=?''',(b['id'],)).fetchone()
        kinds={r['kind']:r['total'] for r in c.execute('SELECT kind,count(*) total FROM requests WHERE business_id=? GROUP BY kind',(b['id'],))}
        lead_stages={'new':0,'qualified':0,'closed':0,'unreviewed':0}
        for row in c.execute("SELECT COALESCE(lead_status,'unreviewed') AS stage,count(*) AS total FROM requests WHERE business_id=? AND kind='question' GROUP BY lead_status",(b['id'],)):
            lead_stages[row['stage']]=row['total']
        selections=dict(c.execute("""SELECT count(*) AS requests,
            COALESCE(sum(quantity),0) AS units,
            COALESCE(sum(CASE WHEN unit_price_cents=0 THEN 1 ELSE 0 END),0) AS quote_requests,
            COALESCE(sum(CASE WHEN quantity IS NULL THEN 1 ELSE 0 END),0) AS unknown_quantity_requests
            FROM requests WHERE business_id=? AND product_id IS NOT NULL""",(b['id'],)).fetchone())
        station_scans={r['station_id']:r['total'] for r in c.execute('SELECT station_id,count(*) total FROM scans WHERE business_id=? GROUP BY station_id',(b['id'],))}
        station_requests={r['station_id']:r['total'] for r in c.execute('SELECT station_id,count(*) total FROM requests WHERE business_id=? GROUP BY station_id',(b['id'],))}
        today=ts()//86400
        daily_scans={r['day_bucket']:r['total'] for r in c.execute('SELECT created_at/86400 AS day_bucket,count(*) total FROM scans WHERE business_id=? AND created_at>=? GROUP BY created_at/86400',(b['id'],(today-6)*86400))}
        daily_requests={r['day_bucket']:r['total'] for r in c.execute('SELECT created_at/86400 AS day_bucket,count(*) total FROM requests WHERE business_id=? AND created_at>=? GROUP BY created_at/86400',(b['id'],(today-6)*86400))}
        activity=[{'day':day*86400,'scans':daily_scans.get(day,0),'requests':daily_requests.get(day,0)} for day in range(today-6,today+1)]
        station_activity=[{'label':spot['label'],'scans':station_scans.get(spot['id'],0),'requests':station_requests.get(spot['id'],0)} for spot in spots]
        return {'id':b['id'],'name':b['name'],'slug':b['slug'],'industry':b['industry'],'accent':b['accent'],'tagline':b['tagline'],'role':b['role'],
          'stations':spots,'products':products,'requests':reqs,
          'analytics':{'total':counts['total'],'open':counts['open'] or 0,'resolved':counts['completed'] or 0,'scans':sum(station_scans.values()),'request_kinds':kinds,'lead_stages':lead_stages,'catalog_requests':selections,'stations':station_activity,'daily':activity}}

@app.get('/api/admin/{slug}/requests')
async def request_history(slug:str,request:Request,
                          status:Literal['all','open','in_progress','completed']='all',
                          lead_status:Literal['','new','qualified','closed','unreviewed']='',
                          kind:str=Query(default='',max_length=30),
                          search:str=Query(default='',max_length=100),
                          station_id:int|None=Query(default=None,gt=0,le=9223372036854775807),
                          before:int|None=Query(default=None,gt=0,le=9223372036854775807),
                          limit:int=Query(default=25,ge=1,le=100)):
    s=user_session(request)
    with db() as c:
        b=grant(c,slug,s['user_id'])
        clauses=['r.business_id=?']; values=[b['id']]
        if lead_status:
            clauses.append("r.kind='question'")
            if lead_status == 'unreviewed':
                clauses.append('r.lead_status IS NULL')
            else:
                clauses.append('r.lead_status=?');values.append(lead_status)
        if kind:
            if kind not in ALLOWED_KINDS[b['industry']]: fail(400,'Unsupported request type')
            clauses.append('r.kind=?');values.append(kind)
        if station_id is not None:
            if not c.execute('SELECT id FROM stations WHERE id=? AND business_id=?',(station_id,b['id'])).fetchone():
                fail(404,'Location not found')
            clauses.append('r.station_id=?');values.append(station_id)
        if search.strip():
            literal=search.strip().lower().replace('!','!!').replace('%','!%').replace('_','!_')
            clauses.append("(LOWER(r.message) LIKE ? ESCAPE '!' OR LOWER(s.label) LIKE ? ESCAPE '!' OR LOWER(COALESCE(r.customer_name,'')) LIKE ? ESCAPE '!' OR LOWER(COALESCE(r.customer_contact,'')) LIKE ? ESCAPE '!')")
            values.extend(['%'+literal+'%']*4)
        source=' FROM requests r JOIN stations s ON s.id=r.station_id WHERE '+' AND '.join(clauses)
        counts={'all':0,'open':0,'in_progress':0,'completed':0}
        for row in c.execute('SELECT r.status,count(*) total'+source+' GROUP BY r.status',tuple(values)):
            counts[row['status']]=row['total'];counts['all']+=row['total']
        total=counts[status]
        if status!='all': source+=' AND r.status=?';values.append(status)
        if before is not None: source+=' AND r.id<?';values.append(before)
        rows=[dict(r) for r in c.execute('SELECT r.id,r.kind,r.message,r.status,r.created_at,r.updated_at'+PRIVATE_FIELDS+',s.label AS station'+source+' ORDER BY r.id DESC LIMIT ?',tuple(values+[limit+1]))]
        more=len(rows)>limit;rows=rows[:limit]
        return {'requests':rows,'total':total,'status_counts':counts,'has_more':more,
                'next_before':rows[-1]['id'] if more else None}


@app.patch('/api/admin/{slug}/requests/{rid}/lead')
async def update_lead(slug:str,rid:int,body:LeadStatus,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        row=c.execute('SELECT kind FROM requests WHERE id=? AND business_id=?',(rid,b['id'])).fetchone()
        if not row: fail(404,'Request not found')
        if row['kind']!='question': fail(400,'Only inquiries have lead stages')
        c.execute('UPDATE requests SET lead_status=?,updated_at=? WHERE id=? AND business_id=?',(body.status,ts(),rid,b['id']))
    return {'ok':True}

@app.patch('/api/admin/{slug}/requests/{rid}')
async def update_request(slug:str,rid:int,body:ChangeStatus,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'])
        current=c.execute('SELECT status FROM requests WHERE id=? AND business_id=?',(rid,b['id'])).fetchone()
        if not current: fail(404,'Request not found')
        allowed={'open':{'in_progress','completed'},'in_progress':{'completed'},'completed':set()}
        if body.status not in allowed[current['status']]: fail(409,'Request already handled or invalid status transition')
        changed=c.execute('UPDATE requests SET status=?,updated_at=? WHERE id=? AND business_id=? AND status=?',(body.status,ts(),rid,b['id'],current['status']))
        if not changed.rowcount: fail(409,'Request changed. Refresh before updating it again.')
        return {'ok':True,'status':body.status}

@app.post('/api/admin/{slug}/products')
async def add_product(slug:str,body:Product,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        rid=c.execute('INSERT INTO products(business_id,name,description,category,price_cents) VALUES(?,?,?,?,?)',(b['id'],body.name.strip(),body.description.strip(),body.category.strip() or 'Featured',body.price_cents)).lastrowid
        return {'ok':True,'id':rid}

@app.patch('/api/admin/{slug}/products/{pid}')
async def edit_product(slug:str,pid:int,body:Product,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        changed=c.execute('UPDATE products SET name=?,description=?,category=?,price_cents=? WHERE id=? AND business_id=? AND active=1',
                          (body.name.strip(),body.description.strip(),body.category.strip() or 'Featured',body.price_cents,pid,b['id']))
        if not changed.rowcount: fail(404,'Published item not found')
    return {'ok':True}

@app.delete('/api/admin/{slug}/products/{pid}')
async def remove_product(slug:str,pid:int,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        if not c.execute('UPDATE products SET active=0 WHERE id=? AND business_id=?',(pid,b['id'])).rowcount: fail(404,'Item not found')
        return {'ok':True}

@app.post('/api/admin/{slug}/stations')
async def create_station(slug:str,body:Spot,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        code=slugify(body.label)
        if not code: fail(400,'Choose a valid station name')
        if c.execute('SELECT id FROM stations WHERE business_id=? AND code=?',(b['id'],code)).fetchone(): fail(409,'Location already exists')
        rid=c.execute('INSERT INTO stations(business_id,label,code,token,created_at) VALUES(?,?,?,?,?)',(b['id'],body.label.strip(),code,secrets.token_urlsafe(24),ts())).lastrowid
        return {'ok':True,'id':rid}

@app.patch('/api/admin/{slug}/stations/{spot_id}')
async def edit_station(slug:str,spot_id:int,body:StationSettings,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        changed=c.execute('UPDATE stations SET label=?,active=? WHERE id=? AND business_id=?',
                          (body.label,int(body.active),spot_id,b['id']))
        if not changed.rowcount: fail(404,'Location not found')
    return {'ok':True}

@app.post('/api/admin/{slug}/stations/{spot_id}/rotate')
async def rotate_station(slug:str,spot_id:int,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        if not c.execute('UPDATE stations SET token=? WHERE id=? AND business_id=?',(secrets.token_urlsafe(24),spot_id,b['id'])).rowcount: fail(404,'Location not found')
        return {'ok':True,'note':'Old QR links have been revoked. Print new codes.'}

@app.patch('/api/admin/{slug}/settings')
async def settings(slug:str,body:Settings,request:Request):
    s=user_session(request,True)
    if not re.fullmatch('#[a-fA-F0-9]{6}',body.accent): fail(400,'Use a six-digit hex color')
    with db() as c:
        b=grant(c,slug,s['user_id'],EDIT_ROLES)
        c.execute('UPDATE businesses SET name=?,tagline=?,accent=? WHERE id=?',(body.name.strip(),body.tagline.strip(),body.accent,b['id']))
        return {'ok':True}

@app.post('/api/admin/{slug}/invites')
async def create_invite(slug:str,body:InviteRequest,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],{'owner'})
        token=secrets.token_urlsafe(32)
        c.execute('INSERT INTO invites(token_hash,business_id,role,expires_at) VALUES(?,?,?,?)',(sha(token),b['id'],body.role,ts()+86400))
        origin=PUBLIC_URL or str(request.base_url).rstrip('/')
        return {'ok':True,'join_url':origin+'/?invite='+quote(token,safe=''),'expires_in_hours':24}

@app.get('/api/admin/{slug}/members')
async def members(slug:str,request:Request):
    s=user_session(request)
    with db() as c:
        b=grant(c,slug,s['user_id'],{'owner'})
        rows=c.execute('''SELECT u.id,u.email,m.role FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.business_id=? ORDER BY m.role,u.email''',(b['id'],)).fetchall()
        return {'members':[dict(r) for r in rows]}

@app.get('/api/admin/{slug}/invites')
async def pending_invites(slug:str,request:Request):
    s=user_session(request)
    with db() as c:
        b=grant(c,slug,s['user_id'],{'owner'})
        rows=c.execute('SELECT token_hash AS id,role,expires_at FROM invites WHERE business_id=? AND used_at IS NULL AND expires_at>? ORDER BY expires_at,token_hash',(b['id'],ts())).fetchall()
        return {'invites':[dict(r) for r in rows]}

@app.post('/api/admin/{slug}/invites/{invite_id}/revoke')
async def revoke_invite(slug:str,invite_id:str,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],{'owner'})
        if not re.fullmatch('[a-f0-9]{64}',invite_id): fail(404,'Invitation not found')
        changed=c.execute('UPDATE invites SET expires_at=? WHERE token_hash=? AND business_id=? AND used_at IS NULL AND expires_at>?',(ts(),invite_id,b['id'],ts()))
        if not changed.rowcount: fail(404,'Active invitation not found')
        return {'ok':True}

@app.patch('/api/admin/{slug}/members/{uid}')
async def change_member(slug:str,uid:int,body:MemberRole,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],{'owner'})
        target=c.execute('SELECT role FROM memberships WHERE business_id=? AND user_id=?',(b['id'],uid)).fetchone()
        if not target: fail(404,'Member not found')
        if target['role']=='owner': fail(409,'Owner access cannot be changed here')
        c.execute('UPDATE memberships SET role=? WHERE business_id=? AND user_id=?',(body.role,b['id'],uid))
        return {'ok':True}

@app.delete('/api/admin/{slug}/members/{uid}')
async def revoke_member(slug:str,uid:int,request:Request):
    s=user_session(request,True)
    with db() as c:
        b=grant(c,slug,s['user_id'],{'owner'})
        target=c.execute('SELECT role FROM memberships WHERE business_id=? AND user_id=?',(b['id'],uid)).fetchone()
        if not target: fail(404,'Member not found')
        if target['role']=='owner': fail(409,'Owner access cannot be removed here')
        c.execute('DELETE FROM memberships WHERE business_id=? AND user_id=?',(b['id'],uid))
        return {'ok':True}

@app.get('/api/qr/{token}.png')
async def qr_png(token:str,request:Request):
    # Important: keep *.png handler before QR data handler in actual FastAPI route order.
    with db() as c: resolve_q(c,token)
    url=(PUBLIC_URL or str(request.base_url).rstrip('/'))+'/q/'+quote(token,safe='')
    qr=qrcode.QRCode(box_size=10,border=4,error_correction=qrcode.constants.ERROR_CORRECT_Q)
    qr.add_data(url);qr.make(fit=True)
    output=io.BytesIO();qr.make_image(fill_color='black',back_color='white').save(output,format='PNG');output.seek(0)
    return StreamingResponse(output,media_type='image/png',headers={'Cache-Control':'no-store'})

@app.get('/healthz')
async def healthz(): return {'ok':True,'mode':'demo' if DEMO else 'pilot'}
