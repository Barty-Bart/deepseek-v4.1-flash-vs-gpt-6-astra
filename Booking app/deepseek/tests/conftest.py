"""Shared test fixtures. Every test runs against an isolated temporary database."""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from northline import create_app                       # noqa: E402
from northline.config import SHOP_TZ                   # noqa: E402
from northline.db import open_standalone, write_txn    # noqa: E402
from northline.seed import seed_database               # noqa: E402

# A fixed "now": Tuesday 15 September 2026, 09:00 Melbourne time (shop open).
NOW = datetime(2026, 9, 15, 9, 0, tzinfo=SHOP_TZ)
ADMIN_USER = "admin"
ADMIN_PASS = "northline-demo"
CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture
def freeze_time(monkeypatch):
    """Pin 'now' for deterministic scheduling across all modules that use it."""
    import northline.admin_panel
    import northline.bookings
    import northline.customer
    import northline.scheduling
    import northline.seed

    def fixed() -> datetime:
        return NOW

    modules = (northline.admin_panel, northline.bookings, northline.customer,
               northline.scheduling, northline.seed)
    for module in modules:
        monkeypatch.setattr(module, "local_now", fixed, raising=False)
    return NOW


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test-northline.sqlite"


@pytest.fixture
def app(db_path, tmp_path, monkeypatch, freeze_time):
    # Every test runs on the frozen clock so fixed dates in the fixtures and the
    # assertions never drift with the wall clock.
    monkeypatch.setenv("NORTHLINE_SECRET_KEY", "test-secret-key-not-for-production")
    application = create_app(
        DATABASE_PATH=db_path,
        SECRET_KEY_FILE=tmp_path / "secret_key",
        INSTANCE_DIR=tmp_path,
        SECRET_KEY="test-secret-key-not-for-production",
        TESTING=True,
        ADMIN_USERNAME=ADMIN_USER,
        ADMIN_PASSWORD=ADMIN_PASS,
    )
    # Seed explicitly, exactly like a developer would with `flask seed`.
    conn = open_standalone(db_path)
    try:
        with write_txn(conn):
            seed_database(conn, ADMIN_USER, ADMIN_PASS)
    finally:
        conn.close()
    yield application


@pytest.fixture
def client(app, freeze_time):
    return app.test_client()


@pytest.fixture
def admin_client(app, client, freeze_time):
    login(client)
    return client


def csrf_from(client, url: str) -> str:
    html = client.get(url).get_data(as_text=True)
    match = CSRF_RE.search(html)
    assert match, f"no CSRF token found on {url}"
    return match.group(1)


def session_csrf(client) -> str:
    """A token from a page that always renders a form (used for nav-only pages)."""
    return csrf_from(client, "/manage")


def login(client, username: str = ADMIN_USER, password: str = ADMIN_PASS):
    token = csrf_from(client, "/admin/login")
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def booking_form_token(client, service=1, barber=1, day="2026-09-15") -> str:
    """Prefer the real booking form; fall back to any page with a CSRF token.

    The fallback keeps token retrieval independent of whether the chosen day
    still has free slots, which is exactly the case when a request is expected
    to be rejected.
    """
    html = client.get(f"/book?service={service}&barber={barber}&date={day}").get_data(as_text=True)
    match = CSRF_RE.search(html)
    return match.group(1) if match else session_csrf(client)


def post_booking(client, *, service=1, barber=1, day="2026-09-15", time="13:00",
                 name="Test Customer", email="test.customer@example.com", token=None):
    token = token or booking_form_token(client, service, barber, day)
    if not token:
        token = session_csrf(client)
    return client.post(
        "/book",
        data={
            "csrf_token": token,
            "service": str(service),
            "barber": str(barber),
            "date": day,
            "time": time,
            "name": name,
            "email": email,
        },
    )


def slots_on(client, service=1, barber=1, day="2026-09-15"):
    html = client.get(f"/book?service={service}&barber={barber}&date={day}").get_data(as_text=True)
    return re.findall(r'name="time" value="(\d\d:\d\d)"', html)


def all_appointments(path: Path):
    conn = open_standalone(path)
    try:
        return conn.execute("SELECT * FROM appointments ORDER BY id").fetchall()
    finally:
        conn.close()


def reference_token(client) -> str:
    """The private management link shown right after a booking."""
    html = client.get("/booked").get_data(as_text=True)
    match = re.search(r"/manage/([A-Za-z0-9_\-]{20,})", html)
    assert match, "no private management link on the confirmation page"
    return match.group(1)


def tomorrow() -> str:
    return (NOW.date() + timedelta(days=1)).isoformat()
