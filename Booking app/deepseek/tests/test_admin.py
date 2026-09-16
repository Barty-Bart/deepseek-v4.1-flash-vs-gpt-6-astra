"""Admin authentication, CSRF protection and dashboard operations."""
from __future__ import annotations

from conftest import (
    ADMIN_PASS,
    ADMIN_USER,
    all_appointments,
    csrf_from,
    login,
    post_booking,
    session_csrf,
    slots_on,
    tomorrow,
)

from northline.db import open_standalone
from northline.scheduling import iso_utc

CUSTOMER_NAME = "Priya Raman"          # seeded demo customer


def _blocks(app):
    conn = open_standalone(app.config["DATABASE_PATH"])
    try:
        return conn.execute("SELECT * FROM blocks ORDER BY id").fetchall()
    finally:
        conn.close()


def _status(app, reference_endswith=None):
    return [r["status"] for r in all_appointments(app.config["DATABASE_PATH"])]


# --------------------------------------------------------------------------- #
# Unauthenticated access
# --------------------------------------------------------------------------- #
def test_unauthenticated_dashboard_redirects_and_leaks_nothing(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]
    body = response.get_data(as_text=True)
    assert CUSTOMER_NAME not in body and "priya.raman@example.com" not in body


def test_unauthenticated_mutations_change_nothing(client, app):
    before = _status(app)
    blocks_before = len(_blocks(app))

    cancel = client.post("/admin/appointments/1/cancel",
                         data={"csrf_token": session_csrf(client)})
    assert cancel.status_code == 302
    assert "/admin/login" in cancel.headers["Location"]

    add_block = client.post("/admin/blocks", data={
        "csrf_token": session_csrf(client), "barber": "1", "date": tomorrow(),
        "start": "15:00", "end": "16:00", "reason": "unauthorised",
    })
    assert add_block.status_code == 302

    delete_block = client.post("/admin/blocks/1/delete", data={"csrf_token": session_csrf(client)})
    assert delete_block.status_code == 302

    assert _status(app) == before
    assert len(_blocks(app)) == blocks_before


def test_admin_pages_return_no_customer_data_to_anonymous_callers(client):
    for url in ("/admin/", "/admin/?date=2026-09-16", "/admin/blocks"):
        response = client.get(url, follow_redirects=False)
        assert response.status_code in (302, 405)
        assert "Priya" not in response.get_data(as_text=True)


# --------------------------------------------------------------------------- #
# Login / logout
# --------------------------------------------------------------------------- #
def test_login_rejects_bad_credentials(client):
    response = login(client, "admin", "wrong-password")
    assert response.status_code == 401
    assert "Incorrect username or password" in response.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302

    unknown = login(client, "not-a-user", "northline-demo")
    assert unknown.status_code == 401


