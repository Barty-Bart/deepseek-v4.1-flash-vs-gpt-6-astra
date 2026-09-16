from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest

from db import get_db
from seed import seed_database
from tests.conftest import book, csrf, login, slots


@pytest.mark.parametrize('path', ['/admin', '/admin?date=2026-09-15', '/admin?staff=1'])
def test_admin_read_requires_auth(client, path):
    book(client, name='Hidden Customer')
    response = client.get(path)
    assert response.status_code == 302
    assert response.location.endswith('/admin/login')
    assert b'Hidden Customer' not in response.data


@pytest.mark.parametrize('path', ['/admin/bookings/1/cancel', '/admin/blocks', '/admin/blocks/1/delete', '/admin/logout'])
def test_every_admin_mutation_requires_auth_even_with_valid_csrf(app, client, path):
    book(client)
    response = client.post(path, data={'csrf_token': csrf(client), 'date': '2026-09-15', 'block_staff': '1', 'start': '14:00', 'end': '15:00', 'reason': 'Test reason'})
    assert response.status_code == 302
    assert response.location.endswith('/admin/login')
    with app.app_context():
        assert get_db().execute('SELECT status FROM bookings').fetchone()[0] == 'confirmed'
        assert get_db().execute('SELECT COUNT(*) FROM blocks').fetchone()[0] == 0


def test_login_password_hash_logout_and_session(client, app):
    token = csrf(client, '/admin/login')
    assert client.post('/admin/login', data={'csrf_token': token, 'username': 'admin', 'password': 'wrong'}).status_code == 401
    with app.app_context():
        password_hash = get_db().execute('SELECT password_hash FROM admins').fetchone()[0]
        assert password_hash != 'test-password' and password_hash.startswith('scrypt:')
    token = login(client)
    assert client.get('/admin').status_code == 200
    saved_cookie = client.get_cookie('northline_session').value
    assert client.post('/admin/logout', data={'csrf_token': token}).status_code == 303
    assert client.get('/admin').status_code == 302
    client.set_cookie('northline_session', saved_cookie)
    assert client.get('/admin').status_code == 302  # A copied cookie cannot restore a revoked session.
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM admin_sessions').fetchone()[0] == 0


def test_admin_session_expiry_is_enforced_on_server(client, app):
    token = login(client)
    original_now = app.config['NOW']()
    app.config['NOW'] = lambda: original_now + timedelta(hours=8)
    assert client.get('/admin').status_code == 302
    assert client.post('/admin/blocks', data={'csrf_token': token}).status_code == 302


def test_csrf_required_for_all_mutations(app, client):
    booked = book(client)
    login(client)
    for path in ['/book', '/availability', '/admin/login', '/admin/logout', '/admin/bookings/1/cancel', '/admin/blocks', '/admin/blocks/1/delete', booked.location + '/cancel']:
        for token in ('', 'forged', 'é'):
            response = client.post(path, data={'csrf_token': token})
            assert response.status_code == 400
            assert b'form has expired' in response.data
    with app.app_context():
        assert get_db().execute('SELECT status FROM bookings').fetchone()[0] == 'confirmed'


def test_block_overlap_explains_appointment_then_admin_cancellation_allows_block(app, client):
    book(client, name='Riley Example')
    token = login(client)
    data = {'csrf_token': token, 'date': '2026-09-15', 'block_staff': '1', 'start': '09:45', 'end': '10:15', 'reason': 'Training'}
    response = client.post('/admin/blocks', data=data)
    assert response.status_code == 409
    assert b'Riley Example' in response.data and b'Cancel that appointment first' in response.data
    with app.app_context():
        booking = get_db().execute('SELECT * FROM bookings').fetchone()
    assert booking['reference'].encode() in response.data
    cancelled = client.post(f"/admin/bookings/{booking['id']}/cancel", data={'csrf_token': token, 'date': '2026-09-15'})
    assert cancelled.status_code == 303
    assert client.post('/admin/blocks', data=data).status_code == 303
    assert '09:30' not in slots(client)
    assert '10:00' not in slots(client)
    assert '09:15' in slots(client)  # Ends exactly at block start.
    assert '10:15' in slots(client)  # Starts exactly at block end.
    assert '10:00' in slots(client, staff=2)
    with app.app_context():
        block_id = get_db().execute('SELECT id FROM blocks').fetchone()[0]
    assert client.post(f'/admin/blocks/{block_id}/delete', data={'csrf_token': token, 'date': '2026-09-15'}).status_code == 303
    assert '10:00' in slots(client)


