"""Additive, tenant-scoped customer workflow API. No external messages are sent."""
import json
import hmac
from typing import Literal
from urllib.parse import urlsplit
from fastapi import Request, Query
from pydantic import BaseModel, Field, field_validator

STAGES = ('new', 'contacted', 'quoted', 'booked', 'won', 'lost', 'archived')
STAGE_SQL = "COALESCE(g.stage,CASE WHEN r.lead_status='closed' THEN 'archived' WHEN r.lead_status='qualified' THEN 'contacted' ELSE 'new' END)"
DDL = (
    '''CREATE TABLE IF NOT EXISTS growth_settings(business_id BIGINT PRIMARY KEY REFERENCES businesses(id),
       profile TEXT NOT NULL DEFAULT 'general', review_url TEXT NOT NULL DEFAULT '', booking_url TEXT NOT NULL DEFAULT '',
       setup_complete BIGINT NOT NULL DEFAULT 0, updated_at BIGINT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS growth_jobs(request_id BIGINT PRIMARY KEY, business_id BIGINT NOT NULL REFERENCES businesses(id),
       stage TEXT NOT NULL CHECK(stage IN ('new','contacted','quoted','booked','won','lost','archived')),
       quote_cents BIGINT, quote_description TEXT NOT NULL DEFAULT '', quote_expires BIGINT,
       quote_revision BIGINT NOT NULL DEFAULT 0, accepted_revision BIGINT,
       appointment_at BIGINT, followup_at BIGINT, revenue_cents BIGINT,
       note TEXT NOT NULL DEFAULT '', revision BIGINT NOT NULL DEFAULT 1, updated_at BIGINT NOT NULL,
       FOREIGN KEY(business_id,request_id) REFERENCES requests(business_id,id))''',
)


def upgrade_sqlite(c):
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_request_growth_tenant ON requests(business_id,id)')
    for sql in DDL: c.execute(sql)
    c.execute('CREATE INDEX IF NOT EXISTS idx_growth_followup ON growth_jobs(business_id,followup_at)')


class Config(BaseModel):
    profile: Literal['general','tint','detailing','restaurant','barber','retail'] = 'general'
    review_url: str = Field(default='',max_length=500)
    booking_url: str = Field(default='',max_length=500)
    setup_complete: bool = Field(default=False,strict=True)

    @field_validator('review_url','booking_url')
    @classmethod
    def safe_url(cls,value):
        value=value.strip()
        if value:
            u=urlsplit(value)
            if u.scheme!='https' or not u.hostname or u.username or u.password: raise ValueError('Use an HTTPS URL without credentials')
        return value


class Job(BaseModel):
    revision: int = Field(ge=0,strict=True)
    stage: Literal['new','contacted','quoted','booked','won','lost','archived']
    quote_cents: int|None = Field(default=None,ge=0,le=100000000,strict=True)
    quote_description: str = Field(default='',max_length=500)
    quote_expires: int|None = Field(default=None,ge=1,le=4102444800,strict=True)
    appointment_at: int|None = Field(default=None,ge=1,le=4102444800,strict=True)
    followup_at: int|None = Field(default=None,ge=1,le=4102444800,strict=True)
    revenue_cents: int|None = Field(default=None,ge=0,le=100000000,strict=True)
    note: str = Field(default='',max_length=1000)


class Decision(BaseModel):
    quote_revision: int = Field(ge=1,strict=True)
    decision: Literal['accept','decline']


def config(c,bid):
    row=c.execute('SELECT profile,review_url,booking_url,setup_complete FROM growth_settings WHERE business_id=?',(bid,)).fetchone()
    return dict(row) if row else dict(profile='general',review_url='',booking_url='',setup_complete=0)


