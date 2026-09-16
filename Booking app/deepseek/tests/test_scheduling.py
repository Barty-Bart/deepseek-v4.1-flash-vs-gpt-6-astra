"""Service duration, working hours, breaks, blocks and per-barber availability."""
from __future__ import annotations

import pytest

from conftest import NOW, post_booking, slots_on, tomorrow

from northline.config import SHOP_TZ
from northline.db import open_standalone
from northline.scheduling import fmt_datetime_long, parse_utc

ALEX, JORDAN = 1, 2
CLASSIC_CUT, BEARD_TRIM, CUT_AND_BEARD = 1, 2, 3
TODAY = "2026-09-15"       # Tuesday
WEDNESDAY = "2026-09-16"


def test_slots_respect_working_hours_and_break(client):
    slots = slots_on(client, CLASSIC_CUT, ALEX, TODAY)
    assert slots[0] == "09:00"
    assert "16:30" in slots            # 16:30–17:00 ends exactly at closing
    assert "16:45" not in slots        # would run past 17:00
    assert "12:15" not in slots        # would run into the 12:30 break
    assert "12:00" in slots            # ends exactly at 12:30
    assert "12:45" not in slots        # starts inside the break
    assert "13:00" in slots            # first slot after the break


def test_jordan_starts_later_than_alex(client):
    alex = slots_on(client, BEARD_TRIM, ALEX, TODAY)
    jordan = slots_on(client, BEARD_TRIM, JORDAN, TODAY)
    assert alex[0] == "09:00"
    assert jordan[0] == "10:00"
    assert "09:00" not in jordan and "09:45" not in jordan


def test_durations_change_what_fits(client):
    trim = slots_on(client, BEARD_TRIM, ALEX, TODAY)          # 15 min
    cut = slots_on(client, CLASSIC_CUT, ALEX, TODAY)          # 30 min
    combo = slots_on(client, CUT_AND_BEARD, ALEX, TODAY)      # 45 min
    assert "16:45" in trim
    assert "16:45" not in cut
    assert "16:30" in cut and "16:15" in combo
    assert "16:30" not in combo
    assert len(trim) > len(cut) > len(combo)
    # 45 minutes cannot fit between 12:00 and 13:00 either side of the break.
    assert "12:00" not in combo and "12:15" not in combo


def test_combo_rejected_when_it_would_cross_closing(client):
    response = post_booking(client, service=CUT_AND_BEARD, barber=ALEX, day=TODAY, time="16:30")
    assert response.status_code == 200
    assert "not available then" in response.get_data(as_text=True)


def test_break_is_enforced_on_the_backend(client):
    response = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="12:15")
    assert response.status_code == 200
    assert "break" in response.get_data(as_text=True).lower()


def test_seeded_block_removes_slots_and_rejects_backend_requests(client):
    # The demo data blocks Alex 11:00–12:00 on the next open day.
    slots = slots_on(client, CLASSIC_CUT, ALEX, WEDNESDAY)
    assert "11:00" not in slots and "11:30" not in slots
    assert "10:30" in slots and "12:00" in slots
    response = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=WEDNESDAY, time="11:00")
    assert response.status_code == 200
    assert "unavailable" in response.get_data(as_text=True).lower()


def test_off_grid_and_out_of_hours_requests_rejected(client):
    off_grid = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="09:07")
    assert "15-minute grid" in off_grid.get_data(as_text=True)

    # 08:00 today is before opening *and* before "now".
    early = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="08:00")
    assert "already passed" in early.get_data(as_text=True)

    # 07:30 tomorrow is on the grid but outside the barber's working hours.
    out_of_hours = post_booking(
        client, service=CLASSIC_CUT, barber=ALEX, day=tomorrow(), time="07:30"
    )
    assert "not available then" in out_of_hours.get_data(as_text=True)

    # Jordan does not start until 10:00.
    too_early_for_jordan = post_booking(
        client, service=BEARD_TRIM, barber=JORDAN, day=TODAY, time="09:30"
    )
    assert "not available then" in too_early_for_jordan.get_data(as_text=True)


