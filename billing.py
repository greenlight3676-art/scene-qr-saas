"""Mode-checked Stripe transport and subscription projection. No card data stored.

Test mode is the default. Live mode requires an explicit private host setting
and matching live credentials; this module never enables it automatically.
Signed snapshot events trigger canonical subscription reads, so delayed snapshots
cannot resurrect canceled or past-due entitlements.
"""
import hashlib
import hmac
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request as URLRequest, build_opener
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from managed_auth import NoRedirect

urlopen = build_opener(NoRedirect).open


class BillingError(Exception): pass


def live_mode():
    mode=os.getenv('SCENE_BILLING_MODE','test')
    if mode not in ('test','live'): raise BillingError('Choose test or live billing mode')
    return mode=='live'


def plans():
    try:
        value = json.loads(os.getenv('SCENE_STRIPE_PRICES', '{}'))
        if not isinstance(value, dict) or any(not re.fullmatch(r'[a-z0-9_-]{1,32}', k) or not isinstance(v,str) or not re.fullmatch(r'price_[A-Za-z0-9]+', v) for k,v in value.items()):
            raise ValueError()
        return value
    except (ValueError, TypeError): raise BillingError('Invalid server price mapping') from None


def configuration():
    key = os.getenv('SCENE_STRIPE_SECRET_KEY','')
    prefixes=('sk_live_','rk_live_') if live_mode() else ('sk_test_','rk_test_')
    if not key.startswith(prefixes):
        raise BillingError('Stripe credentials must match the configured billing mode')
    return key


def configuration_status():
    """Only configuration facts, never secrets or a claim of provider acceptance."""
    try:
        mode='live' if live_mode() else 'test'
        configuration()
        choices=plans()
        secrets=[v.strip() for v in os.getenv('SCENE_STRIPE_WEBHOOK_SECRETS','').split(',') if v.strip()]
        ready=bool(choices and secrets and all(v.startswith('whsec_') for v in secrets)
                   and re.fullmatch(r'20\d\d-\d\d-\d\d\.[a-z]+',os.getenv('SCENE_STRIPE_API_VERSION','')))
        return {'configured':ready,'mode':mode,'plans':list(choices) if ready else []}
    except BillingError:
        return {'configured':False,'mode':os.getenv('SCENE_BILLING_MODE','test') if os.getenv('SCENE_BILLING_MODE','test') in ('test','live') else 'unconfigured','plans':[]}


def call(path, fields=None, idempotency=None):
    key=configuration()
    headers={'Authorization':'Bearer '+key,'Content-Type':'application/x-www-form-urlencoded'}
    # An explicit deployment version is required to prevent silent account-version drift.
    version=os.getenv('SCENE_STRIPE_API_VERSION','')
    if not re.fullmatch(r'20\d\d-\d\d-\d\d\.[a-z]+', version): raise BillingError('Pin a reviewed Stripe API version')
    headers['Stripe-Version']=version
    if idempotency: headers['Idempotency-Key']=idempotency
    req=URLRequest('https://api.stripe.com/v1/'+path, data=None if fields is None else urlencode(fields).encode(), headers=headers)
    try:
        with urlopen(req,timeout=10) as response: result=json.loads(response.read(262145))
        if not isinstance(result,dict) or ('livemode' in result and result['livemode'] is not live_mode()): raise ValueError()
        return result
    except (HTTPError,URLError,TimeoutError,OSError,ValueError):
        raise BillingError('Stripe unavailable; retry with the same idempotency key') from None


def verify_signature(body, header, now=None):
    secrets=[v.strip() for v in os.getenv('SCENE_STRIPE_WEBHOOK_SECRETS','').split(',') if v.strip()]
    if not secrets or any(not v.startswith('whsec_') for v in secrets): raise BillingError('Webhook verification is not configured')
    parts={}
    try:
        for part in header.split(','):
            key,value=part.split('=',1);parts.setdefault(key,[]).append(value)
        if len(parts.get('t',[])) != 1: raise ValueError()
        stamp=int(parts['t'][0])
        if abs((int(time.time()) if now is None else now)-stamp)>300: raise ValueError()
        signed=str(stamp).encode()+b'.'+body
        if not any(hmac.compare_digest(hmac.new(secret.encode(),signed,hashlib.sha256).hexdigest(), sig)
                   for secret in secrets for sig in parts.get('v1',[]) if re.fullmatch('[a-fA-F0-9]{64}',sig)):
            raise ValueError()
    except (ValueError,TypeError,KeyError): raise ValueError('Invalid webhook signature') from None


