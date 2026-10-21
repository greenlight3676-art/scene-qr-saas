"""Opt-in real Chromium checks against a local, isolated SQLite server."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(os.getenv('SCENE_BROWSER_TESTS') != '1',
                                reason='Set SCENE_BROWSER_TESTS=1 with Playwright Chromium installed')


@pytest.fixture
def local_site(tmp_path):
    import httpx
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'SCENE_DEMO': '0', 'SCENE_DATABASE_URL': '',
           'SCENE_DB': str(tmp_path / 'browser.sqlite'), 'SCENE_PUBLIC_URL': url,
           'SCENE_SECURE_COOKIE': '0'}
    with (tmp_path / 'server.log').open('w') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server:app',
                                    '--host', '127.0.0.1', '--port', str(port)],
                                   cwd=Path(__file__).resolve().parents[1], env=env,
                                   stdout=log, stderr=log)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail('Local test server exited; inspect temporary server log')
                try:
                    if httpx.get(url + '/healthz').status_code == 200:
                        break
                except httpx.TransportError:
                    time.sleep(0.1)
            else:
                pytest.fail('Local test server did not start')
            yield url
        finally:
            process.terminate()
            process.wait(timeout=10)


@pytest.mark.parametrize('width', [320, 390, 768])
def test_mobile_guest_to_dashboard_request(local_site, width, tmp_path):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            owner = browser.new_context(viewport={'width': width, 'height': 844},
                                        reduced_motion='reduce', base_url=local_site)
            guest = browser.new_context(viewport={'width': width, 'height': 844},
                                        reduced_motion='reduce', base_url=local_site)
            result = owner.request.post('/api/auth/signup', data={
                'email': 'browser@example.invalid', 'password': 'SyntheticBrowserFixture123!',
                'name': 'Sample mobile business with a deliberately long name for small screens',
                'industry': 'auto'})
            assert result.ok
            slug = result.json()['slug']
            board = owner.request.get('/api/admin/' + slug).json()
            token = board['stations'][0]['token']
            dashboard, phone = owner.new_page(), guest.new_page()
            errors = []
            dashboard.on('pageerror', lambda error: errors.append(str(error)))
            phone.on('pageerror', lambda error: errors.append(str(error)))
            dashboard.goto('/')
            expect(dashboard.locator('#appShell')).to_be_visible()
            phone.goto('/?q=' + token)
            phone.locator('[data-kind="service"]').click()
            expect(phone.locator('#receiptState')).to_have_text('open')
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="requests"]').click()
            expect(dashboard.locator('#sidebarCurtain')).to_be_hidden()
            dashboard.locator('[data-action="refresh"]').click()
            control = dashboard.locator('[data-status-id]').first
            expect(control).to_be_visible()
            control.scroll_into_view_if_needed()
            box = control.bounding_box()
            assert box['height'] >= 44
            assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
            for page in (dashboard, phone):
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            control.select_option('completed')
            expect(dashboard.locator('.request-card').first).to_contain_text('COMPLETED')
            expect(phone.locator('#receiptState')).to_have_text('completed', timeout=12000)
            assert not errors, errors
            dashboard.screenshot(path=str(tmp_path / f'dashboard-{width}.png'), full_page=True)
            phone.screenshot(path=str(tmp_path / f'guest-{width}.png'), full_page=True)
        finally:
            browser.close()


@pytest.mark.parametrize('width', [320, 390])
def test_mobile_inquiries_receipts_and_owner_team_controls(local_site, width):
    from urllib.parse import parse_qs, urlsplit
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            owner = browser.new_context(viewport={'width':width,'height':844}, reduced_motion='reduce', base_url=local_site)
            guest = browser.new_context(viewport={'width':width,'height':844}, reduced_motion='reduce', base_url=local_site)
            member = browser.new_context(base_url=local_site)
            result = owner.request.post('/api/auth/signup', data={
                'email':'workflow@example.invalid','password':'SyntheticBrowserFixture123!',
                'name':'Sample inquiry studio','industry':'auto'})
            assert result.ok
            slug = result.json()['slug']
            csrf = {'x-scene-csrf':owner.request.get('/api/me').json()['csrf']}
            token = owner.request.get('/api/admin/'+slug).json()['stations'][0]['token']
            for name in ('Sample service one','Sample service two'):
                assert owner.request.post(f'/api/admin/{slug}/products', headers=csrf,
                                          data={'name':name,'price_cents':100}).ok
            invitation = owner.request.post(f'/api/admin/{slug}/invites', headers=csrf, data={'role':'manager'}).json()
            invite_token = parse_qs(urlsplit(invitation['join_url']).query)['invite'][0]
            assert member.request.post('/api/auth/join', data={
                'token':invite_token,'email':'teammate@example.invalid','password':'SyntheticBrowserFixture123!'}).ok
            member_csrf = {'x-scene-csrf':member.request.get('/api/me').json()['csrf']}
            phone, dashboard = guest.new_page(), owner.new_page()
            errors = []
            for page in (phone,dashboard):
                page.on('pageerror',lambda error:errors.append(str(error)))
            phone.goto('/?q='+token)
            phone.locator('[data-add]').nth(0).click()
            phone.locator('[data-add]').nth(1).click()
            phone.locator('[data-send-cart]').click()
            expect(phone.locator('[data-receipt-id]')).to_have_count(2)
            phone.locator('[data-kind="question"]').click()
            phone.locator('#guestNote').fill('Synthetic inquiry for browser verification')
            phone.locator('#guestName').fill('Sample Guest')
            phone.locator('#guestContact').fill('guest@example.invalid')
            phone.locator('#guestMessageForm button').click()
            expect(phone.locator('[data-receipt-id]')).to_have_count(2)
            assert phone.locator('#guestConsent').evaluate('(node)=>!node.checkValidity()')
            phone.locator('#guestConsent').check()
            phone.locator('#guestMessageForm button').click()
            expect(phone.locator('[data-receipt-id]')).to_have_count(3)
            phone.reload()
            expect(phone.locator('[data-receipt-id]')).to_have_count(3)
            assert phone.evaluate("!Object.values(sessionStorage).some(value=>value.includes('guest@example.invalid'))")
            dashboard.goto('/')
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="team"]').click()
            role = dashboard.locator('[data-member-role]')
            expect(role).to_have_value('manager')
            role.select_option('staff')
            expect(dashboard.locator('.team-row small',has_text='staff')).to_be_visible()
            assert member.request.post(f'/api/admin/{slug}/products', headers=member_csrf,
                                       data={'name':'Denied item','price_cents':100}).status == 403
            for page in (phone,dashboard):
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            dashboard.on('dialog',lambda dialog:dialog.accept())
            dashboard.locator('[data-revoke-member]').click()
            expect(dashboard.locator('[data-member-role]')).to_have_count(0)
            assert member.request.get('/api/admin/'+slug).status == 404
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="requests"]').click()
            expect(dashboard.locator('.request-card',has_text='guest@example.invalid')).to_have_count(1)
            assert not errors, errors
        finally:
            browser.close()
