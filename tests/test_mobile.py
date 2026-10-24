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
            expect(phone.locator('#receiptState')).to_have_text('New')
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
            expect(phone.locator('#receiptState')).to_have_text('Done', timeout=12000)
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
            phone.locator('#questionDetails summary').click()
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
            dashboard.locator('[data-lead-id]').select_option('qualified')
            expect(dashboard.locator('[data-lead-id]')).to_have_value('qualified')
            dashboard.locator('#requestLead').select_option('qualified')
            dashboard.locator('#requestSearchForm button[type="submit"]').click()
            expect(dashboard.locator('.request-card')).to_have_count(1)
            dashboard.locator('#requestLead').select_option('closed')
            dashboard.locator('#requestSearchForm button[type="submit"]').click()
            expect(dashboard.locator('.request-card')).to_have_count(0)
            dashboard.locator('#clearRequestFilters').click()
            expect(dashboard.locator('.request-card')).to_have_count(3)
            assert dashboard.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors, errors
        finally:
            browser.close()


@pytest.mark.parametrize('width',[320,768])
def test_full_history_catalog_quantity_and_invite_revocation(local_site,width,tmp_path):
    import sqlite3
    from playwright.sync_api import sync_playwright,expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            owner=browser.new_context(viewport={'width':width,'height':844},reduced_motion='reduce',base_url=local_site)
            guest=browser.new_context(viewport={'width':width,'height':844},reduced_motion='reduce',base_url=local_site)
            result=owner.request.post('/api/auth/signup',data={'email':'history-browser@example.invalid','password':'SyntheticBrowserFixture123!','name':'Sample catalog studio','industry':'auto'})
            assert result.ok
            slug=result.json()['slug'];csrf={'x-scene-csrf':owner.request.get('/api/me').json()['csrf']}
            board=owner.request.get('/api/admin/'+slug).json();token=board['stations'][0]['token']
            for name,category in [('Sample wax','Detailing'),('Sample seats','Care')]+[(f'Example item {i}','Detailing') for i in range(5)]:
                assert owner.request.post(f'/api/admin/{slug}/products',headers=csrf,data={'name':name,'category':category,'price_cents':125}).ok
            # Synthetic history seeded only in this test's disposable SQLite DB.
            with sqlite3.connect(tmp_path/'browser.sqlite') as c:
                for i in range(31):
                    c.execute('INSERT INTO requests(business_id,station_id,kind,message,status,receipt_hash,client_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                              (board['id'],board['stations'][0]['id'],'question' if i==0 else 'service','Oldest synthetic inquiry' if i==0 else f'Archive {i}','completed','fixture-only',f'browser-history-fixture-{i}',1,1))
            phone,dashboard=guest.new_page(),owner.new_page()
            errors=[]
            for page in (phone,dashboard):page.on('pageerror',lambda error:errors.append(str(error)))
            phone.goto('/?q='+token)
            phone.locator('#questionDetails summary').click()
            phone.locator('#guestNote').fill('Please keep this draft')
            phone.locator('#guestContact').fill('sample@example.invalid')
            phone.locator('#guestConsent').check()
            phone.locator('#guestSearch').fill('wax')
            expect(phone.locator('.guest-product:visible')).to_have_count(1)
            phone.locator('[data-add]:visible').click()
            expect(phone.locator('#guestNote')).to_have_value('Please keep this draft')
            expect(phone.locator('#guestConsent')).to_be_checked()
            phone.get_by_role('button',name='Increase Sample wax quantity').click()
            expect(phone.locator('.cart-line')).to_contain_text('2 × Sample wax')
            phone.locator('#guestSearch').fill('')
            phone.get_by_role('button',name='Care',exact=True).click()
            expect(phone.locator('.guest-product:visible')).to_have_count(1)
            expect(phone.locator('.guest-product:visible')).to_contain_text('Sample seats')
            phone.locator('[data-send-cart]').click()
            expect(phone.locator('[data-receipt-id]')).to_have_count(1)
            expect(phone.locator('#guestNote')).to_have_value('Please keep this draft')
            request=owner.request.get('/api/admin/'+slug).json()['requests'][0]
            assert 'Quantity 2' in request['message']
            dashboard.goto('/')
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="requests"]').click()
            expect(dashboard.locator('.request-card')).to_have_count(25)
            dashboard.locator('#nextRequests').click()
            expect(dashboard.locator('.request-card')).to_have_count(7)
            expect(dashboard.locator('.request-list')).to_contain_text('Oldest synthetic inquiry')
            dashboard.locator('#previousRequests').click()
            expect(dashboard.locator('.request-card')).to_have_count(25)
            dashboard.locator('#requestSearch').fill('oldest')
            dashboard.locator('#requestKind').select_option('question')
            dashboard.locator('#requestSearchForm button[type="submit"]').click()
            expect(dashboard.locator('.request-card')).to_have_count(1)
            expect(dashboard.locator('.request-list')).to_contain_text('Oldest synthetic inquiry')
            expect(dashboard.locator('#nextRequests')).to_be_disabled()
            dashboard.locator('#requestSearch').fill('Unsubmitted draft filter')
            dashboard.locator('#clearRequestFilters').click()
            expect(dashboard.locator('#requestSearch')).to_have_value('')
            expect(dashboard.locator('#requestKind')).to_have_value('')
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="team"]').click()
            dashboard.locator('#inviteForm button[type="submit"]').click()
            expect(dashboard.locator('[data-revoke-invite]')).to_have_count(1)
            dashboard.locator('[data-revoke-invite]').click()
            expect(dashboard.locator('[data-revoke-invite]')).to_have_count(0)
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="settings"]').click()
            save=dashboard.locator('#settingsForm button[type="submit"]')
            with dashboard.expect_response(lambda response:response.request.method=='PATCH' and response.url.endswith('/settings')):
                save.click()
            expect(save).to_be_enabled()
            for page in (dashboard,phone):
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors,errors
            dashboard.screenshot(path=str(tmp_path/f'team-{width}.png'),full_page=True)
            phone.screenshot(path=str(tmp_path/f'catalog-{width}.png'),full_page=True)
        finally:
            browser.close()


