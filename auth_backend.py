"""Managed identity lifecycle; provider proofs never accept client-supplied roles."""
import base64
import json
import secrets
from pydantic import BaseModel, Field
from fastapi import Request
from fastapi.responses import JSONResponse
import managed_auth


def token_issued_at(token):
    # Claims are used ONLY after provider validation of this exact bearer token.
    try:
        part = token.split('.')[1]
        value = json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))['iat']
        return value if isinstance(value, int) and not isinstance(value, bool) else 0
    except (ValueError, KeyError, IndexError, TypeError):
        return 0


def check_revocation(s, c, subject, token):
    block = c.execute('SELECT revoked_before FROM auth_blocks WHERE subject=?', (subject,)).fetchone()
    if block and token_issued_at(token) <= block['revoked_before']:
        s.fail(401, 'Sign in again after the password change')


def ensure_identity(s, subject, token, email):
    with s.db() as c:
        check_revocation(s, c, subject, token)
        identity = c.execute('SELECT user_id FROM auth_identities WHERE subject=?', (subject,)).fetchone()
        if identity:
            return identity['user_id']
        # Existing beta users require separate dual-proof migration; never link by email.
        if c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            s.fail(403, 'Legacy account requires verified identity migration')
    user = managed_auth.call('user', token=token)
    if (user.get('id') != subject or not user.get('email_confirmed_at') or user.get('is_anonymous')
            or user.get('email', '').lower().strip() != email):
        s.fail(401, 'Verified identity does not match the account')
    with s.db() as c:
        # Repeat under the application transaction lock to prevent concurrent provisioning.
        identity = c.execute('SELECT user_id FROM auth_identities WHERE subject=?', (subject,)).fetchone()
        if identity:
            return identity['user_id']
        if c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            s.fail(403, 'Legacy account requires verified identity migration')
        uid = c.execute('INSERT INTO users(email,password,created_at) VALUES(?,?,?)',
                        (email, '!managed-only!', s.ts())).lastrowid
        s.scope(c, 'scene.auth_subject', subject)
        c.execute('INSERT INTO auth_identities(subject,user_id) VALUES(?,?)', (subject, uid))
        return uid


def start_flow(s, email, purpose, name='', industry=''):
    value = secrets.token_urlsafe(40)
    with s.db() as c:
        c.execute('DELETE FROM auth_flows WHERE expires_at<=?', (s.ts(),))
        c.execute('INSERT INTO auth_flows VALUES(?,?,?,?,?,?)',
                  (s.sha(value), email, purpose, name, industry, s.ts()+1800))
    return value


def flow_cookie(s, response, value):
    response.set_cookie('scene_auth_flow', value, max_age=1800, httponly=True,
                        secure=s.SECURE_COOKIE, samesite='lax', path='/')
    return response


def register(s, body):
    value = start_flow(s, body.email.lower().strip(), 'signup', body.name.strip(), body.industry)
    payload = {'email': body.email.lower().strip(), 'password': body.password}
    if body.captcha_token:
        payload['gotrue_meta_security'] = {'captcha_token': body.captcha_token}
    try:
        managed_auth.call('signup', payload)
    except managed_auth.AuthError:
        s.fail(503, 'Registration unavailable; try again shortly')
    return flow_cookie(s, JSONResponse({'ok': True, 'verification_required': True,
        'note': 'Check your email, then verify in this browser.', 'next': '/auth/confirm'}, status_code=202), value)


def revoke_sessions(s, subject):
    with s.db() as c:
        c.execute('INSERT INTO auth_blocks(subject,revoked_before) VALUES(?,?) ON CONFLICT(subject) DO UPDATE SET revoked_before=excluded.revoked_before',
                  (subject, s.ts()))
        identity = c.execute('SELECT user_id FROM auth_identities WHERE subject=?', (subject,)).fetchone()
        if identity:
            c.execute('DELETE FROM sessions WHERE user_id=?', (identity['user_id'],))


class Verification(BaseModel):
    token: str = Field(default='', max_length=128)
    token_hash: str = Field(default='', max_length=256)


