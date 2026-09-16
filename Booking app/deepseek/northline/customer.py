"""Customer-facing booking journey."""
from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    url_for,
)

from .bookings import (
    cancel_by_token,
    create_appointment,
    find_barber,
    find_by_token,
    find_service,
    load_choices,
    parse_local_datetime,
)
from .config import (
    BOOKING_HORIZON_DAYS,
    BREAK_END,
    BREAK_START,
    SHOP_TZ_NAME,
)
from .db import get_db
from .scheduling import (
    BookingError,
    available_slots,
    bookable_dates,
    local_now,
)

bp = Blueprint("customer", __name__)


def _parse_day(raw: str | None):
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.app_context_processor
def inject_globals():
    return {"shop_tz_name": SHOP_TZ_NAME, "break_window": f"{BREAK_START}–{BREAK_END}"}


@bp.route("/")
def home():
    conn = get_db()
    services, barbers = load_choices(conn)
    return render_template(
        "home.html",
        services=services,
        barbers=barbers,
        horizon=BOOKING_HORIZON_DAYS,
        selected_service=find_service(conn, request.args.get("service")),
        selected_barber=find_barber(conn, request.args.get("barber")),
    )


@bp.route("/book", methods=("GET", "POST"))
def book():
    conn = get_db()
    services, barbers = load_choices(conn)
    now = local_now()

    service = find_service(conn, request.values.get("service"))
    barber = find_barber(conn, request.values.get("barber"))
    day = _parse_day(request.values.get("date"))
    errors: list[str] = []

    if request.method == "POST":
        errors = _handle_post(conn, now, services, barbers)
        if not errors:
            return redirect(url_for("customer.booked"))

    dates = bookable_dates(now)

    slots: list[datetime] = []
    if service and barber and day:
        slots = available_slots(conn, barber, service, day, now=now)

    return render_template(
        "book.html",
        services=services,
        barbers=barbers,
        selected_service=service,
        selected_barber=barber,
        selected_day=day,
        dates=dates,
        slots=slots,
        errors=errors,
        horizon=BOOKING_HORIZON_DAYS,
        min_date=dates[0].isoformat() if dates else "",
        max_date=dates[-1].isoformat() if dates else "",
        today=now.date().isoformat(),
    )


def _handle_post(conn, now, services, barbers) -> list[str]:
    """Create the booking; returns a list of customer-facing error messages."""
    from flask import session

    service = find_service(conn, request.form.get("service"))
    barber = find_barber(conn, request.form.get("barber"))
    day = _parse_day(request.form.get("date"))
    start = parse_local_datetime(
        request.form.get("date") or "", request.form.get("time") or ""
    )
    if start is None and day is not None:
        errors = [
            "That start time is not one we offer. Please choose a time from the list."
        ]
        return errors
    try:
        row = create_appointment(
            conn,
            barber_id=barber["id"] if barber else -1,
            service_id=service["id"] if service else -1,
            start_local=start,
            customer_name=request.form.get("name", ""),
            customer_email=request.form.get("email", ""),
            now=now,
        )
    except BookingError as exc:
        return [exc.message]
    session["last_booking_token"] = row["manage_token"]
    return []


@bp.route("/booked")
def booked():
    """Booking confirmation. Only readable with the private token in session."""
    from flask import session

    token = session.get("last_booking_token")
    row = find_by_token(get_db(), token) if token else None
    if row is None:
        return redirect(url_for("customer.home"))
    return render_template("booked.html", appt=row)


@bp.route("/manage")
def manage_entry():
    return render_template("manage_entry.html", error=None), 200


@bp.route("/manage/lookup", methods=("POST",))
def manage_lookup():
    raw = (request.form.get("token") or "").strip()
    token = raw.rstrip("/").rsplit("/", 1)[-1] if raw.startswith("http") else raw
    if find_by_token(get_db(), token) is None:
        # A friendly message here; the private view itself still 404s for bad links.
        return render_template(
            "manage_entry.html",
            error="We could not find a booking for that link. Check the whole link was pasted, "
                  "or ask the shop to look it up.",
        ), 404
    return redirect(url_for("customer.manage", token=token))


@bp.route("/manage/<token>")
def manage(token: str):
    row = find_by_token(get_db(), token)
    if row is None:
        abort(404)
    return render_template("manage.html", appt=row, error=None)


@bp.route("/manage/<token>/cancel", methods=("POST",))
def cancel(token: str):
    if find_by_token(get_db(), token) is None:
        abort(404)
    row, error = cancel_by_token(get_db(), token)
    if error:
        return render_template("manage.html", appt=row, error=error), 409
    return render_template("manage.html", appt=row, error=None, cancelled=True)