@pytest.mark.parametrize('width',[320,768])
def test_catalog_edit_station_pause_and_selection_notes(local_site,width):
    from playwright.sync_api import sync_playwright,expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            owner=browser.new_context(viewport={'width':width,'height':844},reduced_motion='reduce',base_url=local_site)
            guest=browser.new_context(viewport={'width':width,'height':844},reduced_motion='reduce',base_url=local_site)
            registered=owner.request.post('/api/auth/signup',data={'email':'operations-browser@example.invalid','password':'SyntheticOperationsPass123!','name':'Sample operations studio','industry':'auto'})
            assert registered.ok
            slug=registered.json()['slug'];board=owner.request.get('/api/admin/'+slug).json()
            station=board['stations'][0];token=station['token']
            dashboard,phone=owner.new_page(),guest.new_page()
            errors=[]
            for page in (dashboard,phone):page.on('pageerror',lambda error:errors.append(str(error)))
            dashboard.goto('/')
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="catalog"]').click()
            dashboard.locator('#prodName').fill('Synthetic original service')
            dashboard.locator('#prodPrice').fill('10.50')
            dashboard.locator('#productForm button[type="submit"]').click()
            expect(dashboard.locator('.catalog-row')).to_contain_text('Synthetic original service')
            phone.goto('/?q='+token)
            phone.locator('[data-add]').click()
            phone.get_by_role('button',name='Increase Synthetic original service quantity').click()
            phone.locator('#cartNote').fill('Synthetic guest preference')
            # Notes survive quantity renders and stay out of receipt persistence.
            phone.get_by_role('button',name='Increase Synthetic original service quantity').click()
            expect(phone.locator('#cartNote')).to_have_value('Synthetic guest preference')
            phone.get_by_role('button',name='Decrease Synthetic original service quantity').click()
            phone.locator('[data-send-cart]').click()
            expect(phone.locator('[data-receipt-id]')).to_have_count(1)
            assert phone.evaluate("!Object.values(sessionStorage).some(value=>value.includes('Synthetic guest preference'))")
            dashboard.locator('[data-edit-product]').click()
            expect(dashboard.locator('#prodName')).to_be_focused()
            dashboard.locator('#cancelProductEdit').click()
            expect(dashboard.locator('[data-edit-product]')).to_be_focused()
            dashboard.locator('[data-edit-product]').click()
            dashboard.locator('#prodName').fill('Synthetic updated service')
            dashboard.locator('#prodName').press('Tab')
            expect(dashboard.locator('#prodDesc')).to_be_focused()
            dashboard.locator('#prodPrice').fill('20.00')
            dashboard.locator('#productForm button[type="submit"]').click()
            expect(dashboard.locator('.catalog-row')).to_contain_text('Synthetic updated service')
            saved=owner.request.get('/api/admin/'+slug).json()['requests'][0]
            assert (saved['product_name'],saved['unit_price_cents'],saved['quantity'])==('Synthetic original service',1050,2)
            assert 'Synthetic guest preference' in saved['message']
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="stations"]').click()
            settings=dashboard.locator(f'[data-station-form="{station["id"]}"]')
            station_card=dashboard.locator('.qr-card').filter(has=settings)
            settings.locator('[name="label"]').fill('Renamed synthetic reception')
            settings.locator('[name="active"]').uncheck()
            settings.get_by_role('button',name='Save location').click()
            expect(station_card.locator('.qr-paused')).to_be_visible()
            assert owner.request.get('/api/admin/'+slug).json()['stations'][0]['token']==token
            phone.reload()
            expect(phone.locator('.loading-phone')).to_contain_text('QR location is unavailable')
            settings.locator('[name="active"]').check()
            settings.get_by_role('button',name='Save location').click()
            expect(station_card.locator('.qr-image')).to_be_visible()
            phone.reload()
            expect(phone.locator('.guest-spot')).to_contain_text('Renamed synthetic reception')
            expect(phone.locator('.guest-product')).to_contain_text('Synthetic updated service')
            expect(phone.locator('[data-receipt-id]')).to_have_count(1)
            dashboard.locator('#mobileMenu').click()
            dashboard.locator('#mainNav [data-screen="analytics"]').click()
            expect(dashboard.get_by_role('heading',name='Inquiry stages')).to_be_visible()
            panel=dashboard.locator('.panel').filter(has=dashboard.get_by_role('heading',name='Catalog requests'))
            expect(panel).to_contain_text('Known requested units')
            expect(panel.locator('.analytics-count').filter(has_text='Known requested units')).to_contain_text('2')
            for page in (dashboard,phone):
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors,errors
        finally:
            browser.close()


