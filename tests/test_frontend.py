"""Guest scan -> private receipt -> staff starts and completes -> refreshed guest sees Done.

Opt in with SCENE_BROWSER_TESTS=1; uses only an isolated local SQLite demo.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import pytest

pytestmark=pytest.mark.skipif(os.getenv('SCENE_BROWSER_TESTS')!='1',reason='Set SCENE_BROWSER_TESTS=1')

@pytest.fixture(scope='module')
def frontend_server(tmp_path_factory):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    env={**os.environ,'SCENE_ENV':'development','SCENE_AUTH_MODE':'local','SCENE_DEMO':'1',
         'SCENE_DATABASE_URL':'','SCENE_DB':str(tmp_path_factory.mktemp('signage')/'test.db'),
         'SCENE_PUBLIC_URL':base,'SCENE_SECURE_COOKIE':'0','SCENE_TRUSTED_HOSTS':'',
         'SCENE_REQUIRE_SUBSCRIPTION':'0','SCENE_REQUIRE_GUEST_SESSION':'0'}
    process=subprocess.Popen([sys.executable,'-m','uvicorn','server:app','--host','127.0.0.1','--port',str(port),'--workers','1'],env=env,cwd=Path(__file__).resolve().parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if process.poll() is not None:pytest.fail('Local frontend server exited')
            try:
                with urllib.request.urlopen(base+'/healthz',timeout=1) as r:
                    if r.status==200:break
            except Exception:time.sleep(.1)
        else:pytest.fail('Local frontend server did not become healthy')
        yield base
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()

@pytest.mark.parametrize('width',[320,375,390])
def test_scan_request_receipt_staff_complete(frontend_server,width):
    from playwright.sync_api import sync_playwright,expect
    base=frontend_server
    with urllib.request.urlopen(base+'/api/demo/trio-demo') as r:token=json.load(r)['q']
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            guest=browser.new_context(viewport={'width':width,'height':800},reduced_motion='reduce').new_page()
            guest.goto(base+'/?q='+token)
            guest.get_by_role('button',name='Call server',exact=True).click()
            expect(guest.locator('#rcpt')).to_contain_text('Call server')
            expect(guest.locator('#rcpt')).to_contain_text('New')
            guest.reload()
            expect(guest.locator('#rcpt')).to_contain_text('Call server')
            assert guest.evaluate('document.documentElement.scrollWidth<=innerWidth')
            staff=browser.new_context(viewport={'width':1280,'height':800},reduced_motion='reduce').new_page()
            staff.goto(base)
            staff.get_by_role('button',name='Sign in',exact=True).click()
            staff.get_by_label('Email',exact=True).fill('demo@scene.local')
            staff.get_by_label('Password',exact=True).fill('SceneDemo2026!')
            staff.locator('#authSubmit').click()
            ticket=staff.locator('.request-card',has_text='Call server').filter(has=staff.locator('[data-next-status="in_progress"]')).first
            ticket.get_by_role('button',name='Start',exact=False).click()
            staff.locator('.request-card',has_text='Call server').filter(has=staff.locator('[data-next-status="completed"]')).first.get_by_role('button',name='Mark done',exact=False).click()
            expect(guest.locator('#rcpt')).to_contain_text('Done',timeout=15000)
        finally:browser.close()


def test_email_callbacks_clear_sensitive_fragments(frontend_server):
    from playwright.sync_api import sync_playwright,expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_context(reduced_motion='reduce').new_page()
            page.goto(frontend_server+'/#access_token=synthetic-invalid&type=signup')
            expect(page).to_have_url(frontend_server+'/auth/confirm')
            expect(page.locator('#status')).to_contain_text('Sign in to continue')
            expect(page.locator('#verify-form')).to_be_hidden()
            page.goto(frontend_server+'/#access_token=synthetic-invalid&type=recovery')
            expect(page).to_have_url(frontend_server+'/auth/confirm')
            expect(page.locator('#password-form')).to_be_visible()
            assert page.evaluate('location.hash')==''
        finally:browser.close()


def test_recovery_and_onboarding_modes_survive_reload(frontend_server):
    from playwright.sync_api import sync_playwright,expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_context(reduced_motion='reduce').new_page()
            for mode,selector in [('recover','#recover-form'),('onboard','#onboard-form')]:
                page.goto(frontend_server+'/auth/confirm?'+mode+'=1')
                expect(page.locator(selector)).to_be_visible()
                page.reload()
                expect(page.locator(selector)).to_be_visible()
        finally:browser.close()
