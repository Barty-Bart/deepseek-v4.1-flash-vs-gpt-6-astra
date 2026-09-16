"""Timezone-aware scheduling rules for Northline Barber.

All interval maths uses half-open intervals ``[start, end)``: a booking that
ends exactly when the next one begins does not overlap. Stored timestamps are
ISO-8601 UTC strings; everything user-facing is rendered in Australia/Melbourne.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date as date_cls
from datetime import datetime, time as time_cls, timedelta, timezone

from .config import (
    BOOKING_HORIZON_DAYS,
    BREAK_END,
    BREAK_START,
    CLOSE_TIME,
    OPEN_TIME,
    OPEN_WEEKDAYS,
    SHOP_TZ,
    SLOT_STEP_MINUTES,
)

UTC = timezone.utc


class BookingError(Exception):
    """A rejected booking request. ``message`` is safe to show a customer."""

    def __init__(self, message: str, *, conflict: bool = False):
        super().__init__(message)
        self.message = message
        self.conflict = conflict


# --------------------------------------------------------------------------- #
# Time helpers
# --------------------------------------------------------------------------- #
def parse_hhmm(value: str) -> time_cls:
    hours, minutes = value.split(":")
    return time_cls(int(hours), int(minutes))


def local_now() -> datetime:
    return datetime.now(SHOP_TZ)


def to_utc(naive_local: datetime) -> datetime:
    """Attach the Melbourne zone to a naive wall-clock time, then convert."""
    if naive_local.tzinfo is None:
        naive_local = naive_local.replace(tzinfo=SHOP_TZ)
    return naive_local.astimezone(UTC)


def to_local(aware: datetime) -> datetime:
    return aware.astimezone(SHOP_TZ)


def iso_utc(value: datetime) -> str:
    return to_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def local_interval(start_utc: str, end_utc: str) -> tuple[datetime, datetime]:
    return to_local(parse_utc(start_utc)), to_local(parse_utc(end_utc))


def _as_aware(value: datetime | str) -> datetime:
    """Accept either an aware datetime or a stored ISO-8601 UTC string."""
    if isinstance(value, str):
        return parse_utc(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def fmt_time(value: datetime | str) -> str:
    return to_local(_as_aware(value)).strftime("%H:%M")


def fmt_date_long(value: datetime | str) -> str:
    return to_local(_as_aware(value)).strftime("%a %-d %b %Y")


def fmt_datetime_long(value: datetime | str) -> str:
    return to_local(_as_aware(value)).strftime("%a %-d %b %Y, %H:%M")


def day_bounds_utc(day: date_cls) -> tuple[datetime, datetime]:
    """[local midnight, next local midnight) for a calendar day, DST-safe."""
    start = datetime.combine(day, time_cls(0, 0), tzinfo=SHOP_TZ)
    end = datetime.combine(day + timedelta(days=1), time_cls(0, 0), tzinfo=SHOP_TZ)
    return start.astimezone(UTC), end.astimezone(UTC)


def minutes(count: int) -> timedelta:
    return timedelta(minutes=int(count))


def is_future(value: datetime | str, now: datetime | None = None) -> bool:
    now = now or local_now()
    return _as_aware(value) > now


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def bookable_dates(now: datetime | None = None) -> list[date_cls]:
    now = now or local_now()
    today = now.date()
    return [
        today + timedelta(days=offset)
        for offset in range(0, BOOKING_HORIZON_DAYS + 1)
        if (today + timedelta(days=offset)).weekday() in OPEN_WEEKDAYS
    ]


# --------------------------------------------------------------------------- #
# Interval collection
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    kind: str          # 'appointment' | 'block'
    label: str = ""


def barber_intervals(
    conn: sqlite3.Connection,
    barber_id: int,
    window_start: datetime,
    window_end: datetime,
) -> list[Interval]:
    """Confirmed appointments and blocks for one barber inside a UTC window."""
    rows = conn.execute(
        """
        SELECT start_utc, end_utc, 'appointment' AS kind, reference AS label
          FROM appointments
         WHERE barber_id = ? AND status = 'confirmed'
           AND start_utc < ? AND end_utc > ?
        UNION ALL
        SELECT start_utc, end_utc, 'block' AS kind, COALESCE(reason, '') AS label
          FROM blocks
         WHERE barber_id = ?
           AND start_utc < ? AND end_utc > ?
        """,
        (
            barber_id, iso_utc(window_end), iso_utc(window_start),
            barber_id, iso_utc(window_end), iso_utc(window_start),
        ),
    ).fetchall()
    return [
        Interval(parse_utc(r["start_utc"]), parse_utc(r["end_utc"]), r["kind"], r["label"])
        for r in rows
    ]


def _break_interval(day: date_cls) -> tuple[datetime, datetime]:
    return (
        to_utc(datetime.combine(day, parse_hhmm(BREAK_START))),
        to_utc(datetime.combine(day, parse_hhmm(BREAK_END))),
    )


# --------------------------------------------------------------------------- #
# Availability
# --------------------------------------------------------------------------- #
def available_slots(
    conn: sqlite3.Connection,
    barber: sqlite3.Row,
    service: sqlite3.Row,
    day: date_cls,
    now: datetime | None = None,
) -> list[datetime]:
    """Start times (as Melbourne-local aware datetimes) the customer may pick."""
    now = now or local_now()
    if day.weekday() not in OPEN_WEEKDAYS:
        return []
    if day < now.date() or day > now.date() + timedelta(days=BOOKING_HORIZON_DAYS):
        return []

    duration = timedelta(minutes=service["duration_minutes"])
    work_start = max(parse_hhmm(barber["work_start"]), parse_hhmm(OPEN_TIME))
    work_end = min(parse_hhmm(barber["work_end"]), parse_hhmm(CLOSE_TIME))
    if work_end <= work_start:
        return []

    first = datetime.combine(day, work_start, tzinfo=SHOP_TZ)
    last_start = datetime.combine(day, work_end, tzinfo=SHOP_TZ) - duration

    window_start = first.astimezone(UTC)
    window_end = (last_start + duration).astimezone(UTC)
    busy = barber_intervals(conn, barber["id"], window_start, window_end)
    break_start, break_end = _break_interval(day)

    slots: list[datetime] = []
    cursor = first
    step = timedelta(minutes=SLOT_STEP_MINUTES)
    while cursor <= last_start:
        end = cursor + duration
        if cursor >= now:
            if not overlaps(cursor, end, break_start, break_end):
                if not any(overlaps(cursor, end, i.start, i.end) for i in busy):
                    slots.append(cursor)
        cursor = cursor + step
    return slots


def validate_request(
    conn: sqlite3.Connection,
    *,
    barber: sqlite3.Row | None,
    service: sqlite3.Row | None,
    start_local: datetime | None,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Full backend re-validation of a requested slot. Returns (start_utc, end_utc)."""
    now = now or local_now()

    if service is None or not service["active"]:
        raise BookingError("That service is not available. Please choose one of the listed services.")
    if barber is None or not barber["active"]:
        raise BookingError("That barber is not available. Please choose Alex or Jordan.")
    if start_local is None:
        raise BookingError("Please choose a start time.")

    start_local = start_local.replace(second=0, microsecond=0)
    if start_local.tzinfo is None:
        start_local = start_local.replace(tzinfo=SHOP_TZ)
    start_local = start_local.astimezone(SHOP_TZ)

    if start_local.minute % SLOT_STEP_MINUTES != 0:
        raise BookingError(
            f"Appointments start on a {SLOT_STEP_MINUTES}-minute grid. Please pick a listed time."
        )
    if start_local < now:
        raise BookingError("That time has already passed. Please choose a later slot.")
    if start_local.date() > now.date() + timedelta(days=BOOKING_HORIZON_DAYS):
        raise BookingError(
            f"Bookings open {BOOKING_HORIZON_DAYS} days ahead. Please choose an earlier date."
        )
    if start_local.date() < now.date():
        raise BookingError("That date is in the past. Please choose a later date.")
    if start_local.weekday() not in OPEN_WEEKDAYS:
        raise BookingError("The shop is closed that day — we open Tuesday to Saturday.")

    duration = timedelta(minutes=service["duration_minutes"])
    end_local = start_local + duration

    work_start = max(parse_hhmm(barber["work_start"]), parse_hhmm(OPEN_TIME))
    work_end = min(parse_hhmm(barber["work_end"]), parse_hhmm(CLOSE_TIME))
    open_dt = datetime.combine(start_local.date(), work_start, tzinfo=SHOP_TZ)
    close_dt = datetime.combine(start_local.date(), work_end, tzinfo=SHOP_TZ)
    if start_local < open_dt or end_local > close_dt:
        raise BookingError(
            f"{barber['name']} is not available then. {barber['name']} works "
            f"{work_start.strftime('%H:%M')}–{work_end.strftime('%H:%M')} on that day, and a "
            f"{service['duration_minutes']}-minute appointment must fit inside those hours."
        )

    break_start, break_end = _break_interval(start_local.date())
    if overlaps(start_local, end_local, break_start, break_end):
        raise BookingError(
            f"That time crosses the {BREAK_START}–{BREAK_END} break. Please choose another time."
        )

    start_utc, end_utc = start_local.astimezone(UTC), end_local.astimezone(UTC)
    for interval in barber_intervals(conn, barber["id"], start_utc, end_utc):
        if interval.kind == "block":
            raise BookingError(
                f"{barber['name']} is unavailable then. Please choose another time."
            )
        raise BookingError(
            f"Sorry — that time was just taken for {barber['name']}. "
            "Please pick another slot.",
            conflict=True,
        )
    return start_utc, end_utc


def block_conflict(
    conn: sqlite3.Connection, barber_id: int, start_utc: datetime, end_utc: datetime
) -> sqlite3.Row | None:
    """The first confirmed appointment a proposed unavailable period would overlap."""
    return conn.execute(
        """
        SELECT a.*, s.name AS service_name
          FROM appointments a
          JOIN services s ON s.id = a.service_id
         WHERE a.barber_id = ? AND a.status = 'confirmed'
           AND a.start_utc < ? AND a.end_utc > ?
         ORDER BY a.start_utc
         LIMIT 1
        """,
        (barber_id, iso_utc(end_utc), iso_utc(start_utc)),
    ).fetchone()
