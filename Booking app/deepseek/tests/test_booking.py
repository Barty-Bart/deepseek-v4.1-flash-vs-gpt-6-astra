"""Customer journey: persistence, cancellation, validation and private links."""
from __future__ import annotations

import re

from conftest import (
    NOW,
    all_appointments,
    booking_form_token,
    post_booking,
    reference_token,
    session_csrf,
    slots_on,
)

from northline import create_app
from northline.db import open_standalone
from northline.scheduling import fmt_datetime_long, parse_utc

ALEX = 1
CLASSIC_CUT = 1


def test_happy_path_creates_a_booking(client, app):
    response = post_booking(
        client, service=CLASSIC_CUT, barber=ALEX, day="2026-09-15", time="13:00",
        name="Ada Lovelace", email="Ada.Lovelace@Example.com",
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/booked")

    page = client.get("/booked").get_data(as_text=True)
    assert "NB-" in page
    assert "Ada Lovelace" in page
    assert "ada.lovelace@example.com" in page          # emails are normalised to lower case
    assert "Tuesday 15 September 2026" in page or "Tue 15 Sep 2026" in page

    rows = all_appointments(app.config["DATABASE_PATH"])
    assert len(rows) == 6                               # 5 seeded + 1 new
    booked = rows[-1]
    assert booked["status"] == "confirmed"
    assert booked["start_utc"] == "2026-09-15T03:00:00Z"    # 13:00 AEST
    assert booked["end_utc"] == "2026-09-15T03:30:00Z"


def test_booking_persists_across_application_restart(app, db_path):
    """A second app instance over the same file must still see the booking."""
    first = app.test_client()
    assert post_booking(first, day="2026-09-15", time="14:00", name="Restart Test",
                        email="restart@example.com").status_code == 302
    token = reference_token(first)

    restarted = create_app(
        DATABASE_PATH=db_path,
        SECRET_KEY_FILE=app.config["SECRET_KEY_FILE"],
        SECRET_KEY="test-secret-key-not-for-production",
        TESTING=True,
    )
    fresh = restarted.test_client()
    page = fresh.get(f"/manage/{token}")
    assert page.status_code == 200
    assert "Restart Test" in page.get_data(as_text=True)
    assert "Confirmed" in page.get_data(as_text=True)


def test_confirmation_requires_the_private_token_in_session(client):
    post_booking(client, day="2026-09-15", time="14:00")
    with client.session_transaction() as session:
        token = session.get("last_booking_token")
    assert token and len(token) >= 32

    with client.session_transaction() as session:
        session.pop("last_booking_token")
    assert client.get("/booked").status_code == 302


def test_cancellation_releases_the_slot(client, app):
    post_booking(client, day="2026-09-15", time="13:00")
    token = reference_token(client)
    assert "13:00" not in slots_on(client, CLASSIC_CUT, ALEX, "2026-09-15")

    page = client.post(f"/manage/{token}/cancel",
                       data={"csrf_token": session_csrf(client)})
    assert page.status_code == 200
    assert "Booking cancelled" in page.get_data(as_text=True)
    assert "Cancelled" in page.get_data(as_text=True)
    assert "13:00" in slots_on(client, CLASSIC_CUT, ALEX, "2026-09-15")

    # The record is preserved, not deleted.
    rows = all_appointments(app.config["DATABASE_PATH"])
    assert [r["status"] for r in rows].count("cancelled") == 1
    assert rows[-1]["cancelled_at_utc"] is not None

    # And the slot can be rebooked by somebody else.
    other = post_booking(client, day="2026-09-15", time="13:00",
                         name="Second Customer", email="second@example.com")
    assert other.status_code == 302


def test_cancelling_twice_is_refused(client):
    post_booking(client, day="2026-09-15", time="13:00")
    token = reference_token(client)
    token_value = session_csrf(client)
    assert client.post(f"/manage/{token}/cancel", data={"csrf_token": token_value}).status_code == 200
    second = client.post(f"/manage/{token}/cancel", data={"csrf_token": session_csrf(client)})
    assert second.status_code == 409
    assert "already cancelled" in second.get_data(as_text=True).lower()


def test_past_appointment_cannot_be_cancelled(client, app):
    """A booking made in the past is viewable but no longer cancellable."""
    conn = open_standalone(app.config["DATABASE_PATH"])
    with conn:
        conn.execute(
            """INSERT INTO appointments
               (reference, manage_token, barber_id, service_id, customer_name, customer_email,
                start_utc, end_utc, status, created_at_utc)
               VALUES ('NB-PAST01', 'pastbookingtoken0123456789abcdef', 1, 1, 'Old Booking',
                       'old@example.com', '2026-09-14T01:00:00Z', '2026-09-14T01:30:00Z',
                       'confirmed', '2026-09-01T00:00:00Z')"""
        )
    conn.close()
    page = client.get("/manage/pastbookingtoken0123456789abcdef")
    assert page.status_code == 200
    assert "no longer be cancelled" in page.get_data(as_text=True)
    refused = client.post("/manage/pastbookingtoken0123456789abcdef/cancel",
                          data={"csrf_token": session_csrf(client)})
    assert refused.status_code == 409
    assert "already passed" in refused.get_data(as_text=True)


def test_validation_errors_are_shown_and_nothing_is_saved(client, app):
    before = len(all_appointments(app.config["DATABASE_PATH"]))

    bad_email = post_booking(client, day="2026-09-15", time="13:00",
                             name="Valid Name", email="not-an-email")
    assert bad_email.status_code == 200
    assert "valid email address" in bad_email.get_data(as_text=True)

    bad_name = post_booking(client, day="2026-09-15", time="13:00", name="A", email="a@b.co")
    assert "at least 2 characters" in bad_name.get_data(as_text=True)

    blank = post_booking(client, day="2026-09-15", time="13:00", name="", email="")
    assert "enter your name" in blank.get_data(as_text=True)

    assert len(all_appointments(app.config["DATABASE_PATH"])) == before


def test_private_link_cannot_be_enumerated_or_accessed_by_another_customer(client):
    post_booking(client, day="2026-09-15", time="13:00", name="Customer One",
                 email="one@example.com")
    token_one = reference_token(client)
    post_booking(client, day="2026-09-15", time="15:00", name="Customer Two",
                 email="two@example.com")
    token_two = reference_token(client)
    assert token_one != token_two
    assert len(token_one) >= 32 and len(token_two) >= 32

    # Guessing, truncating or mutating a token gives nothing back.
    for candidate in (token_two[:-1], token_two[:-4], token_two[:16], token_two.upper(),
                      "x" * 43, "0" * 43, token_two + "a"):
        response = client.get(f"/manage/{candidate}")
        assert response.status_code == 404, candidate
        assert "Customer Two" not in response.get_data(as_text=True)

    # Another customer's link never exposes your details.
    other = client.get(f"/manage/{token_two}")
    assert "Customer Two" in other.get_data(as_text=True)
    assert "Customer One" not in other.get_data(as_text=True)
    assert "one@example.com" not in other.get_data(as_text=True)

    # Cancelling with a wrong token cannot touch your booking.
    assert client.post(f"/manage/{token_two[:-1]}/cancel",
                       data={"csrf_token": session_csrf(client)}).status_code == 404
    assert "Customer One" in client.get(f"/manage/{token_one}").get_data(as_text=True)


def test_management_link_accepts_a_pasted_url(client):
    post_booking(client, day="2026-09-15", time="13:00")
    token = reference_token(client)
    response = client.post("/manage/lookup",
                           data={"token": f"http://127.0.0.1:5182/manage/{token}",
                                 "csrf_token": session_csrf(client)})
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/manage/{token}")


def test_csrf_is_required_for_booking_and_cancelling(client):
    no_token = client.post(
        "/book",
        data={"service": "1", "barber": "1", "date": "2026-09-15", "time": "13:00",
              "name": "No Token", "email": "no.token@example.com"},
    )
    assert no_token.status_code == 400

    post_booking(client, day="2026-09-15", time="13:00")
    token = reference_token(client)
    stale = client.post(f"/manage/{token}/cancel", data={"csrf_token": "not-the-token"})
    assert stale.status_code == 400
    assert "Confirmed" in client.get(f"/manage/{token}").get_data(as_text=True)


def test_customer_pages_never_list_other_customers(client):
    post_booking(client, day="2026-09-15", time="13:00", name="Secret Person",
                 email="secret@example.com")
    token = reference_token(client)
    for url in ("/", "/book?service=1&barber=1&date=2026-09-15", "/manage"):
        body = client.get(url).get_data(as_text=True)
        assert "Secret Person" not in body
        assert "secret@example.com" not in body
    # Your own booking is shown only through your private link.
    assert "Secret Person" in client.get(f"/manage/{token}").get_data(as_text=True)


def test_lookup_with_an_unknown_link_explains_instead_of_redirecting(client):
    response = client.post("/manage/lookup",
                           data={"token": "http://127.0.0.1:5182/manage/not-a-real-token-value",
                                 "csrf_token": session_csrf(client)})
    assert response.status_code == 404
    body = response.get_data(as_text=True)
    assert "could not find a booking" in body
    assert "not-a-real-token-value" not in body
