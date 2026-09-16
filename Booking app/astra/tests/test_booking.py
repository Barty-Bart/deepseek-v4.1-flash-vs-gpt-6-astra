import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest

from app import create_app
from db import get_db
from scheduling import BookingError, TZ, at_time, local, parse_day, utc_string
from tests.conftest import book, csrf, login, slots


def test_persistence_across_application_restart(app, client, config):
    response = book(client)
    assert response.status_code == 303
    private_path = response.location
    restarted = create_app(config).test_client()
    page = restarted.get(private_path)
    assert page.status_code == 200
    assert b'Test Customer' in page.data
    assert '10:00' not in slots(restarted)
    with app.app_context():
        row = get_db().execute('SELECT * FROM bookings').fetchone()
        assert row['starts_at'] == '2026-09-15T00:00:00Z'
        assert row['ends_at'] == '2026-09-15T00:30:00Z'
        assert row['token_hash'] == hashlib.sha256(private_path.rsplit('/', 1)[-1].encode()).hexdigest()


@pytest.mark.parametrize('service,last_before_break,last_of_day', [(1, '12:00', '16:30'), (2, '12:15', '16:45'), (3, '11:45', '16:15')])
def test_service_duration_hours_and_breaks(client, service, last_before_break, last_of_day):
    available = slots(client, service=service)
    assert last_before_break in available
    assert last_of_day in available
    assert available[-1] == last_of_day
    assert '12:30' not in available
    assert '12:45' not in available
    assert '13:00' in available
    assert '17:00' not in available
    assert book(client, service=str(service), slot=last_of_day).status_code == 303


@pytest.mark.parametrize('changes,expected', [
    ({'slot': '08:45'}, 409), ({'slot': '17:00'}, 409), ({'service': '3', 'slot': '16:30'}, 409),
    ({'service': '1', 'slot': '12:15'}, 409), ({'slot': '12:30'}, 409),
    ({'staff': '2', 'slot': '09:45'}, 409), ({'date': '2026-09-20'}, 409),
    ({'date': '2026-09-21'}, 409), ({'date': '2026-09-14'}, 400),
    ({'date': '2026-10-16'}, 400), ({'date': '2026-10-15', 'slot': '09:00'}, 409),
    ({'date': 'bad'}, 400), ({'date': '2026-02-30'}, 400),
    ({'slot': '10:07'}, 409), ({'slot': ''}, 400), ({'slot': '25:00'}, 400),
    ({'service': '99'}, 400), ({'service': '1 OR 1=1'}, 400), ({'staff': '99'}, 400),
    ({'name': ' '}, 400), ({'name': 'a' * 81}, 400), ({'name': 'Foo\nBar'}, 400),
    ({'email': 'invalid'}, 400), ({'email': 'x@a..com'}, 400), ({'email': 'a' * 250 + '@test.com'}, 400),
])
def test_invalid_requests_are_rejected_without_writes(app, client, changes, expected):
    response = book(client, **changes)
    assert response.status_code == expected
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0] == 0


def test_past_today_is_rejected(app, client):
    app.config['NOW'] = lambda: datetime(2026, 9, 15, 10, 1, tzinfo=TZ)
    assert book(client).status_code == 409
    assert '10:00' not in slots(client)
    assert '10:15' in slots(client)


def test_adjacent_appointments_allowed_and_overlap_rejected(client):
    assert book(client, service='3').status_code == 303  # 10:00–10:45
    assert book(client, service='2', slot='09:45').status_code == 303
    assert book(client, service='1', slot='10:45').status_code == 303
    conflict = book(client, service='1', slot='10:15')
    assert conflict.status_code == 409
    assert b'just been booked' in conflict.data
    assert b'value="10:15"' not in conflict.data


def test_separate_barber_availability(client):
    assert '09:00' in slots(client, staff=1)
    assert '09:00' not in slots(client, staff=2)
    assert book(client, staff='1').status_code == 303
    assert '10:00' not in slots(client, staff=1)
    assert '10:00' in slots(client, staff=2)
    assert book(client, staff='2').status_code == 303