def test_booking_cannot_cross_block(client):
    token = login(client)
    assert client.post('/admin/blocks', data={'csrf_token': token, 'date': '2026-09-15', 'block_staff': '1', 'start': '11:00', 'end': '11:30', 'reason': 'Maintenance'}).status_code == 303
    assert book(client, slot='10:45', service='3').status_code == 409
    assert book(client, slot='10:45', service='2').status_code == 303


@pytest.mark.parametrize('changes', [{'end': '10:00'}, {'end': '09:00'}, {'start': '09:07'}, {'block_staff': '99'}, {'reason': ''}, {'start': '08:00'}, {'end': '18:00'}, {'date': '2026-09-20'}, {'date': '2026-09-14'}, {'date': '2026-10-16'}, {'date': 'no-date'}])
def test_invalid_blocks_rejected_without_write(app, client, changes):
    token = login(client)
    data = {'csrf_token': token, 'date': '2026-09-15', 'block_staff': '1', 'start': '10:00', 'end': '11:00', 'reason': 'Staff training'}
    data.update(changes)
    assert client.post('/admin/blocks', data=data).status_code == 400
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM blocks').fetchone()[0] == 0


def test_block_and_booking_concurrent_transaction(app):
    barrier = Barrier(2)
    def block_attempt():
        client = app.test_client()
        token = login(client)
        barrier.wait(timeout=10)
        return client.post('/admin/blocks', data={'csrf_token': token, 'date': '2026-09-15', 'block_staff': '1', 'start': '10:00', 'end': '11:00', 'reason': 'Training'}).status_code
    def booking_attempt():
        client = app.test_client()
        token = csrf(client)
        barrier.wait(timeout=10)
        return client.post('/book', data={'csrf_token': token, 'date': '2026-09-15', 'staff': '1', 'service': '1', 'slot': '10:15', 'name': 'Race Customer', 'email': 'race@example.com'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(block_attempt), pool.submit(booking_attempt)
        assert sorted([first.result(), second.result()]) == [303, 409]
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0] + get_db().execute('SELECT COUNT(*) FROM blocks').fetchone()[0] == 1


def test_dashboard_filters_and_empty_states(client):
    book(client, name='Alex Customer')
    book(client, staff='2', name='Jordan Customer')
    login(client)
    response = client.get('/admin?date=2026-09-15&staff=1')
    assert b'Alex Customer' in response.data and b'Jordan Customer' not in response.data
    response = client.get('/admin?date=2026-09-15&staff=2')
    assert b'Jordan Customer' in response.data and b'Alex Customer' not in response.data
    assert b'No appointments' in client.get('/admin?date=2026-09-16').data
    assert client.get('/admin?date=invalid').status_code == 400
    assert client.get('/admin?staff=99').status_code == 400


def test_explicit_seed_is_idempotent_and_reset_requires_confirmation(app):
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM admins')
        result = seed_database(db, app.config['NOW']())
        assert 'Seeded 6 fictional' in result
        count = db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
        first = db.execute('SELECT reference FROM bookings ORDER BY id').fetchone()[0]
        assert 'already seeded' in seed_database(db, app.config['NOW']())
        assert db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0] == count
    runner = app.test_cli_runner()
    assert runner.invoke(args=['reset-demo']).exit_code != 0
    with app.app_context():
        assert get_db().execute('SELECT reference FROM bookings ORDER BY id').fetchone()[0] == first
    assert runner.invoke(args=['reset-demo', '--yes']).exit_code == 0
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0] == 6
