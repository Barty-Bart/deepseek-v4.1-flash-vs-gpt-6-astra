"""Booking domain logic: creation, lookup and cancellation."""
from __future__ import annotations

import re
import secrets
import sqlite3
from datetime import datetime

from .config import BOOKING_HORIZON_DAYS, SHOP_TZ
from .db import write_txn
from .scheduling import (
    BookingError,
    iso_utc,
    local_now,
    overlaps,
    parse_utc,
    validate_request,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
NAME_MIN, NAME_MAX = 2, 80
REFERENCE_ALPHABET = "ACDEFGHJKLMNPQRSTUVWXYZ23456789"   # no look-alike characters


def new_reference() -> str:
    body = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
    return f"NB-{body}"


def new_manage_token() -> str:
    """256 bits of entropy — private links cannot be guessed or enumerated."""
    return secrets.token_urlsafe(32)


def validate_customer(name: str, email: str) -> tuple[str, str]:
    name = (name or "").strip()
    email = (email or "").strip()
    if len(name) < NAME_MIN:
        raise BookingError("Please enter your name (at least 2 characters).")
    if len(name) > NAME_MAX:
        raise BookingError(f"Please keep your name under {NAME_MAX} characters.")
    if not email:
        raise BookingError("Please enter an email address.")
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise BookingError("Please enter a valid email address, for example you@example.com.")
    return name, email.lower()


def load_choices(conn: sqlite3.Connection):
    services = conn.execute(
        "SELECT * FROM services WHERE active = 1 ORDER BY sort_order, id"
    ).fetchall()
    barbers = conn.execute(
        "SELECT * FROM barbers WHERE active = 1 ORDER BY sort_order, id"
    ).fetchall()
    return services, barbers


def find_service(conn, raw) -> sqlite3.Row | None:
    try:
        return conn.execute(
            "SELECT * FROM services WHERE id = ? AND active = 1", (int(raw),)
        ).fetchone()
    except (TypeError, ValueError):
        return None


def find_barber(conn, raw) -> sqlite3.Row | None:
    try:
        return conn.execute(
            "SELECT * FROM barbers WHERE id = ? AND active = 1", (int(raw),)
        ).fetchone()
    except (TypeError, ValueError):
        return None


def parse_local_datetime(day: str, hhmm: str) -> datetime | None:
    try:
        return datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=SHOP_TZ)
    except (TypeError, ValueError):
        return None


def create_appointment(
    conn: sqlite3.Connection,
    *,
    barber_id: int,
    service_id: int,
    start_local: datetime,
    customer_name: str,
    customer_email: str,
    now: datetime | None = None,
) -> sqlite3.Row:
    """Validate and persist a booking atomically.

    The whole check-then-insert runs inside a single ``BEGIN IMMEDIATE``
    transaction, so two concurrent requests for an overlapping slot cannot both
    commit: the loser re-reads the winner's row and is rejected as a conflict.
    """
    now = now or local_now()
    barber = find_barber(conn, barber_id)
    service = find_service(conn, service_id)
    name, email = validate_customer(customer_name, customer_email)

    with write_txn(conn):
        start_utc, end_utc = validate_request(
            conn, barber=barber, service=service, start_local=start_local, now=now
        )
        # Re-check inside the write lock: the interval set may have changed.
        clash = conn.execute(
            """
            SELECT 1 FROM appointments
             WHERE barber_id = ? AND status = 'confirmed'
               AND start_utc < ? AND end_utc > ?
             LIMIT 1
            """,
            (barber_id, iso_utc(end_utc), iso_utc(start_utc)),
        ).fetchone()
        if clash:
            raise BookingError(
                f"Sorry — that time was just taken for {barber['name']}. Please pick another slot.",
                conflict=True,
            )

        for _ in range(12):
            reference, token = new_reference(), new_manage_token()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO appointments
                        (reference, manage_token, barber_id, service_id, customer_name,
                         customer_email, start_utc, end_utc, status, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
                    """,
                    (
                        reference, token, barber_id, service_id, name, email,
                        iso_utc(start_utc), iso_utc(end_utc), iso_utc(now),
                    ),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:  # pragma: no cover - astronomically unlikely
            raise BookingError("We could not create a booking reference. Please try again.")

        return conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (cur.lastrowid,)
        ).fetchone()


def find_by_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    if not token or len(token) < 20:
        return None
    return conn.execute(
        """
        SELECT a.*, b.name AS barber_name, s.name AS service_name,
               s.duration_minutes, s.price_cents
          FROM appointments a
          JOIN barbers b ON b.id = a.barber_id
          JOIN services s ON s.id = a.service_id
         WHERE a.manage_token = ?
        """,
        (token,),
    ).fetchone()


def cancel_by_token(conn: sqlite3.Connection, token: str, now: datetime | None = None):
    """Cancel a future confirmed booking. Returns (row, error_message)."""
    now = now or local_now()
    row = find_by_token(conn, token)
    if row is None:
        return None, "This management link is not valid."
    if row["status"] != "confirmed":
        return row, "This appointment is already cancelled."
    if parse_utc(row["start_utc"]) <= now:
        return row, "This appointment has already passed and cannot be cancelled here."

    with write_txn(conn):
        updated = conn.execute(
            """
            UPDATE appointments
               SET status = 'cancelled', cancelled_at_utc = ?
             WHERE id = ? AND status = 'confirmed'
            """,
            (iso_utc(now), row["id"]),
        )
        if updated.rowcount != 1:
            return (find_by_token(conn, token), "This appointment is already cancelled.")
    return find_by_token(conn, token), None


def slot_still_free(conn, barber_id: int, start_utc: datetime, end_utc: datetime) -> bool:
    from .scheduling import barber_intervals

    return not any(
        overlaps(start_utc, end_utc, i.start, i.end)
        for i in barber_intervals(conn, barber_id, start_utc, end_utc)
    )


__all__ = [
    "BOOKING_HORIZON_DAYS",
    "BookingError",
    "cancel_by_token",
    "create_appointment",
    "find_barber",
    "find_by_token",
    "find_service",
    "load_choices",
    "new_manage_token",
    "new_reference",
    "overlaps",
    "parse_local_datetime",
    "slot_still_free",
    "validate_customer",
]
