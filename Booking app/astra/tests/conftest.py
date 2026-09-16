import re
from datetime import datetime

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from db import get_db
from scheduling import TZ


@pytest.fixture
def config(tmp_path):
    return {'TESTING': True, 'DATABASE': str(tmp_path / 'test.sqlite3'), 'SECRET_KEY': 'isolated-test-secret',
            'NOW': lambda: datetime(2026, 9, 15, 8, 0, tzinfo=TZ)}


@pytest.fixture
def app(config):
    app = create_app(config)
    with app.app_context():
        get_db().execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)',
                         ('admin', generate_password_hash('test-password')))
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client, path='/'):
    response = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match, f'No CSRF token on {path}: {response.status_code}'
    return match.group(1)


def book(client, **changes):
    data = {'service': '1', 'staff': '1', 'date': '2026-09-15', 'slot': '10:00',
            'name': 'Test Customer', 'email': 'customer@example.com', 'csrf_token': csrf(client)}
    data.update(changes)
    return client.post('/book', data=data)


def login(client):
    token = csrf(client, '/admin/login')
    response = client.post('/admin/login', data={'csrf_token': token, 'username': 'admin', 'password': 'test-password'})
    assert response.status_code == 303
    return csrf(client, '/admin')


def slots(client, service=1, staff=1, day='2026-09-15'):
    response = client.get('/api/availability', query_string={'service': service, 'staff': staff, 'date': day})
    assert response.status_code == 200
    return [slot['value'] for slot in response.json['slots']]