def install(s):
    def authorize(c,slug,user):
        b=s.grant(c,slug,user['user_id'],s.EDIT_ROLES)
        return user,b

    @s.app.get('/api/admin/{slug}/growth')
    def dashboard(slug:str,request:Request):
        user=s.user_session(request)
        with s.db() as c:
            _,b=authorize(c,slug,user)
            source=' FROM requests r LEFT JOIN growth_jobs g ON g.request_id=r.id AND g.business_id=r.business_id WHERE r.business_id=? AND r.kind=\'question\''
            stages={k:0 for k in STAGES}
            for row in c.execute('SELECT '+STAGE_SQL+' stage,count(*) total'+source+' GROUP BY '+STAGE_SQL,(b['id'],)): stages[row['stage']]=row['total']
            due=c.execute("SELECT count(*) total FROM growth_jobs WHERE business_id=? AND followup_at<=? AND stage NOT IN ('won','lost','archived')",(b['id'],s.ts())).fetchone()['total']
            placements=[dict(r) for r in c.execute('''SELECT t.id,t.label,t.active,
                (SELECT count(*) FROM scans z WHERE z.business_id=t.business_id AND z.station_id=t.id) scans,
                (SELECT count(*) FROM requests z WHERE z.business_id=t.business_id AND z.station_id=t.id AND z.kind='question') inquiries,
                (SELECT count(*) FROM growth_jobs j JOIN requests z ON z.id=j.request_id AND z.business_id=j.business_id WHERE j.business_id=t.business_id AND z.station_id=t.id AND j.stage='won') won,
                (SELECT COALESCE(sum(j.revenue_cents),0) FROM growth_jobs j JOIN requests z ON z.id=j.request_id AND z.business_id=j.business_id WHERE j.business_id=t.business_id AND z.station_id=t.id AND j.stage='won') revenue_cents,
                (SELECT count(*) FROM growth_jobs j JOIN requests z ON z.id=j.request_id AND z.business_id=j.business_id WHERE j.business_id=t.business_id AND z.station_id=t.id AND j.stage='won' AND j.revenue_cents IS NULL) unvalued_wins
                FROM stations t WHERE t.business_id=? ORDER BY t.id''',(b['id'],))]
            return {'config':config(c,b['id']),'stages':stages,'due':due,'placements':placements,'server_time':s.ts()}

    @s.app.put('/api/admin/{slug}/growth/config')
    def save_config(slug:str,body:Config,request:Request):
        user=s.user_session(request,True)
        with s.db() as c:
            user,b=authorize(c,slug,user)
            c.execute('''INSERT INTO growth_settings(business_id,profile,review_url,booking_url,setup_complete,updated_at) VALUES(?,?,?,?,?,?)
                ON CONFLICT(business_id) DO UPDATE SET profile=excluded.profile,review_url=excluded.review_url,booking_url=excluded.booking_url,setup_complete=excluded.setup_complete,updated_at=excluded.updated_at''',
                (b['id'],body.profile,body.review_url,body.booking_url,int(body.setup_complete),s.ts()))
            s.audit(c,b['id'],user['user_id'],'growth.settings',b['id'])
            return {'ok':True,'config':config(c,b['id'])}

    @s.app.get('/api/admin/{slug}/growth/jobs')
    def jobs(slug:str,request:Request,stage:str=Query(default='',max_length=20),search:str=Query(default='',max_length=100),before:int|None=Query(default=None,gt=0),limit:int=Query(default=30,ge=1,le=100),due:bool=False):
        if stage and stage not in STAGES: s.fail(400,'Unknown job stage')
        user=s.user_session(request)
        with s.db() as c:
            _,b=authorize(c,slug,user)
            clauses=["r.business_id=?","r.kind='question'"];args=[b['id']]
            if stage: clauses.append(STAGE_SQL+'=?');args.append(stage)
            if before: clauses.append('r.id<?');args.append(before)
            if due: clauses.append("g.followup_at<=? AND g.stage NOT IN ('won','lost','archived')");args.append(s.ts())
            if search.strip():
                term='%'+search.strip().lower().replace('!','!!').replace('%','!%').replace('_','!_')+'%'
                clauses.append("(LOWER(r.message) LIKE ? ESCAPE '!' OR LOWER(COALESCE(r.customer_name,'')) LIKE ? ESCAPE '!' OR LOWER(COALESCE(r.customer_contact,'')) LIKE ? ESCAPE '!')");args.extend([term]*3)
            rows=[dict(r) for r in c.execute('''SELECT r.id,r.message,r.status,r.customer_name,r.customer_contact,r.reply_consent_at,r.created_at,t.label station,
                '''+STAGE_SQL+''' stage,COALESCE(g.revision,0) revision,g.quote_cents,COALESCE(g.quote_description,'') quote_description,g.quote_expires,
                COALESCE(g.quote_revision,0) quote_revision,g.accepted_revision,g.appointment_at,g.followup_at,g.revenue_cents,COALESCE(g.note,'') note
                FROM requests r JOIN stations t ON t.id=r.station_id AND t.business_id=r.business_id
                LEFT JOIN growth_jobs g ON g.request_id=r.id AND g.business_id=r.business_id WHERE '''+' AND '.join(clauses)+' ORDER BY r.id DESC LIMIT ?',tuple(args+[limit+1]))]
            more=len(rows)>limit;rows=rows[:limit]
            return {'jobs':rows,'has_more':more,'next_before':rows[-1]['id'] if more else None}

    @s.app.put('/api/admin/{slug}/growth/jobs/{rid}')
    def save_job(slug:str,rid:s.ResourceID,body:Job,request:Request):
        user=s.user_session(request,True)
        with s.db() as c:
            user,b=authorize(c,slug,user)
            r=c.execute('SELECT kind,status FROM requests WHERE business_id=? AND id=?',(b['id'],rid)).fetchone()
            if not r: s.fail(404,'Request not found')
            if r['kind']!='question': s.fail(400,'Only inquiries can become jobs')
            old=c.execute('SELECT * FROM growth_jobs WHERE business_id=? AND request_id=?',(b['id'],rid)).fetchone()
            if body.revision!=(old['revision'] if old else 0): s.fail(409,'This job changed. Refresh before saving again.')
            if body.stage=='quoted' and (body.quote_cents is None or not body.quote_description.strip() or not body.quote_expires or body.quote_expires<=s.ts()): s.fail(400,'Add a price, scope and future expiry before sharing a quote')
            if body.stage=='booked' and not body.appointment_at: s.fail(400,'Add the confirmed appointment time')
            if body.revenue_cents is not None and body.stage!='won': s.fail(400,'Record revenue only for a won job')
            quote_changed=not old or any(body.model_dump()[k]!=old[k] for k in ('quote_cents','quote_description','quote_expires'))
            qrev=(old['quote_revision'] if old else 0)+(1 if quote_changed and body.quote_cents is not None else 0)
            accepted=old['accepted_revision'] if old and not quote_changed else None
            values=(rid,b['id'],body.stage,body.quote_cents,body.quote_description,body.quote_expires,qrev,accepted,body.appointment_at,body.followup_at,body.revenue_cents,body.note,body.revision+1,s.ts())
            c.execute('''INSERT INTO growth_jobs(request_id,business_id,stage,quote_cents,quote_description,quote_expires,quote_revision,accepted_revision,appointment_at,followup_at,revenue_cents,note,revision,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(request_id) DO UPDATE SET stage=excluded.stage,quote_cents=excluded.quote_cents,quote_description=excluded.quote_description,quote_expires=excluded.quote_expires,quote_revision=excluded.quote_revision,accepted_revision=excluded.accepted_revision,appointment_at=excluded.appointment_at,followup_at=excluded.followup_at,revenue_cents=excluded.revenue_cents,note=excluded.note,revision=excluded.revision,updated_at=excluded.updated_at''',values)
            s.audit(c,b['id'],user['user_id'],'growth.'+body.stage,rid)
            return {'ok':True,'revision':body.revision+1}

    def receipt(c,rid,request,mutate=False):
        if mutate:s.same_origin(request)
        ticket=request.headers.get('x-scene-ticket','')
        if len(ticket)<25:s.fail(401,'Private receipt required')
        s.scope(c,'scene.receipt_hash',s.sha(ticket))
        r=c.execute('SELECT id,business_id,receipt_hash,status FROM requests WHERE id=?',(rid,)).fetchone()
        if not r or not hmac.compare_digest(r['receipt_hash'],s.sha(ticket)):s.fail(404,'Request not found')
        s.scope(c,'scene.tenant_id',r['business_id'])
        return r

    @s.app.get('/api/guest/requests/{rid}/journey')
    def journey(rid:s.ResourceID,request:Request):
        s.rate_limit(request,'growth-receipt',60,60)
        with s.db() as c:
            r=receipt(c,rid,request)
            g=c.execute('SELECT stage,quote_cents,quote_description,quote_expires,quote_revision,accepted_revision,appointment_at FROM growth_jobs WHERE business_id=? AND request_id=?',(r['business_id'],rid)).fetchone()
            result=dict(g) if g else {'stage':'new'}
            if result.get('quote_cents') is not None:result['quote_expired']=not result['quote_expires'] or result['quote_expires']<=s.ts()
            # Completed service requests may offer the same return actions regardless of feedback.
            result['return_links']=config(c,r['business_id']) if r['status']=='completed' else {}
            result['return_links']={k:v for k,v in result['return_links'].items() if k in ('review_url','booking_url')}
            return result

    @s.app.post('/api/guest/requests/{rid}/journey')
    def decide(rid:s.ResourceID,body:Decision,request:Request):
        s.same_origin(request);s.rate_limit(request,'growth-receipt',60,60)
        with s.db() as c:
            r=receipt(c,rid,request,True)
            g=c.execute('SELECT * FROM growth_jobs WHERE business_id=? AND request_id=?',(r['business_id'],rid)).fetchone()
            if not g or g['quote_revision']!=body.quote_revision:s.fail(409,'This quote changed. Refresh your receipt.')
            if g['accepted_revision']==body.quote_revision:
                if body.decision=='decline':s.fail(409,'This quote was already accepted. Contact the business to change it.')
                return {'ok':True,'already_accepted':True}
            if g['stage']!='quoted':s.fail(409,'This quote is no longer offered. Ask the business for an update.')
            if g['quote_cents'] is None or not g['quote_expires'] or g['quote_expires']<=s.ts():s.fail(409,'Quote expired. Ask the business for an update.')
            c.execute('UPDATE growth_jobs SET accepted_revision=?,stage=?,revision=revision+1,updated_at=? WHERE business_id=? AND request_id=?',
                (body.quote_revision if body.decision=='accept' else None,'contacted' if body.decision=='accept' else 'lost',s.ts(),r['business_id'],rid))
            s.audit(c,r['business_id'],None,'quote.'+body.decision,rid)
            return {'ok':True,'note':'Quote response recorded. The business must confirm scheduling. No payment was made.'}
