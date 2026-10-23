"""Durable invitation outbox. Worker is explicit, dry-run by default, never auto-started."""
import argparse
import json
import os
import re
import secrets
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
from managed_auth import NoRedirect

urlopen=build_opener(NoRedirect).open


class DeliveryError(Exception): pass


def enqueue(s,c,bid,email,invite_hash,url):
    mid=secrets.token_hex(16)
    payload=json.dumps({'to':[email],'subject':'Your invitation to Scene QR',
        'text':'You have been invited to a Scene QR business team. Sign in with your verified account and use this single-use link within 24 hours: '+url+'\nIf you did not expect this invitation, ignore it.'},sort_keys=True)
    c.execute('INSERT INTO mail_outbox(id,business_id,invite_hash,recipient,payload,created_at,next_attempt) VALUES(?,?,?,?,?,?,?)',
              (mid,bid,invite_hash,email,payload,s.ts(),s.ts()))
    return mid


def send(payload,key):
    secret=os.getenv('SCENE_RESEND_API_KEY','');sender=os.getenv('SCENE_MAIL_FROM','')
    if os.getenv('SCENE_MAIL_SEND','0')!='1' or not secret.startswith('re_') or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',sender):
        raise DeliveryError('Mail delivery is not enabled/configured')
    data=json.loads(payload);data['from']=sender
    request=Request('https://api.resend.com/emails',data=json.dumps(data).encode(),headers={
        'Authorization':'Bearer '+secret,'Content-Type':'application/json','Idempotency-Key':'scene-invite-'+key})
    try:
        with urlopen(request,timeout=10) as response: result=json.loads(response.read(65536))
        if not isinstance(result.get('id'),str):raise ValueError()
        return result['id']
    except (HTTPError,URLError,TimeoutError,OSError,ValueError):
        raise DeliveryError('Delivery unavailable') from None


def process_one(s,deliver=send,business_id=None):
    with s.db() as c:
        s.scope(c,'scene.mail_worker','1')
        if business_id is None:
            row=c.execute("SELECT * FROM mail_outbox WHERE state='pending' AND next_attempt<=? ORDER BY created_at,id LIMIT 1",(s.ts(),)).fetchone()
        else:
            row=c.execute("SELECT * FROM mail_outbox WHERE state='pending' AND next_attempt<=? AND business_id=? ORDER BY created_at,id LIMIT 1",(s.ts(),business_id)).fetchone()
        if not row:return 'empty'
        s.scope(c,'scene.tenant_id',row['business_id'])
        invite=c.execute('SELECT expires_at,used_at FROM invites WHERE business_id=? AND token_hash=?',(row['business_id'],row['invite_hash'])).fetchone()
        # Never retry outside the provider idempotency window, or send revoked/used invites.
        if not invite or invite['used_at'] or invite['expires_at']<=s.ts() or s.ts()-row['created_at']>=82800 or row['attempts']>=8:
            c.execute("UPDATE mail_outbox SET state='review' WHERE id=? AND business_id=?",(row['id'],row['business_id']))
            return 'review'
        try:
            provider_id=deliver(row['payload'],row['id'])
        except DeliveryError:
            c.execute('UPDATE mail_outbox SET attempts=attempts+1,next_attempt=? WHERE id=? AND business_id=?',
                      (s.ts()+min(3600,30*2**row['attempts']),row['id'],row['business_id']))
            return 'retry'
        c.execute("UPDATE mail_outbox SET state='accepted',provider_id=?,attempts=attempts+1 WHERE id=? AND business_id=?",(provider_id,row['id'],row['business_id']))
        s.audit(c,row['business_id'],None,'invite.email_accepted',row['business_id'])
        # 'accepted' means provider accepted, not proof of inbox delivery.
        return 'accepted'


def install(s):
    from fastapi import Request
    @s.app.get('/api/admin/{slug}/mail')
    def status(slug: str,request: Request):
        session=s.user_session(request)
        with s.db() as c:
            b=s.grant(c,slug,session['user_id'],{'owner'})
            rows=c.execute('SELECT id,recipient,state,attempts,created_at,next_attempt FROM mail_outbox WHERE business_id=? ORDER BY created_at DESC LIMIT 100',(b['id'],)).fetchall()
            return {'messages':[dict(row) for row in rows]}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send',action='store_true',help='Operator-approved external delivery; requires SCENE_MAIL_SEND=1')
    args=parser.parse_args()
    if not args.send:
        print('Dry run: no email sent. Review owner-visible /api/admin/{slug}/mail and record scoped sending approval before --send.')
    else:
        import server
        print(process_one(server))