def test_founder_browser_signup_lost_response_and_refresh(local_site, tmp_path):
    """Synthetic owner signup via UI and committed-but-lost guest POST response."""
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            owner = browser.new_context(viewport={'width': 390, 'height': 844},
                                        reduced_motion='reduce', base_url=local_site)
            guest = browser.new_context(viewport={'width': 390, 'height': 844},
                                        reduced_motion='reduce', base_url=local_site)
            dashboard = owner.new_page()
            dashboard.goto('/')
            dashboard.get_by_role('button', name='Start building').click()
            dashboard.locator('#authBusiness').fill('Synthetic Founder Browser Studio')
            dashboard.locator('#authIndustry').select_option('auto')
            dashboard.locator('#authEmail').fill('founder-browser@example.invalid')
            dashboard.locator('#authPassword').fill('SyntheticFounderBrowser123!')
            dashboard.locator('#authSubmit').click()
            expect(dashboard.locator('#appShell')).to_be_visible()
            slug = owner.request.get('/api/me').json()['businesses'][0]['slug']
            board = owner.request.get('/api/admin/' + slug).json()
            token = board['stations'][0]['token']
            phone = guest.new_page()
            phone.goto('/q/' + token)
            expect(phone.locator('.guest-spot')).to_contain_text('Front Desk')

            # Commit the POST on the actual local server, then lose its response.
            def lose_response(route):
                response = route.fetch()
                assert response.ok
                route.abort('failed')
            phone.route('**/api/q/*/requests', lose_response)
            phone.locator('[data-kind="service"]').click()
            expect(phone.get_by_role('alert')).to_contain_text('Delivery is uncertain')
            assert owner.request.get('/api/admin/' + slug).json()['analytics']['total'] == 1
            phone.locator('[data-kind="service"]').click()
            assert owner.request.get('/api/admin/' + slug).json()['analytics']['total'] == 1
            phone.unroute('**/api/q/*/requests', lose_response)
            phone.reload()
            expect(phone.get_by_role('alert')).to_contain_text('Ask staff to check')
            phone.locator('[data-kind="service"]').click()
            assert owner.request.get('/api/admin/' + slug).json()['analytics']['total'] == 1

            # Recovery is an explicit staff check, never an automatic resend.
            phone.on('dialog', lambda dialog: dialog.accept())
            phone.locator('#resolveUncertain').click()
            expect(phone.locator('#resolveUncertain')).to_have_count(0)
            phone.locator('#questionDetails summary').click()
            phone.locator('#guestNote').fill('Synthetic follow-up after staff check')
            phone.locator('#guestMessageForm button[type="submit"]').click()
            expect(phone.locator('[data-receipt-id]')).to_have_count(1)
            phone.reload()
            expect(phone.locator('[data-receipt-id]')).to_have_count(1)
            assert owner.request.get('/api/admin/' + slug).json()['analytics']['total'] == 2
            dashboard.reload()
            expect(dashboard.locator('#appShell')).to_be_visible()
            assert guest.request.get('/api/admin/' + slug).status == 401
            assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth')
            phone.screenshot(path=str(tmp_path / 'founder-recovery-phone.png'), full_page=True)
        finally:
            browser.close()
