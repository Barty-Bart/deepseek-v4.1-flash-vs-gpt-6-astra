"""Two simultaneous attempts at the same slot must not both succeed."""
from __future__ import annotations

import threading

from conftest import all_appointments, booking_form_token, session_csrf

from northline.db import open_standalone
from northline.scheduling import iso_utc


def _post(app, day: str, time: str, name: str, email: str, ready, go, results, index):
    client = app.test_client()
    token = booking_form_token(client, 1, 1, day)
    ready.set()
    go.wait(10)
    response = client.post(
        "/book",
        data={
            "csrf_token": token,
            "service": "1",
            "barber": "1",
            "date": day,
            "time": time,
            "name": name,
            "email": email,
        },
    )
    results[index] = response


def test_concurrent_overlapping_requests_only_one_wins(app):
    day, time = "2026-09-15", "14:30"
    ready, go = threading.Event(), threading.Event()
    results: dict[int, object] = {}

    threads = [
        threading.Thread(
            target=_post,
            args=(app, day, time, f"Racer {i}", f"racer{i}@example.com", ready, go, results, i),
        )
        for i in range(2)
    ]
    for thread in threads:
        thread.start()
    ready.wait(5)       # both have a session + CSRF token
    go.set()            # fire at the same time
    for thread in threads:
        thread.join(15)

    assert len(results) == 2
    statuses = sorted(r.status_code for r in results.values())
    assert statuses == [200, 302], statuses

    loser = next(r for r in results.values() if r.status_code == 200)
    assert "just taken" in loser.get_data(as_text=True)

    rows = all_appointments(app.config["DATABASE_PATH"])
    matching = [
        r for r in rows
        if r["start_utc"] == "2026-09-15T04:30:00Z" and r["status"] == "confirmed"
    ]
    assert len(matching) == 1
    winner_email = matching[0]["customer_email"]
    assert winner_email in {"racer0@example.com", "racer1@example.com"}


def test_concurrent_adjacent_requests_both_succeed(app):
    """Different slots for the same barber are fine at the same time."""
    ready, go = threading.Event(), threading.Event()
    results: dict[int, object] = {}
    plan = [(0, "15:00"), (1, "15:30")]

    threads = [
        threading.Thread(
            target=_post,
            args=(app, "2026-09-15", time, f"Neighbour {i}", f"neighbour{i}@example.com",
                  ready, go, results, i),
        )
        for i, time in plan
    ]
    for thread in threads:
        thread.start()
    ready.wait(5)
    go.set()
    for thread in threads:
        thread.join(15)

    assert sorted(r.status_code for r in results.values()) == [302, 302]
    rows = all_appointments(app.config["DATABASE_PATH"])
    starts = {r["start_utc"] for r in rows if r["customer_name"].startswith("Neighbour")}
    assert starts == {"2026-09-15T05:00:00Z", "2026-09-15T05:30:00Z"}


def test_conflict_response_refreshes_availability(client):
    """The rejected page re-renders the slot list without the taken time."""
    from conftest import post_booking

    assert post_booking(client, day="2026-09-15", time="16:00").status_code == 302
    clash = post_booking(client, day="2026-09-15", time="16:00", name="Second Racer",
                         email="second.racer@example.com")
    body = clash.get_data(as_text=True)
    assert clash.status_code == 200
    assert "just taken" in body
    # The freshly rendered availability no longer offers 16:00.
    assert 'name="time" value="16:00"' not in body
    assert 'name="time" value="15:30"' in body or 'name="time" value="16:30"' in body


def test_many_connections_racing_the_same_slot(app, db_path):
    """Direct proof at the database layer: only one of N write transactions wins.

    Each thread opens its own SQLite connection, like separate server workers would.
    """
    from datetime import datetime

    from northline.bookings import BookingError, create_appointment
    from northline.config import SHOP_TZ
    from northline.db import open_standalone, write_txn

    start = datetime(2026, 9, 15, 15, 0, tzinfo=SHOP_TZ)
    ready, go = threading.Event(), threading.Event()
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt(index: int) -> None:
        conn = open_standalone(db_path)
        try:
            ready.set()
            go.wait(10)
            try:
                create_appointment(
                    conn, barber_id=1, service_id=1, start_local=start,
                    customer_name=f"Connection {index}", customer_email=f"conn{index}@example.com",
                    now=start,
                )
                result = "ok"
            except BookingError:
                result = "conflict"
        finally:
            conn.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    ready.wait(10)
    go.set()
    for thread in threads:
        thread.join(30)

    assert len(outcomes) == 8
    assert outcomes.count("ok") == 1, outcomes
    assert outcomes.count("conflict") == 7, outcomes

    rows = all_appointments(db_path)
    wins = [
        r for r in rows
        if r["start_utc"] == "2026-09-15T05:00:00Z" and r["status"] == "confirmed"
    ]
    assert len(wins) == 1
