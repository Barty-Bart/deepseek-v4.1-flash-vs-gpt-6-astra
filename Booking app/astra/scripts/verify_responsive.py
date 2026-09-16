"""Responsive update checks. All booking/admin mutations use a temporary database."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
from threading import Thread
from time import monotonic

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from db import get_db
from scheduling import TZ
from seed import ADMIN_PASSWORD, seed_database
from scripts.verify_operation import snapshot

REPORTS = ROOT / 'reports' / 'responsive-update'
REPORTS.mkdir(exist_ok=True)
started = monotonic()
report = {'started_at': datetime.now(timezone.utc).isoformat(), 'checks': [], 'screenshots': [], 'picker_calls': [], 'page_errors': [], 'server_errors': [], 'block_responses': []}
PREVIEW = f"http://127.0.0.1:{os.environ.get('PORT', '5181')}"


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def check(name):
    report['checks'].append(name)
    print('PASS ' + name, flush=True)


def capture(page, name):
    modal_open = page.locator('#field-picker').is_visible()
    if not modal_open:
        page.evaluate("() => { document.activeElement?.blur(); window.scrollTo({top: 0, behavior: 'instant'}); }")
        settle(page)
    page.screenshot(path=str(REPORTS / (name + '.png')), full_page=not modal_open)
    report['screenshots'].append(name + '.png')


def watch(page):
    page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
    page.on('response', lambda response: report['server_errors'].append(response.url) if response.status >= 500 else None)
    page.on('response', lambda response: report['block_responses'].append(response.status) if response.request.method == 'POST' and response.url.endswith('/admin/blocks') else None)


def layout(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal page overflow'


def settle(page):
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def visible_below_header(page, selector):
    settle(page)
    bounds = page.locator(selector).bounding_box()
    header = page.locator('.site-header').bounding_box()
    assert bounds and header
    assert bounds['y'] >= header['y'] + header['height'] - 1, f'{selector} covered by header: {bounds}, {header}'


def header_and_menu(page, mobile):
    page.evaluate("window.scrollTo({ top: 550, behavior: 'instant' })")
    settle(page)
    assert abs(page.locator('.site-header').bounding_box()['y']) < 1
    page.locator('#email').focus()
    visible_below_header(page, '#email')
    # Reproduce reverse tab focus on a control currently hidden by the header.
    page.locator('#name').evaluate("e => window.scrollTo({top: scrollY + e.getBoundingClientRect().top - 15, behavior: 'instant'})")
    page.locator('#name').focus()
    visible_below_header(page, '#name')
    if mobile:
        toggle = page.get_by_role('button', name='Open menu', exact=True)
        toggle.click()
        expect(page.locator('#primary-navigation')).to_be_visible()
        expect(page.get_by_role('button', name='Close menu', exact=True)).to_have_attribute('aria-expanded', 'true')
        page.keyboard.press('Tab')
        expect(page.locator('#primary-navigation a').first).to_be_focused()
        page.keyboard.press('Escape')
        expect(toggle).to_be_focused()
        expect(page.locator('#primary-navigation')).to_be_hidden()
        page.keyboard.press('Enter')
        expect(page.locator('#primary-navigation')).to_be_visible()
        page.locator('#primary-navigation .nav-book').click()
        expect(page.locator('#primary-navigation')).to_be_hidden()
        visible_below_header(page, '#booking')
        toggle.click()
        page.locator('#name').focus()
        expect(page.locator('#primary-navigation')).to_be_hidden()
        toggle.click()
        page.locator('.page-intro h1').click()
        expect(page.locator('#primary-navigation')).to_be_hidden()
        toggle.click()
        page.set_viewport_size({'width': 1440, 'height': 1000})
        expect(toggle).to_be_hidden()
        expect(page.locator('#primary-navigation')).to_be_visible()
        expect(page.locator('.menu-toggle')).to_have_attribute('aria-expanded', 'false')
    else:
        expect(page.locator('.menu-toggle')).to_be_hidden()
        page.locator('.nav-book').click()
        visible_below_header(page, '#booking')


PICKER_SPY = """(() => {
  window.nativePickerCalls = [];
  const native = HTMLInputElement.prototype.showPicker;
  window.nativePickerAvailable = typeof native === 'function';
  if (native) HTMLInputElement.prototype.showPicker = function() {
    const call = {id: this.id, type: this.type, activation: navigator.userActivation ? navigator.userActivation.isActive : null};
    window.nativePickerCalls.push(call);
    try { const result = native.call(this); call.result = 'returned'; return result; }
    catch (error) { call.result = error.name; throw error; }
  };
})()"""


def native_field(page, selector, mobile, tag):
    field = page.locator(selector)
    field.scroll_into_view_if_needed()
    settle(page)
    # Test value area, middle, and right padding, not just an icon.
    for position in ('left', 'middle', 'right'):
        box = field.bounding_box()
        x = {'left': 12, 'middle': box['width'] / 2, 'right': box['width'] - 12}[position]
        before = page.evaluate('window.nativePickerCalls.length')
        if mobile:
            field.tap(position={'x': x, 'y': box['height'] / 2})
        else:
            field.click(position={'x': x, 'y': box['height'] / 2}, no_wait_after=True)
        calls = page.evaluate('window.nativePickerCalls')
        if page.locator('#field-picker').is_visible() and len(calls) == before:
            report['picker_calls'].append({'id': selector, 'case': tag, 'position': position, 'result': 'direct accessible fallback'})
        elif page.evaluate('window.nativePickerAvailable'):
            assert len(calls) == before + 1, f'No whole-field native call: {selector}, {position}'
            assert calls[-1]['activation'] is not False
            report['picker_calls'].append({**calls[-1], 'case': tag, 'position': position})
            if calls[-1]['result'] != 'returned':
                expect(page.locator('#field-picker')).to_be_visible()
        else:
            expect(page.locator('#field-picker')).to_be_visible()
            report['picker_calls'].append({'id': selector, 'case': tag, 'position': position, 'result': 'automatic fallback'})
        page.keyboard.press('Escape')
        expect(page.locator('#field-picker')).to_be_hidden()
    before = page.evaluate('window.nativePickerCalls.length')
    field.evaluate('element => element.blur()')
    field.focus()
    assert page.evaluate('window.nativePickerCalls.length') == before, 'Tab/focus should not force a picker'
    visible_below_header(page, selector)


def choose_date(page, field_id, value):
    page.locator(f'[data-picker-for="{field_id}"]').click()
    expect(page.locator('#field-picker')).to_be_visible()
    page.locator(f'.picker-days button[data-date="{value}"]').click()
    expect(page.locator('#field-picker')).to_be_hidden()
    assert page.locator('#' + field_id).input_value() == value
    settle(page)


def choose_time(page, field_id, value):
    page.locator(f'[data-picker-for="{field_id}"]').click()
    expect(page.locator('#field-picker')).to_be_visible()
    page.locator(f'.picker-times button[data-time="{value}"]').click()
    expect(page.locator('#field-picker')).to_be_hidden()
    assert page.locator('#' + field_id).input_value() == value
    settle(page)


def select_radio(page, name, value):
    control = page.locator(f'input[name="{name}"][value="{value}"]')
    # Activate the visible label that users tap, not a forced click on the
    # visually hidden one-pixel radio underneath a sticky header.
    control.locator('..').click()
    expect(control).to_be_checked()


def login(page, base, mobile):
    page.goto(base + '/admin/login')
    page.get_by_label('Username', exact=True).fill('admin')
    page.get_by_label('Password', exact=True).fill(ADMIN_PASSWORD)
    page.get_by_role('button', name='Sign in', exact=True).click()
    expect(page.get_by_role('heading', name='The appointment book.')).to_be_visible()


def journey(browser, engine, width, height, base):
    mobile = width < 760
    tag = f'{engine}-{width}x{height}'
    context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=mobile, has_touch=mobile, reduced_motion='reduce')
    context.add_init_script(PICKER_SPY)
    page = context.new_page(); watch(page)
    try:
        page.goto(base, wait_until='networkidle')
        layout(page)
        if engine == 'chromium': capture(page, tag + '-booking')
        header_and_menu(page, mobile)
        page.set_viewport_size({'width': width, 'height': height})
        if mobile:
            expect(page.locator('#primary-navigation')).to_be_hidden()
            for selector in ('.menu-toggle', '.service-card', '.barber-card', '.time-option span', '#date-picker'):
                assert page.locator(selector).first.bounding_box()['height'] >= 44
            if engine == 'chromium':
                page.get_by_role('button', name='Open menu', exact=True).click()
                capture(page, tag + '-menu')
                page.get_by_role('button', name='Close menu', exact=True).click()
        check(tag + ': sticky header, anchors, focus, accessible menu and thumb targets')

        native_field(page, '#date-picker', mobile, tag)
        page.locator('[data-picker-for="date-picker"]').click()
        expect(page.locator('.picker-days button[data-date="2026-09-14"]')).to_be_disabled()
        expect(page.locator('.picker-days button[data-date="2026-09-20"]')).to_be_disabled()
        page.locator('.picker-days button[data-date="2026-09-15"]').focus()
        page.keyboard.press('ArrowRight')
        expect(page.locator('.picker-days button[data-date="2026-09-16"]')).to_be_focused()
        if engine == 'chromium' and mobile: capture(page, tag + '-calendar')
        page.keyboard.press('Escape')
        expect(page.locator('#date-picker')).to_be_focused()
        choose_date(page, 'date-picker', '2026-09-15')
        expect(page.locator('#time-slots input').first).to_have_count(1)
        select_radio(page, 'service', '3')
        expect(page.locator('#summary-service')).to_have_text('Cut and Beard')
        select_radio(page, 'staff', '2')
        expect(page.locator('#summary-barber')).to_have_text('Jordan')
        expect(page.locator('#time-slots input[value="10:00"]')).to_have_count(1)
        assert page.locator('input[type="time"]').count() == 0
        assert page.locator('#time-slots input[value="09:00"]').count() == 0
        select_radio(page, 'slot', '10:00')
        page.get_by_label('Full name', exact=True).fill('Phone Check Customer')
        page.get_by_label('Email address', exact=True).fill('phone-check@example.com')

        rival = context.new_page(); watch(rival)
        rival.goto(base + '/?service=3&staff=2&date=2026-09-15')
        select_radio(rival, 'slot', '10:00')
        rival.get_by_label('Full name', exact=True).fill('Stale Page Customer')
        rival.get_by_label('Email address', exact=True).fill('stale-page@example.com')
        page.get_by_role('button', name='Confirm my appointment').click()
        page.wait_for_url('**/booking/*')
        private_url = page.url
        expect(page.locator('.management-date')).to_contain_text('10:00 am–10:45 am')
        layout(page)
        if engine == 'chromium': capture(page, tag + '-confirmation')
        with rival.expect_response(lambda response: response.url.endswith('/book')) as conflict:
            rival.get_by_role('button', name='Confirm my appointment').click()
        assert conflict.value.status == 409
        expect(rival.locator('.error-summary')).to_contain_text('just been booked')
        expect(rival.locator('.error-summary')).to_be_focused()
        visible_below_header(rival, '.error-summary')
        expect(rival.locator('#time-slots input[value="10:00"]')).to_have_count(0)
        assert rival.locator('#name').input_value() == 'Stale Page Customer'
        layout(rival)
        rival.close()
        page.get_by_text('Need to cancel your appointment?', exact=True).click()
        page.get_by_role('button', name='Yes, cancel my appointment').focus()
        visible_below_header(page, '.cancel-details .button')
        page.get_by_role('button', name='Yes, cancel my appointment').click()
        expect(page.get_by_role('heading', name='Until next time.')).to_be_visible()
        layout(page)
        if engine == 'chromium' and mobile: capture(page, tag + '-cancelled')
        released = context.request.get(base + '/api/availability?service=3&staff=2&date=2026-09-15').json()
        assert '10:00' in [slot['value'] for slot in released['slots']]
        check(tag + ': booking, stale-slot conflict, private cancellation and released availability')

        page.goto(base + '/admin/login')
        layout(page)
        if engine == 'chromium': capture(page, tag + '-login')
        login(page, base, mobile)
        for selector in ('#filter-date', '#block-date', '#block-start', '#block-end'):
            native_field(page, selector, mobile, tag)
        page.locator('#filter-date').fill('2026-09-16')
        assert page.locator('#filter-date').input_value() == '2026-09-16'
        if engine == 'chromium':
            # Exercise the actual native segmented editor without clicking/opening it.
            page.locator('#filter-date').focus()
            page.keyboard.press('ArrowUp')
            assert page.locator('#filter-date').input_value() != '2026-09-16'
            page.locator('#filter-date').fill('2026-09-16')
        page.get_by_role('button', name='View day').click()
        expect(page.locator('.appointments-table')).to_contain_text('Sam Taylor')
        page.locator('#block-reason').focus()
        visible_below_header(page, '#block-reason')
        layout(page)
        if engine == 'chromium': capture(page, tag + '-admin')
        if mobile:
            for row in page.locator('.booking-row').all():
                assert row.bounding_box()['width'] <= width - 36
            assert page.locator('.action-cell button').first.bounding_box()['height'] >= 44
            assert page.locator('.block-row button').first.bounding_box()['height'] >= 44
        page.locator('#block-staff').select_option('2')
        page.locator('[data-picker-for="block-start"]').click()
        expect(page.locator('.picker-times button[data-time="09:00"]')).to_have_count(0)
        page.keyboard.press('Escape')
        page.locator('#block-staff').select_option('1')
        choose_date(page, 'block-date', '2026-09-16')
        choose_time(page, 'block-start', '10:00')
        choose_time(page, 'block-end', '10:30')
        page.locator('#block-reason').fill('Responsive verification')
        page.get_by_role('button', name='Add unavailable period').click()
        expect(page.locator('.error-summary')).to_contain_text('Sam Taylor')
        visible_below_header(page, '.error-summary')
        layout(page)
        choose_time(page, 'block-start', '16:00')
        choose_time(page, 'block-end', '16:30')
        page.get_by_role('button', name='Add unavailable period').click()
        row = page.locator('.block-row').filter(has_text='Responsive verification')
        expect(row).to_be_visible()
        row.get_by_role('button').click()
        expect(page.locator('.block-row').filter(has_text='Responsive verification')).to_have_count(0)
        if mobile:
            page.get_by_role('button', name='Open menu', exact=True).click()
        page.get_by_role('button', name='Log out', exact=True).click()
        page.goto(base + '/admin')
        assert page.url.endswith('/admin/login')
        check(tag + ': all date/time fields, manual entry, responsive admin rows, block conflict/create/remove and logout')
    except Exception:
        report['failed_page'] = {'case': tag, 'url': page.url,
                                 'errors': page.locator('.error-summary').all_text_contents(),
                                 'form_values': page.locator('.block-form').evaluate_all("forms => forms.map(form => [...form.elements].filter(el => el.name && el.type !== 'hidden').map(el => ({name:el.name, value:el.value, valid:el.validity.valid})))")}
        page.screenshot(path=str(REPORTS / 'failure-viewport.png'))
        raise
    finally:
        context.close()


def fallback_checks(browser, engine, base, mode):
    context = browser.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True, reduced_motion='reduce')
    replacement = "undefined" if mode == 'missing' else "function() { throw new DOMException('Unavailable', 'NotAllowedError'); }"
    context.add_init_script(f"HTMLInputElement.prototype.showPicker = {replacement};")
    page = context.new_page(); watch(page)
    try:
        page.goto(base)
        page.locator('#date-picker').tap(position={'x': 15, 'y': 24})
        expect(page.locator('#field-picker')).to_be_visible()
        page.locator('.picker-days button[data-date="2026-09-16"]').click()
        assert page.locator('#date-picker').input_value() == '2026-09-16'
        expect(page.locator('#selected-date-label')).to_contain_text('16 September')
        expect(page.locator('#time-slots input').first).to_have_count(1)
        login(page, base, True)
        for field_id in ('filter-date', 'block-date'):
            page.locator('#' + field_id).tap(position={'x': 15, 'y': 24})
            expect(page.locator('#field-picker')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#' + field_id)).to_be_focused()
        for field_id in ('block-start', 'block-end'):
            page.locator('#' + field_id).tap(position={'x': 15, 'y': 24})
            expect(page.locator('#field-picker')).to_be_visible()
            page.locator('.picker-times button[data-time="14:15"]').click()
            assert page.locator('#' + field_id).input_value() == '14:15'
        layout(page)
        check(f'{engine}: all five fields automatically use selectable fallbacks when showPicker is {mode}')
    finally:
        context.close()


def no_script_journey(browser, base):
    context = browser.new_context(viewport={'width': 393, 'height': 852}, java_script_enabled=False, reduced_motion='reduce')
    page = context.new_page()
    try:
        page.goto(base, wait_until='networkidle')
        page.locator('#primary-navigation .nav-book').click()
        # Animation-frame callbacks do not run when script execution is disabled.
        booking_box = page.locator('#booking').bounding_box()
        header_box = page.locator('.site-header').bounding_box()
        assert booking_box['y'] >= header_box['y'] + header_box['height'] - 1
        layout(page)
        select_radio(page, 'service', '2')
        select_radio(page, 'staff', '2')
        page.get_by_role('button', name='Update available times').click()
        page.wait_for_load_state('networkidle')
        expect(page.locator('#time-slots input[value="16:45"]')).to_have_count(1)
        select_radio(page, 'slot', '10:00')
        page.locator('#name').fill('No Script Check')
        page.locator('#email').fill('no-script-check@example.com')
        page.get_by_role('button', name='Confirm my appointment').click(no_wait_after=True)
        page.wait_for_url('**/booking/*')
        expect(page.get_by_role('heading', name='You’re in good hands.')).to_be_visible()
        page.get_by_text('Need to cancel your appointment?', exact=True).click()
        page.get_by_role('button', name='Yes, cancel my appointment').click()
        expect(page.get_by_role('heading', name='Until next time.')).to_be_visible()
        check('JavaScript-disabled phone booking/cancellation and sticky-header anchor clearance remain functional')
    finally:
        context.close()


try:
    before = snapshot()
    with tempfile.TemporaryDirectory(prefix='responsive-test-', dir=ROOT / '.local') as temp:
        app = create_app({'TESTING': True, 'DATABASE': str(Path(temp) / 'ui.sqlite3'), 'SECRET_KEY': 'isolated-responsive-test',
                          'NOW': lambda: datetime(2026, 9, 15, 8, tzinfo=TZ)})
        with app.app_context():
            seed_database(get_db(), app.config['NOW']())
        server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as playwright:
                for engine in ('chromium', 'webkit'):
                    browser = getattr(playwright, engine).launch()
                    try:
                        for width, height in ((1440, 1000), (393, 852), (402, 874)):
                            journey(browser, engine, width, height, base)
                        fallback_checks(browser, engine, base, 'missing')
                        fallback_checks(browser, engine, base, 'throws')
                        if engine == 'chromium':
                            no_script_journey(browser, base)
                            context = browser.new_context(viewport={'width': 393, 'height': 852}, reduced_motion='reduce')
                            page = context.new_page(); watch(page)
                            page.goto(PREVIEW, wait_until='networkidle')
                            layout(page)
                            expect(page.locator('.menu-toggle')).to_be_visible()
                            capture(page, 'live-preview-393x852')
                            context.close()
                    finally:
                        browser.close()
        finally:
            server.shutdown(); thread.join(timeout=5)
    assert before == snapshot(), 'Existing demo data or secret changed'
    baseline = json.loads((ROOT / '.local' / 'responsive-update-before.json').read_text())
    assert baseline == snapshot(), 'Existing demo data or secret changed since update began'
    report['demo_data_preserved'] = True
    assert not report['page_errors'], report['page_errors']
    assert not report['server_errors'], report['server_errors']
    report['result'] = 'passed'
    check('Existing database and signing secret preserved; no uncaught JavaScript errors or HTTP 5xx responses')
except Exception as error:
    report['result'] = 'failed'
    report['failure'] = str(error)
    raise
finally:
    report['elapsed_seconds'] = round(monotonic() - started, 2)
    (REPORTS / 'browser-verification.json').write_text(json.dumps(report, indent=2) + '\n')
