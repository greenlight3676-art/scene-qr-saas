"""Server-only Supabase Auth transport. No service/owner keys or browser tokens.

Subject bindings are deliberately provisioned separately: email is not identity.
The public API key authenticates the project, never authorizes app data access.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import UUID

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


urlopen = build_opener(NoRedirect).open

PROJECT_URL = 'https://cwehqnziwabvnzviaqlf.supabase.co'


class AuthError(Exception):
    pass


def enabled():
    return os.getenv('SCENE_AUTH_MODE', 'local') == 'supabase'


def validate_config():
    mode = os.getenv('SCENE_AUTH_MODE', 'local')
    if mode not in ('local', 'supabase'):
        raise RuntimeError('Unsupported SCENE_AUTH_MODE')
    if mode == 'supabase':
        key = os.getenv('SCENE_SUPABASE_PUBLISHABLE_KEY', '')
        # Only modern publishable keys: legacy JWT/service keys are not accepted.
        if not key.startswith('sb_publishable_') or len(key) < 25:
            raise RuntimeError('A Supabase publishable key is required')
        if os.getenv('SCENE_SECURE_COOKIE') != '1' or os.getenv('SCENE_DEMO', '0') == '1':
            raise RuntimeError('Managed authentication requires secure cookies and no demo mode')


def call(path, payload=None, token=None, method=None):
    key = os.getenv('SCENE_SUPABASE_PUBLISHABLE_KEY', '')
    if not key.startswith('sb_publishable_'):
        raise AuthError('Authentication unavailable')
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(PROJECT_URL + '/auth/v1/' + path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read(65537))
        if not isinstance(result, dict):
            raise ValueError('Invalid auth response')
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        # Never surface provider bodies, tokens, passwords or request URLs.
        raise AuthError('Authentication unavailable or credentials rejected') from None


def verified_user(token):
    if not isinstance(token, str) or not 20 <= len(token) <= 8192:
        raise AuthError('Invalid access token')
    user = call('user', token=token)
    try:
        subject = str(UUID(user['id']))
    except (KeyError, ValueError, TypeError, AttributeError):
        raise AuthError('Invalid identity') from None
    if not user.get('email_confirmed_at') or user.get('is_anonymous', False):
        raise AuthError('Verified email required')
    return subject


def password_login(email, password):
    result = call('token?grant_type=password', {'email': email, 'password': password})
    token = result.get('access_token')
    subject = verified_user(token)
    lifetime = result.get('expires_in')
    if not isinstance(lifetime, int) or isinstance(lifetime, bool) or lifetime <= 0:
        raise AuthError('Invalid token lifetime')
    return subject, token, min(lifetime, 3600)