def require_entitlement(s,c,bid):
    if os.getenv('SCENE_REQUIRE_SUBSCRIPTION','0') != '1': return
    row=c.execute('SELECT status,price_id,valid_until FROM billing_accounts WHERE business_id=?',(bid,)).fetchone()
    if not row or row['status'] not in ('active','trialing') or row['valid_until']<=s.ts() or row['price_id'] not in plans().values():
        s.fail(402,'An active platform subscription is required for new guest requests')


def event_projection(s,c,event):
    kind=event['type'];obj=event.get('data',{}).get('object',{})
    if not isinstance(obj,dict): raise ValueError('Invalid event object')
    if kind.startswith('customer.subscription.'):
        sub_id=obj.get('id');customer=obj.get('customer')
    elif kind in ('invoice.paid','invoice.payment_failed'):
        sub_id=obj.get('subscription') or (obj.get('parent') or {}).get('subscription_details',{}).get('subscription')
        customer=obj.get('customer')
    else: return 'ignored'
    if not isinstance(sub_id,str) or not re.fullmatch(r'sub_[A-Za-z0-9]+',sub_id): return 'ignored'
    if not isinstance(customer,str) or not re.fullmatch(r'cus_[A-Za-z0-9]+', customer):
        raise ValueError('Invalid event customer')
    account=c.execute('SELECT * FROM billing_accounts WHERE customer_id=?',(customer,)).fetchone()
    if not account: return 'ignored'
    s.scope(c,'scene.tenant_id',account['business_id'])
    # Backend-only customer lookup scope is narrowed before touching private data.
    account=c.execute('SELECT * FROM billing_accounts WHERE business_id=?',(account['business_id'],)).fetchone()
    if account['subscription_id'] not in (None,sub_id) and account['status'] not in ('canceled','incomplete_expired'): return 'ignored'
    subscription=call('subscriptions/'+quote(sub_id,safe=''))
    if not isinstance(subscription,dict): raise BillingError('Invalid subscription response')
    if subscription.get('id') != sub_id or subscription.get('customer') != customer or subscription.get('livemode') is not live_mode():
        raise BillingError('Subscription identity mismatch')
    collection=subscription.get('items')
    items=collection.get('data') if isinstance(collection,dict) else None
    if not isinstance(items,list) or len(items)!=1 or not isinstance(items[0],dict):
        raise BillingError('Unexpected subscription items')
    item=items[0]
    price_data=item.get('price')
    if not isinstance(price_data,dict) or not isinstance(price_data.get('id'),str):
        raise BillingError('Invalid subscription price')
    price=price_data['id']
    end=item.get('current_period_end') or subscription.get('current_period_end') or subscription.get('trial_end') or 0
    if not isinstance(end,int) or isinstance(end,bool) or not 0 <= end <= 9223372036854775807: raise BillingError('Invalid subscription term')
    status=subscription.get('status')
    if status not in ('active','trialing','past_due','unpaid','canceled','incomplete','incomplete_expired','paused'):
        status='unconfigured'
    if price not in plans().values() or subscription.get('pause_collection'):
        status='unconfigured'
    c.execute('UPDATE billing_accounts SET subscription_id=?,status=?,price_id=?,valid_until=?,event_created=?,updated_at=? WHERE business_id=?',
              (sub_id,status,price,end,event['created'],s.ts(),account['business_id']))
    s.audit(c,account['business_id'],None,'subscription.'+status,account['business_id'])
    return 'processed'


def process_webhook(s, body, signature):
    try: verify_signature(body, signature)
    except BillingError:s.fail(503,'Webhook verification is not configured')
    except ValueError:s.fail(400,'Invalid webhook signature')
    try:
        event=json.loads(body)
        if (not isinstance(event,dict) or not isinstance(event.get('id'),str)
                or not re.fullmatch(r'evt_[A-Za-z0-9]+',event['id']) or not isinstance(event.get('type'),str)
                or not isinstance(event.get('created'),int) or isinstance(event.get('created'),bool)
                or not 0 <= event['created'] <= 9223372036854775807
                or event.get('livemode') is not live_mode() or event.get('account')):
            raise ValueError()
        digest=hashlib.sha256(body).hexdigest()
        with s.db() as c:
            prior=c.execute('SELECT payload_hash FROM billing_events WHERE event_id=?',(event['id'],)).fetchone()
            if prior:
                if prior['payload_hash']!=digest:s.fail(409,'Event identifier reused with a different payload')
                return {'ok':True,'duplicate':True}
            # Resolve the public Stripe customer ID using a capability, not broad tenant access.
            customer=event.get('data',{}).get('object',{}).get('customer')
            s.scope(c,'scene.billing_customer',customer if isinstance(customer,str) else '')
            result=event_projection(s,c,event)
            c.execute('INSERT INTO billing_events VALUES(?,?,?,?,?)',(event['id'],digest,event['type'],event['created'],s.ts()))
        return {'ok':True,'result':result}
    except BillingError:s.fail(503,'Subscription reconciliation unavailable; Stripe should retry')
    except (ValueError,TypeError,KeyError,AttributeError):s.fail(400,'Invalid event payload')


