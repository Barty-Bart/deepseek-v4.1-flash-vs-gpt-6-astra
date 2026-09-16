"""Seed and reset commands.

Both are explicit commands (`flask seed` / `flask reset`). The application never
seeds or resets automatically on startup — it only creates missing tables.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from .bookings import new_manage_token, new_reference
from .config import SHOP_TZ
from .scheduling import iso_utc, local_now

BARBERS = [
    ("Alex", "09:00", "17:00", 0),
    ("Jordan", "10:00", "17:00", 1),
]

SERVICES = [
    ("Classic Cut", 30, 4500, 0),
    ("Beard Trim", 15, 2500, 1),
    ("Cut and Beard", 45, 6500, 2),
]

# Demo appointments, expressed as offsets from the seed date in local time.
DEMO_APPOINTMENTS = [
    # (barber, service, day_offset, "HH:MM", name, email)
    ("Alex", "Classic Cut", 1, "09:30", "Priya Raman", "priya.raman@example.com"),
    ("Alex", "Cut and Beard", 1, "14:00", "Tom Whitfield", "tom.whitfield@example.com"),
    ("Jordan", "Beard Trim", 2, "10:15", "Marco Bellini", "marco.bellini@example.com"),
    ("Jordan", "Classic Cut", 3, "13:00", "Hannah Osei", "hannah.osei@example.com"),
    ("Alex", "Beard Trim", 4, "16:15", "Semi Adeyemi", "semi.adeyemi@example.com"),
]

DEMO_BLOCKS = [
    # (barber, day_offset, start, end, reason)
    ("Alex", 1, "11:00", "12:00", "Dentist appointment"),
    ("Jordan", 1, "15:00", "16:00", "Supplier delivery"),
    ("Alex", 3, "09:00", "10:00", "Late start — stocktake"),
]


def next_open_day(now: datetime, minimum_offset: int) -> datetime:
    """A local date at least `minimum_offset` days ahead that the shop opens."""
    day = now.date() + timedelta(days=minimum_offset)
    while day.weekday() not in (1, 2, 3, 4, 5):
        day += timedelta(days=1)
    return day


def seed_database(conn: sqlite3.Connection, admin_username: str, admin_password: str) -> dict:
    """Insert reference data and a small, realistic demo dataset.

    Idempotent for reference data: services, barbers and the admin account are
    upserted, and demo appointments/blocks are only added when no appointment
    rows exist yet.
    """
    now = local_now()

    for name, start, end, order in BARBERS:
        conn.execute(
            """
            INSERT INTO barbers (name, work_start, work_end, active, sort_order)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(name) DO UPDATE SET work_start = excluded.work_start,
                                            work_end = excluded.work_end,
                                            sort_order = excluded.sort_order
            """,
            (name, start, end, order),
        )
    for name, duration, price, order in SERVICES:
        conn.execute(
            """
            INSERT INTO services (name, duration_minutes, price_cents, active, sort_order)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(name) DO UPDATE SET duration_minutes = excluded.duration_minutes,
                                            price_cents = excluded.price_cents,
                                            sort_order = excluded.sort_order
            """,
            (name, duration, price, order),
        )
    conn.execute(
        """
        INSERT INTO admin_users (username, password_hash, created_at_utc)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash
        """,
        (admin_username, generate_password_hash(admin_password), iso_utc(now)),
    )

    barber_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM barbers")}
    service_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM services")}

    existing = conn.execute("SELECT COUNT(*) AS n FROM appointments").fetchone()["n"]
    created = {"appointments": 0, "blocks": 0}
    if existing:
        return created

    for barber, service, offset, hhmm, name, email in DEMO_APPOINTMENTS:
        day = next_open_day(now, offset)
        start_local = datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=SHOP_TZ)
        duration = next(
            d for s, d, _p, _o in SERVICES if s == service
        )
        end_local = start_local + timedelta(minutes=duration)
        conn.execute(
            """
            INSERT INTO appointments
                (reference, manage_token, barber_id, service_id, customer_name,
                 customer_email, start_utc, end_utc, status, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
            """,
            (
                new_reference(), new_manage_token(), barber_ids[barber],
                service_ids[service], name, email,
                iso_utc(start_local), iso_utc(end_local), iso_utc(now),
            ),
        )
        created["appointments"] += 1

    for barber, offset, start, end, reason in DEMO_BLOCKS:
        day = next_open_day(now, offset)
        start_local = datetime.strptime(f"{day} {start}", "%Y-%m-%d %H:%M").replace(tzinfo=SHOP_TZ)
        end_local = datetime.strptime(f"{day} {end}", "%Y-%m-%d %H:%M").replace(tzinfo=SHOP_TZ)
        conn.execute(
            """
            INSERT INTO blocks (barber_id, start_utc, end_utc, reason, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (barber_ids[barber], iso_utc(start_local), iso_utc(end_local), reason, iso_utc(now)),
        )
        created["blocks"] += 1

    return created


def drop_all(conn: sqlite3.Connection) -> None:
    for table in ("appointments", "blocks", "services", "barbers", "admin_users", "schema_version"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