def test_past_and_closed_days_rejected(client):
    past = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day="2026-09-14", time="10:00")
    assert "already passed" in past.get_data(as_text=True)

    earlier_today = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="09:00")
    # 09:00 == now, so it is still bookable; 08:45 is not on the grid at all.
    assert earlier_today.status_code in (200, 302)

    sunday = "2026-09-20"
    closed = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=sunday, time="10:00")
    assert "closed" in closed.get_data(as_text=True).lower()
    assert slots_on(client, CLASSIC_CUT, ALEX, sunday) == []

    monday = "2026-09-21"
    assert slots_on(client, CLASSIC_CUT, ALEX, monday) == []


def test_horizon_is_thirty_days(client):
    too_far = "2026-10-16"      # 31 days after 2026-09-15
    assert slots_on(client, CLASSIC_CUT, ALEX, too_far) == []
    response = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=too_far, time="10:00")
    assert "30 days" in response.get_data(as_text=True)
    assert slots_on(client, CLASSIC_CUT, ALEX, "2026-10-15")  # day 30 still open (Thursday)


def test_invalid_service_or_barber_rejected(client):
    bad_service = post_booking(client, service=999, barber=ALEX, day=TODAY, time="13:00")
    assert "service" in bad_service.get_data(as_text=True).lower()
    bad_barber = post_booking(client, service=CLASSIC_CUT, barber=999, day=TODAY, time="13:00")
    assert "barber" in bad_barber.get_data(as_text=True).lower()


def test_adjacent_appointments_are_allowed(client):
    first = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="13:00")
    assert first.status_code == 302
    # 13:30 starts exactly when the 13:00 booking ends — adjacent, so allowed.
    second = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="13:30")
    assert second.status_code == 302
    slots = slots_on(client, CLASSIC_CUT, ALEX, TODAY)
    assert "13:00" not in slots and "13:30" not in slots
    assert "14:00" in slots


def test_barbers_are_independent(client):
    alex = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="13:00")
    jordan = post_booking(client, service=CLASSIC_CUT, barber=JORDAN, day=TODAY, time="13:00")
    assert alex.status_code == 302 and jordan.status_code == 302
    # Alex's booking does not remove Jordan's slot, and vice versa.
    assert "13:00" not in slots_on(client, CLASSIC_CUT, ALEX, TODAY)
    assert "13:00" not in slots_on(client, CLASSIC_CUT, JORDAN, TODAY)


def test_double_booking_the_same_slot_is_rejected(client):
    assert post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="15:00").status_code == 302
    again = post_booking(
        client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="15:00",
        name="Someone Else", email="other.person@example.com",
    )
    assert again.status_code == 200
    assert "just taken" in again.get_data(as_text=True)


def test_overlapping_different_service_is_rejected(client):
    assert post_booking(client, service=CLASSIC_CUT, barber=ALEX, day=TODAY, time="15:00").status_code == 302
    overlapping = post_booking(client, service=CUT_AND_BEARD, barber=ALEX, day=TODAY, time="14:30")
    assert overlapping.status_code == 200
    assert "just taken" in overlapping.get_data(as_text=True)


def test_daylight_saving_offset_is_applied(client, app):
    """Melbourne switches to AEDT on 4 October 2026; stored times must follow."""
    response = post_booking(client, service=CLASSIC_CUT, barber=ALEX, day="2026-10-06", time="09:00")
    assert response.status_code == 302
    conn = open_standalone(app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            "SELECT * FROM appointments WHERE start_utc = '2026-10-05T22:00:00Z'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "09:00 AEDT should store as 22:00Z the previous day"
    assert fmt_datetime_long(parse_utc(row["start_utc"])) == "Tue 6 Oct 2026, 09:00"
    assert row["end_utc"] == "2026-10-05T22:30:00Z"


def test_slots_are_timezone_aware_and_ordered(client):
    slots = slots_on(client, CUT_AND_BEARD, ALEX, TODAY)
    assert slots == sorted(slots)
    assert all(int(s.split(":")[1]) % 15 == 0 for s in slots)