class Checkout(BaseModel):
    plan: str=Field(min_length=1,max_length=32)


def install(s):
    @s.app.post('/api/billing/webhook')
    async def webhook(request: Request):
        body=await request.body()
        return await run_in_threadpool(process_webhook, s, body, request.headers.get('stripe-signature',''))

    @s.app.get('/api/admin/{slug}/billing')
    def billing_status(slug: str,request: Request):
        session=s.user_session(request)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],{'owner'})
            row=c.execute('SELECT status,price_id,valid_until,updated_at FROM billing_accounts WHERE business_id=?',(b['id'],)).fetchone()
            configured=configuration_status()
            return {'subscription':dict(row) if row else None,'test_mode':configured['mode']=='test',
                    **configured,'portal_available':bool(row and row['status']!='unconfigured')}

    @s.app.post('/api/admin/{slug}/billing/checkout')
    def checkout(slug: str,body: Checkout,request: Request):
        session=s.user_session(request,True);s.rate_limit(request,'checkout',10,3600)
        idem=request.headers.get('idempotency-key','')
        if not re.fullmatch(r'[A-Za-z0-9_-]{20,100}',idem):s.fail(400,'A stable Idempotency-Key is required')
        try:
            configuration();price=plans().get(body.plan)
            if not price:s.fail(400,'Unknown subscription plan')
            origin=s.PUBLIC_URL
            if not origin.startswith('https://'):s.fail(503,'Configure the public HTTPS origin')
            with s.db() as c:
                b=s.grant(c,slug,session['user_id'],{'owner'})
                row=c.execute('SELECT * FROM billing_accounts WHERE business_id=?',(b['id'],)).fetchone()
                if row and row['status'] in ('active','trialing','past_due','unpaid'):s.fail(409,'Manage the existing subscription in the billing portal')
                customer=row['customer_id'] if row else None
                if not customer:
                    created=call('customers',{'metadata[scene_business_id]':b['id']},'scene-customer-'+str(b['id']))
                    customer=created.get('id')
                    if not isinstance(customer,str) or not re.fullmatch(r'cus_[A-Za-z0-9]+',customer):raise BillingError()
                    c.execute('INSERT INTO billing_accounts(business_id,customer_id,updated_at) VALUES(?,?,?) ON CONFLICT(business_id) DO UPDATE SET customer_id=excluded.customer_id', (b['id'],customer,s.ts()))
                result=call('checkout/sessions',{'customer':customer,'mode':'subscription','line_items[0][price]':price,
                    'line_items[0][quantity]':1,'success_url':origin+'/?billing=return','cancel_url':origin+'/?billing=cancel'},f'scene-checkout-{b["id"]}-{idem}')
                url=result.get('url','')
                if urlsplit(url).hostname!='checkout.stripe.com' or not url.startswith('https://'):raise BillingError()
                return {'url':url,'test_mode':not live_mode()}
        except BillingError:s.fail(503,'Subscription billing is not configured or unavailable')

    @s.app.post('/api/admin/{slug}/billing/portal')
    def portal(slug: str,request: Request):
        session=s.user_session(request,True);s.rate_limit(request,'billing-portal',10,3600)
        try:
            with s.db() as c:
                b=s.grant(c,slug,session['user_id'],{'owner'})
                row=c.execute('SELECT customer_id FROM billing_accounts WHERE business_id=?',(b['id'],)).fetchone()
                if not row or not row['customer_id']:s.fail(404,'No subscription customer')
                if not s.PUBLIC_URL.startswith('https://'):s.fail(503,'Configure public HTTPS origin')
                result=call('billing_portal/sessions',{'customer':row['customer_id'],'return_url':s.PUBLIC_URL+'/'})
                url=result.get('url','')
                if urlsplit(url).hostname!='billing.stripe.com' or not url.startswith('https://'):raise BillingError()
                return {'url':url,'test_mode':not live_mode()}
        except BillingError:s.fail(503,'Subscription billing is not configured or unavailable')