def test_login_requires_csrf(client):
    response = client.post("/admin/login", data={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert response.status_code == 400
    assert client.get("/admin/").status_code == 302


def test_login_succeeds_and_session_is_rotated(client):
    with client.session_transaction() as session:
        session["planted"] = "attacker-supplied"
    assert login(client).status_code == 302
    with client.session_transaction() as session:
        assert "planted" not in session
        assert session.get("admin_user_id")


def test_password_is_hashed_in_the_database(app):
    conn = open_standalone(app.config["DATABASE_PATH"])
    try:
        row = conn.execute("SELECT password_hash FROM admin_users WHERE username = ?",
                           (ADMIN_USER,)).fetchone()
    finally:
        conn.close()
    assert row["password_hash"] != ADMIN_PASS
    assert row["password_hash"].startswith(("scrypt:", "pbkdf2:"))


def test_logout_ends_the_session(admin_client):
    assert admin_client.get("/admin/").status_code == 200
    response = admin_client.post("/admin/logout", data={"csrf_token": session_csrf(admin_client)})
    assert response.status_code == 302
    assert admin_client.get("/admin/").status_code == 302


def test_admin_mutations_require_csrf(admin_client, app):
    before = _status(app)
    missing = admin_client.post("/admin/appointments/1/cancel", data={})
    assert missing.status_code == 400
    assert _status(app) == before


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def test_dashboard_lists_the_day_and_shows_customer_details(admin_client):
    day = tomorrow()          # the seeded demo bookings live on the next open days
    body = admin_client.get(f"/admin/?date={day}").get_data(as_text=True)
    assert "Priya Raman" in body
    assert "priya.raman@example.com" in body
    assert "Classic Cut" in body
    assert "09:30" in body
    assert "Dentist appointment" in body       # seeded staff block


def test_dashboard_filters_by_barber(admin_client):
    day = tomorrow()
    alex = admin_client.get(f"/admin/?date={day}&barber=1").get_data(as_text=True)
    jordan = admin_client.get(f"/admin/?date={day}&barber=2").get_data(as_text=True)
    assert "Priya Raman" in alex
    assert "Priya Raman" not in jordan


def test_dashboard_empty_state(admin_client):
    body = admin_client.get("/admin/?date=2026-09-20").get_data(as_text=True)   # a Sunday
    assert "No bookings on this day" in body


def test_invalid_barber_filter_is_handled(admin_client):
    response = admin_client.get("/admin/?date=2026-09-16&barber=999")
    assert response.status_code == 200
    assert "not valid" in response.get_data(as_text=True)


def test_admin_cancel_releases_the_slot(admin_client, app):
    day = tomorrow()
    token = csrf_from(admin_client, f"/admin/?date={day}")
    appointment = next(
        r for r in all_appointments(app.config["DATABASE_PATH"])
        if r["customer_name"] == "Priya Raman"
    )
    token = csrf_from(admin_client, f"/admin/?date={day}")
    response = admin_client.post(
        f"/admin/appointments/{appointment['id']}/cancel",
        data={"csrf_token": token, "return_date": day},
    )
    assert response.status_code == 302
    assert len([s for s in _status(app) if s == "cancelled"]) == 1
    # 09:30 becomes bookable again for Alex.
    assert "09:30" in slots_on(admin_client, 1, 1, day)


# --------------------------------------------------------------------------- #
# Staff unavailable periods
# --------------------------------------------------------------------------- #
def test_block_overlapping_an_appointment_is_rejected_with_the_reference(admin_client, app):
    day = tomorrow()
    before = len(_blocks(app))
    appointment = next(
        r for r in all_appointments(app.config["DATABASE_PATH"])
        if r["customer_name"] == "Priya Raman"
    )
    response = admin_client.post("/admin/blocks", data={
        "csrf_token": csrf_from(admin_client, f"/admin/?date={day}"),
        "barber": "1", "date": day, "start": "09:00", "end": "10:00",
        "reason": "Should not be created", "return_date": day,
    }, follow_redirects=True)
    body = response.get_data(as_text=True)
    assert appointment["reference"] in body
    assert "Cancel that appointment first" in body
    assert len(_blocks(app)) == before
    # The conflicting block was not written.
    assert not any(b["reason"] == "Should not be created" for b in _blocks(app))


def test_block_creation_and_removal(admin_client, app):
    day = "2026-09-17"      # Thursday, no seeded bookings for Alex at 15:00
    response = admin_client.post("/admin/blocks", data={
        "csrf_token": csrf_from(admin_client, f"/admin/?date={day}"),
        "barber": "1", "date": day, "start": "15:00", "end": "16:00",
        "reason": "Training", "return_date": day,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Added unavailability" in response.get_data(as_text=True)

    created = [b for b in _blocks(app) if b["reason"] == "Training"]
    assert len(created) == 1
    assert created[0]["start_utc"] == "2026-09-17T05:00:00Z"

    # The new block removes those slots from availability.
    slots = slots_on(admin_client, 1, 1, day)
    assert "15:00" not in slots and "15:30" not in slots
    assert "14:30" in slots and "16:00" in slots

    removed = admin_client.post(
        f"/admin/blocks/{created[0]['id']}/delete",
        data={"csrf_token": csrf_from(admin_client, f"/admin/?date={day}"), "return_date": day},
        follow_redirects=True,
    )
    assert "Removed the unavailable period" in removed.get_data(as_text=True)
    assert "15:00" in slots_on(admin_client, 1, 1, day)


def test_block_validation_errors(admin_client, app):
    day = "2026-09-17"
    before = len(_blocks(app))
    cases = [
        ({"start": "16:00", "end": "15:00"}, "end time must be after"),
        ({"start": "nonsense", "end": "16:00"}, "valid start and end"),
        ({"start": "", "end": ""}, "valid start and end"),
    ]
    for overrides, expected in cases:
        payload = {"csrf_token": csrf_from(admin_client, f"/admin/?date={day}"),
                   "barber": "1", "date": day, "start": "15:00", "end": "16:00",
                   "reason": "bad"}
        payload.update(overrides)
        response = admin_client.post("/admin/blocks", data=payload, follow_redirects=True)
        assert expected in response.get_data(as_text=True)
    assert len(_blocks(app)) == before

    bad_barber = admin_client.post("/admin/blocks", data={
        "csrf_token": csrf_from(admin_client, f"/admin/?date={day}"),
        "barber": "999", "date": day, "start": "15:00", "end": "16:00",
    }, follow_redirects=True)
    assert "Choose a barber" in bad_barber.get_data(as_text=True)
    assert len(_blocks(app)) == before


def test_blocks_belong_to_one_barber_only(admin_client, app):
    day = "2026-09-17"
    admin_client.post("/admin/blocks", data={
        "csrf_token": csrf_from(admin_client, f"/admin/?date={day}"),
        "barber": "1", "date": day, "start": "14:00", "end": "15:00",
        "reason": "Alex only", "return_date": day,
    })
    assert "14:00" not in slots_on(admin_client, 1, 1, day)
    assert "14:00" in slots_on(admin_client, 1, 2, day)


def test_dashboard_does_not_offer_rescheduling(admin_client):
    body = admin_client.get("/admin/?date=2026-09-16").get_data(as_text=True)
    assert "resched" not in body.lower()