class PasswordChange(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class AcceptInvite(BaseModel):
    token: str = Field(min_length=20, max_length=100)


def accept_invite(s, c, uid, token):
    s.scope(c, 'scene.invite_hash', s.sha(token))
    invitation = c.execute('SELECT * FROM invites WHERE token_hash=? AND used_at IS NULL AND expires_at>?',
                            (s.sha(token), s.ts())).fetchone()
    if not invitation:
        s.fail(410, 'Invitation expired or already used')
    email = c.execute('SELECT email FROM users WHERE id=?', (uid,)).fetchone()['email']
    if invitation['email'] and invitation['email'] != email:
        s.fail(403, 'Invitation is addressed to another account')
    s.scope(c, 'scene.tenant_id', invitation['business_id'])
    if c.execute('SELECT 1 FROM memberships WHERE business_id=? AND user_id=?', (invitation['business_id'], uid)).fetchone():
        s.fail(409, 'Already on this business team')
    c.execute('INSERT INTO memberships VALUES(?,?,?)', (invitation['business_id'], uid, invitation['role']))
    changed = c.execute('UPDATE invites SET used_at=? WHERE token_hash=? AND used_at IS NULL AND expires_at>?',
                        (s.ts(), s.sha(token), s.ts()))
    if changed.rowcount != 1:
        s.fail(409, 'Invitation changed; try again')
    s.audit(c, invitation['business_id'], uid, 'member.joined', uid)


def install(s):
    @s.app.post('/api/auth/verify')
    def verify(body: Verification, request: Request):
        s.same_origin(request); s.rate_limit(request, 'verify', 8, 300)
        if not managed_auth.enabled(): s.fail(503, 'Managed verification is not configured')
        flow_token = request.cookies.get('scene_auth_flow', '')
        with s.db() as c:
            flow = c.execute('SELECT * FROM auth_flows WHERE flow_hash=? AND expires_at>?', (s.sha(flow_token), s.ts())).fetchone()
        if not flow: s.fail(410, 'Start verification again in this browser')
        if bool(body.token) == bool(body.token_hash): s.fail(400, 'Provide one verification code')
        payload = {'type': flow['purpose']}
        if body.token_hash:
            payload['token_hash'] = body.token_hash
        else:
            payload.update(email=flow['email'], token=body.token)
        try:
            result = managed_auth.call('verify', payload)
            token = result.get('access_token')
            subject = managed_auth.verified_user(token)
            uid = ensure_identity(s, subject, token, flow['email'])
            lifetime = valid_lifetime(result)
        except managed_auth.AuthError:
            s.fail(401, 'Verification code is invalid or expired')
        with s.db() as c:
            deleted = c.execute('DELETE FROM auth_flows WHERE flow_hash=? AND expires_at>?', (s.sha(flow_token), s.ts()))
            if deleted.rowcount != 1: s.fail(410, 'Verification already completed')
            organization = None
            if flow['purpose']=='signup' and flow['name'] and flow['industry'] in s.INDUSTRIES:
                organization = s.platform_api.create_business(s,c,uid,flow['name'],flow['industry'])
        response = JSONResponse({'ok': True, 'recovery': flow['purpose']=='recovery', 'onboarding_required': organization is None, 'organization': organization})
        s.signin(response, uid, token, min(lifetime, 300 if flow['purpose']=='recovery' else 3600), purpose='recovery' if flow['purpose']=='recovery' else 'login')
        response.delete_cookie('scene_auth_flow', path='/')
        return response

    @s.app.post('/api/auth/complete-recovery')
    def complete_recovery(body: PasswordChange, request: Request):
        s.same_origin(request); s.rate_limit(request, 'complete-recovery', 5, 3600)
        session = s.user_session(request, True, purpose='recovery')
        try:
            subject = managed_auth.verified_user(session['managed_token'])
            # Revoke locally BEFORE the external write. Failure never leaves old sessions usable.
            revoke_sessions(s, subject)
            managed_auth.call('user', {'password': body.password}, token=session['managed_token'], method='PUT')
        except managed_auth.AuthError:
            s.fail(503, 'Recovery could not finish; request a new code')
        response = JSONResponse({'ok': True, 'note': 'Password changed. Sign in again.'})
        response.delete_cookie('scene_session', path='/')
        return response

    @s.app.post('/api/auth/accept-invite')
    def accept(body: AcceptInvite, request: Request):
        session = s.user_session(request, True)
        with s.db() as c:
            accept_invite(s, c, session['user_id'], body.token)
        return {'ok': True}

    @s.app.post('/api/auth/logout-all')
    def logout_all(request: Request):
        session = s.user_session(request, True)
        with s.db() as c:
            c.execute('DELETE FROM sessions WHERE user_id=?', (session['user_id'],))
        response = JSONResponse({'ok': True})
        response.delete_cookie('scene_session', path='/')
        return response


def valid_lifetime(result):
    lifetime = result.get('expires_in', 300)
    if not isinstance(lifetime, int) or isinstance(lifetime, bool) or lifetime <= 0:
        raise managed_auth.AuthError('Invalid token lifetime')
    return min(lifetime, 3600)
