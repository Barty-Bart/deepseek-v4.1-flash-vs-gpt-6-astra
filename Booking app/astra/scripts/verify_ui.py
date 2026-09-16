"""One focused Chromium pass. Mutations use an isolated temporary database."""
import json
import os
from datetime import datetime
from pathlib import Path
import sys
import tempfile
from threading import Thread

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from db import get_db
from scheduling import TZ
from seed import ADMIN_PASSWORD, seed_database

REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True)
PREVIEW = f"http://127.0.0.1:{os.environ.get('PORT', '5181')}"
report = {'preview': PREVIEW, 'browser': 'Chromium', 'checks': [], 'javascript_errors': [], 'server_errors': [], 'screenshots': []}


def check(name):
    report['checks'].append(name)
    print('PASS ' + name, flush=True)


def screenshot(page, name):
    page.screenshot(path=str(REPORTS / name), full_page=True)
    report['screenshots'].append(name)


def watch(page):
    page.on('pageerror', lambda error: report['javascript_errors'].append(str(error)))
    page.on('response', lambda response: report['server_errors'].append(response.url) if response.status >= 500 else None)


def no_overflow(page):
    if not page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'):
        offenders = page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => {
            const r = e.getBoundingClientRect(); return r.right > innerWidth + 1 && getComputedStyle(e).position !== 'absolute';
        }).map(e => ({tag: e.tagName, class: e.className, width: Math.round(e.getBoundingClientRect().width)})).slice(0, 15)""")
        screenshot(page, 'overflow-inspection.png')
        raise AssertionError('Page overflows horizontally: ' + json.dumps(offenders))


try:
    with tempfile.TemporaryDirectory(prefix='ui-test-', dir=ROOT / '.local') as temp:
        app = create_app({'TESTING': True, 'DATABASE': str(Path(temp) / 'ui.sqlite3'), 'SECRET_KEY': 'isolated-ui-test',
                          'NOW': lambda: datetime(2026, 9, 15, 8, tzinfo=TZ)})
        with app.app_context():
            seed_database(get_db(), app.config['NOW']())
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                desktop = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
                page = desktop.new_page()
                watch(page)
                page.goto(PREVIEW, wait_until='networkidle')
                expect(page.get_by_role('heading', name='Your next good hair day.')).to_be_visible()
                no_overflow(page)
                screenshot(page, 'desktop-booking.png')
                page.keyboard.press('Tab')
                expect(page.get_by_role('link', name='Skip to content')).to_be_focused()
                assert page.get_by_role('link', name='Skip to content').evaluate("element => getComputedStyle(element).outlineStyle") != 'none'
                check('Live preview renders at 1440×1000 with keyboard skip link and visible focus')

                mobile = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
                mobile_page = mobile.new_page()
                watch(mobile_page)
                mobile_page.goto(PREVIEW, wait_until='networkidle')
                no_overflow(mobile_page)
                screenshot(mobile_page, 'mobile-booking.png')
                assert mobile_page.locator('.time-option span').first.bounding_box()['height'] >= 44
                check('Live preview renders at 390×844 without page overflow; time controls have 44px targets')

                page.goto(base, wait_until='networkidle')
                page.locator('input[name="service"][value="3"]').check(force=True)
                expect(page.locator('#summary-service')).to_have_text('Cut and Beard')
                expect(page.locator('#time-slots input').first).to_have_count(1)
                page.locator('input[name="staff"][value="2"]').check(force=True)
                expect(page.locator('#summary-barber')).to_have_text('Jordan')
                expect(page.locator('#time-slots input').first).to_have_count(1)
                assert page.locator('#summary-total').inner_text() == '$65'
                assert page.locator('#time-slots input[value="09:00"]').count() == 0
                assert page.locator('#time-slots input[value="16:30"]').count() == 0
                page.locator('#time-slots input[value="10:00"]').check(force=True)
                page.get_by_label('Full name', exact=True).fill('Morgan Demo')
                page.get_by_label('Email address', exact=True).fill('morgan@example.com')
                page.get_by_role('button', name='Confirm my appointment').click()
                page.wait_for_url('**/booking/*')
                expect(page.get_by_role('heading', name='You’re in good hands.')).to_be_visible()
                expect(page.locator('.management-service')).to_contain_text('Cut and Beard')
                expect(page.locator('.management-service')).to_contain_text('45 minutes')
                expect(page.locator('.management-date')).to_contain_text('10:00 am–10:45 am')
                private_path = page.url.removeprefix(base)
                screenshot(page, 'desktop-confirmation.png')
                check('Customer can select service/barber/time and confirm; summary and stored duration agree')

                mobile_page.goto(base + private_path, wait_until='networkidle')
                no_overflow(mobile_page)
                screenshot(mobile_page, 'mobile-confirmation.png')
                mobile_page.get_by_text('Need to cancel your appointment?', exact=True).click()
                mobile_page.get_by_role('button', name='Yes, cancel my appointment').click()
                expect(mobile_page.get_by_role('heading', name='Until next time.')).to_be_visible()
                page.goto(base + '/?service=3&staff=2&date=2026-09-15', wait_until='networkidle')
                expect(page.locator('#time-slots input[value="10:00"]')).to_have_count(1)
                check('Private booking page renders on mobile; cancellation releases the selected slot')

                mobile_page.goto(base, wait_until='networkidle')
                mobile_page.locator('.date-chip[data-date="2026-09-16"]').click()
                expect(mobile_page.locator('#selected-date-label')).to_contain_text('16 September')
                expect(mobile_page.locator('#time-slots input').first).to_have_count(1)
                assert mobile_page.locator('#date-picker').input_value() == '2026-09-16'
                mobile_page.locator('#date-picker').fill('2026-09-20')
                mobile_page.locator('#date-picker').dispatch_event('change')
                expect(mobile_page.locator('#availability-message')).to_contain_text('closed on Sundays and Mondays')
                expect(mobile_page.locator('#book-button')).to_be_disabled()
                check('Mobile date rail and date picker refresh availability; closed days have a helpful empty state')

                page.goto(base + '/admin', wait_until='networkidle')
                assert page.url.endswith('/admin/login')
                screenshot(page, 'desktop-login.png')
                page.get_by_label('Username', exact=True).fill('admin')
                page.get_by_label('Password', exact=True).fill(ADMIN_PASSWORD)
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.get_by_role('heading', name='The appointment book.')).to_be_visible()
                page.get_by_label('Date', exact=True).first.fill('2026-09-16')
                page.get_by_role('button', name='View day').click()
                expect(page.locator('table')).to_contain_text('Sam Taylor')
                screenshot(page, 'desktop-admin.png')
                check('Admin requires sign in and shows seeded appointments for the chosen date')

                page.locator('#block-staff').select_option('1')
                page.locator('#block-start').fill('10:00')
                page.locator('#block-end').fill('10:30')
                page.locator('#block-reason').fill('Browser verification')
                page.get_by_role('button', name='Add unavailable period').click()
                expect(page.locator('.error-summary')).to_contain_text('Sam Taylor')
                expect(page.locator('.error-summary')).to_be_focused()
                page.locator('#block-start').fill('16:00')
                page.locator('#block-end').fill('16:30')
                page.get_by_role('button', name='Add unavailable period').click()
                expect(page.locator('.block-row').filter(has_text='Browser verification')).to_be_visible()
                page.locator('.block-row').filter(has_text='Browser verification').get_by_role('button', name='Remove', exact=False).click()
                expect(page.locator('.block-row').filter(has_text='Browser verification')).to_have_count(0)
                check('Admin receives a named overlap error and can create/remove a valid unavailable period')

                page.set_viewport_size({'width': 390, 'height': 844})
                no_overflow(page)
                screenshot(page, 'mobile-admin.png')
                if page.locator('.menu-toggle').is_visible():
                    page.get_by_role('button', name='Open menu', exact=True).click()
                page.get_by_role('button', name='Log out').click()
                page.goto(base + '/admin')
                assert page.url.endswith('/admin/login')
                check('Admin layout fits mobile width with a scrollable table; logout revokes access')

                nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
                nojs_page = nojs.new_page()
                watch(nojs_page)
                nojs_page.goto(base, wait_until='networkidle')
                nojs_page.locator('input[name="service"][value="2"]').check(force=True)
                nojs_page.locator('input[name="staff"][value="2"]').check(force=True)
                nojs_page.get_by_role('button', name='Update available times').click()
                nojs_page.wait_for_load_state('networkidle')
                assert '?' not in nojs_page.url
                assert nojs_page.locator('#time-slots input[value="16:45"]').count() == 1
                nojs_page.locator('#time-slots input[value="10:00"]').check(force=True)
                nojs_page.get_by_label('Full name', exact=True).fill('No JavaScript Customer')
                nojs_page.get_by_label('Email address', exact=True).fill('nojs@example.com')
                nojs_page.get_by_role('button', name='Confirm my appointment').click(no_wait_after=True)
                nojs_page.wait_for_url('**/booking/*', timeout=15000)
                expect(nojs_page.get_by_role('heading', name='You’re in good hands.')).to_be_visible()
                check('Complete booking works with JavaScript disabled; refreshing times keeps details out of URLs')

                assert not report['javascript_errors'], report['javascript_errors']
                assert not report['server_errors'], report['server_errors']
                check('No uncaught JavaScript errors or HTTP 5xx responses during the pass')
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
    report['result'] = 'passed'
except Exception as error:
    report['result'] = 'failed'
    report['failure'] = str(error)
    raise
finally:
    (REPORTS / 'browser-verification.json').write_text(json.dumps(report, indent=2) + '\n')
