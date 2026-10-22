"""Stdlib smoke test for an isolated CI container; synthetic data only.

Run using docker exec -i scene-smoke python - [verify] < tests/container_smoke.py.
The verify phase runs after restarting the same container and its /data directory.
"""
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base = 'http://127.0.0.1:8000'


def call(path, body=None, method=None, headers=None):
    request = urllib.request.Request(base + path, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json', **(headers or {})})
    with opener.open(request, timeout=10) as response:
        return json.load(response)


assert call('/healthz') == {'ok': True, 'mode': 'pilot'}
for path in ['/api/demo/trio-demo', '/docs']:
    try:
        opener.open(base + path)
    except urllib.error.HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError('Demo/docs exposed in production image')
account = {'email': 'container-fixture@example.invalid', 'password': 'SyntheticContainerFixture123!'}
verify = len(sys.argv) > 1 and sys.argv[1] == 'verify'
if verify:
    call('/api/auth/login', account)
else:
    call('/api/auth/signup', {**account, 'name': 'Synthetic Container Studio', 'industry': 'auto'})
me = call('/api/me')
slug = me['businesses'][0]['slug']
headers = {'x-scene-csrf': me['csrf']}
board = call('/api/admin/' + slug)
if not verify:
    token = board['stations'][0]['token']
    request = call('/api/q/' + token + '/requests', {
        'kind': 'service', 'client_key': 'synthetic-container-request-0001'})
    call(f'/api/admin/{slug}/requests/{request["request_id"]}',
         {'status': 'completed'}, 'PATCH', headers)
else:
    assert board['analytics']['total'] == 1
    assert board['requests'][0]['status'] == 'completed'
    assert board['name'] == 'Synthetic Container Studio'
print('Synthetic container workflow passed' + (' after restart' if verify else ''))
