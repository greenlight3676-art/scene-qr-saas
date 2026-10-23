"""Production configuration, shared abuse controls and body limits; no secret logging."""
import hashlib
import json
import logging
import os
import re
import time
from urllib.parse import urlsplit
from uuid import uuid4
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

LOG = logging.getLogger('scene.http')
MAX_BODY = 65536


def validate_environment():
    env = os.getenv('SCENE_ENV', 'development')
    if env not in ('development', 'test', 'production'):
        raise RuntimeError('Unsupported SCENE_ENV')
    if env != 'production': return
    from managed_auth import validate_config
    validate_config()
    parsed = urlsplit(os.getenv('SCENE_PUBLIC_URL', ''))
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise RuntimeError('Production requires an HTTPS SCENE_PUBLIC_URL origin')
    if (os.getenv('SCENE_DEMO', '0') != '0' or os.getenv('SCENE_SECURE_COOKIE') != '1'
            or os.getenv('SCENE_AUTH_MODE') != 'supabase' or not os.getenv('SCENE_DATABASE_URL')):
        raise RuntimeError('Production requires managed Auth, PostgreSQL, secure cookies and no demo mode')
    hosts = os.getenv('SCENE_TRUSTED_HOSTS', '').split(',')
    if not hosts or any(not h.strip() or '*' in h for h in hosts) or parsed.hostname not in [h.strip() for h in hosts]:
        raise RuntimeError('Production requires explicit trusted hosts including the public hostname')
    if os.getenv('SCENE_REQUIRE_GUEST_SESSION') != '1':
        raise RuntimeError('Production requires guest session enforcement')
    # Do not silently expose a backend without subscription enforcement.
    if os.getenv('SCENE_REQUIRE_SUBSCRIPTION') != '1':
        raise RuntimeError('Production requires subscription enforcement')


def durable_limit(s, request, operation, limit, window):
    now = s.ts()
    # Trust only the ASGI peer. Proxy forwarding must be restricted by deployment.
    ip = request.client.host if request.client else 'unknown'
    bucket = hashlib.sha256(f'{operation}:{ip}:{now//window}'.encode()).hexdigest()
    denied = False
    with s.db() as c:
        c.execute('DELETE FROM rate_buckets WHERE expires_at<=?', (now,))
        c.execute('INSERT INTO rate_buckets(bucket,hits,expires_at) VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET hits=rate_buckets.hits+1',
                  (bucket, (now//window+1)*window))
        hits = c.execute('SELECT hits FROM rate_buckets WHERE bucket=?', (bucket,)).fetchone()['hits']
        denied = hits > limit
    # Commit the counter even on rejection; retries cannot evade durable limits.
    if denied: s.fail(429, 'Too many requests. Try again shortly.')


class RequestBoundary:
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request_id, started = uuid4().hex, time.monotonic()
        status = 500
        chunks, size = [], 0
        # Bound streamed/chunked bodies too, not merely Content-Length.
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect': return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > MAX_BODY:
                response = JSONResponse({'detail': 'Request body is too large'}, status_code=413,
                                        headers={'X-Request-ID': request_id})
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get('more_body'): break
        delivered = False
        response_started = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type':'http.request', 'body':b''.join(chunks), 'more_body':False}
            return await receive()

        async def safe_send(message):
            nonlocal status, response_started
            if message['type'] == 'http.response.start':
                response_started = True
                status = message['status']
                message['headers'] = list(message.get('headers', [])) + [(b'x-request-id', request_id.encode())]
            await send(message)
        try:
            await self.app(scope, bounded_receive, safe_send)
        except Exception as exc:
            LOG.error(json.dumps({'request_id':request_id,'error_type':type(exc).__name__}))
            if not response_started:
                response = JSONResponse({'detail':'Service temporarily unavailable'},status_code=500)
                await response(scope,bounded_receive,safe_send)
        finally:
            route = getattr(scope.get('route'), 'path', '<unmatched>')
            # Route templates, not paths/query strings, cookies, IPs or payloads.
            LOG.info(json.dumps({'request_id':request_id, 'route':route, 'method':scope['method'],
                                 'status':status, 'duration_ms':round((time.monotonic()-started)*1000)}))


def install(s):
    hosts = [h.strip() for h in os.getenv('SCENE_TRUSTED_HOSTS','').split(',') if h.strip()]
    if hosts: s.app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    s.app.add_middleware(RequestBoundary)

    @s.app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({'detail':[{'loc':list(e['loc']), 'msg':e['msg'], 'type':e['type']} for e in exc.errors()]}, status_code=422)

    @s.app.get('/readyz')
    def ready():
        try:
            with s.db() as c:
                c.execute('SELECT count(*) AS n FROM rate_buckets').fetchone()
                if s.DATABASE_URL:
                    from backend_schema import VERSION
                    row = c.execute('SELECT version FROM scene_migrations').fetchone()
                    if not row or row['version'] != VERSION: raise RuntimeError()
        except Exception:
            return JSONResponse({'ok':False}, status_code=503)
        return {'ok':True}