def test_customer_cancellation_preserves_record_releases_slot(app, client):
    booked = book(client)
    token = csrf(client, booked.location)
    response = client.post(booked.location + '/cancel', data={'csrf_token': token})
    assert response.status_code == 303
    assert b'Cancelled' in client.get(booked.location).data
    assert '10:00' in slots(client)
    with app.app_context():
        row = get_db().execute('SELECT * FROM bookings').fetchone()
        assert row['status'] == 'cancelled'
        assert row['cancelled_at'] is not None
    assert book(client).status_code == 303


def test_past_customer_appointment_cannot_cancel(app, client):
    booked = book(client)
    token = csrf(client, booked.location)
    app.config['NOW'] = lambda: datetime(2026, 9, 15, 10, 0, tzinfo=TZ)
    client.post(booked.location + '/cancel', data={'csrf_token': token})
    with app.app_context():
        assert get_db().execute('SELECT status FROM bookings').fetchone()[0] == 'confirmed'


@pytest.mark.parametrize('second_time', ['10:00', '10:15'])
def test_concurrent_conflicting_requests_exactly_one_succeeds(app, second_time):
    barrier = Barrier(2)
    def attempt(slot):
        client = app.test_client()
        token = csrf(client)
        barrier.wait(timeout=10)
        return client.post('/book', data={'csrf_token': token, 'service': '1', 'staff': '1', 'date': '2026-09-15',
                                         'slot': slot, 'name': 'Concurrent Customer', 'email': 'race@example.com'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(attempt, ['10:00', second_time]))
    assert sorted(responses) == [303, 409]
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'").fetchone()[0] == 1


def test_private_links_do_not_enumerate_or_select_other_bookings(app, client):
    first = book(client, name='Private First', email='first@example.com')
    second = book(client, slot='11:00', name='Private Second', email='second@example.com')
    token1, token2 = first.location.rsplit('/', 1)[-1], second.location.rsplit('/', 1)[-1]
    assert len(token1) == len(token2) == 43 and token1 != token2
    page = client.get(first.location + '?id=2&token=' + token2)
    assert b'first@example.com' in page.data
    assert b'second@example.com' not in page.data
    with app.app_context():
        reference = get_db().execute('SELECT reference FROM bookings LIMIT 1').fetchone()[0]
    for guessed in ('1', '2', reference, 'A' * 43, token1[:-1] + ('B' if token1[-1] != 'B' else 'C')):
        response = client.get('/booking/' + guessed)
        assert response.status_code == 404
        assert b'first@example.com' not in response.data
    assert b'first@example.com' not in client.get('/').data
    assert b'first@example.com' not in client.get('/api/availability?service=1&staff=1&date=2026-09-15').data
    response = client.post(first.location + '/cancel', data={'csrf_token': csrf(client, first.location), 'booking_id': '2'})
    assert response.status_code == 303
    assert b'Confirmed' in client.get(second.location).data
    assert client.get(first.location).headers['Referrer-Policy'] == 'no-referrer'


def test_dst_conversion_and_booking_across_change(app, client):
    assert utc_string(at_time(parse_day('2026-10-03'), '10:00')) == '2026-10-03T00:00:00Z'
    assert utc_string(at_time(parse_day('2026-10-06'), '10:00')) == '2026-10-05T23:00:00Z'
    with pytest.raises(BookingError, match='does not exist'):
        at_time(parse_day('2026-10-04'), '02:15')
    with pytest.raises(BookingError, match='ambiguous'):
        at_time(parse_day('2026-04-05'), '02:15')
    booked = book(client, date='2026-10-06')
    assert booked.status_code == 303
    assert b'AEDT' in client.get(booked.location).data
    with app.app_context():
        booking = get_db().execute('SELECT * FROM bookings').fetchone()
        assert local(booking['starts_at']).hour == 10
        assert booking['starts_at'] == '2026-10-05T23:00:00Z'


def test_no_javascript_availability_preserves_details_without_query_string(client):
    response = client.post('/availability', data={'csrf_token': csrf(client), 'service': '3', 'staff': '2', 'date': '2026-09-16', 'name': 'Saved Name', 'email': 'saved@example.com'})
    assert response.status_code == 200
    assert b'Saved Name' in response.data and b'saved@example.com' in response.data
    assert b'value="16:15"' in response.data and b'value="16:30"' not in response.data
