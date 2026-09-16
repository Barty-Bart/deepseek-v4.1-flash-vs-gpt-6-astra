"""Admin dashboard: daily bookings, cancellations and staff unavailability."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from .bookings import find_barber, load_choices
from .config import SHOP_TZ
from .db import get_db, write_txn
from .scheduling import (
    block_conflict,
    fmt_datetime_long,
    fmt_time,
    iso_utc,
    local_now,
    parse_utc,
    to_utc,
)
from .security import admin_required, current_admin

bp = Blueprint("admin_panel", __name__, url_prefix="/admin")


def _parse_day(raw: str | None):
    try:
        return datetime.strptime(raw or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_local(day: str, hhmm: str):
    try:
        return datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=SHOP_TZ)
    except (TypeError, ValueError):
        return None


@bp.route("/")
@admin_required
def dashboard():
    conn = get_db()
    admin = current_admin()
    services, barbers = load_choices(conn)
    now = local_now()

    day = _parse_day(request.args.get("date")) or now.date()
    raw_barber = request.args.get("barber") or ""
    barber_filter = None
    if raw_barber:
        barber_filter = find_barber(conn, raw_barber)
        if barber_filter is None:
            flash("That barber filter is not valid.", "error")
            barber_filter = None

    sql = """
        SELECT a.*, b.name AS barber_name, s.name AS service_name,
               s.duration_minutes, s.price_cents
          FROM appointments a
          JOIN barbers b ON b.id = a.barber_id
          JOIN services s ON s.id = a.service_id
         WHERE a.start_utc >= ? AND a.start_utc < ?
    """
    params = [iso_utc(datetime.combine(day, datetime.min.time(), tzinfo=SHOP_TZ)),
              iso_utc(datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=SHOP_TZ))]
    if barber_filter is not None:
        sql += " AND a.barber_id = ?"
        params.append(barber_filter["id"])
    sql += " ORDER BY a.start_utc, b.sort_order"

    appointments = conn.execute(sql, params).fetchall()

    block_sql = """
        SELECT bl.*, b.name AS barber_name
          FROM blocks bl JOIN barbers b ON b.id = bl.barber_id
         WHERE bl.end_utc > ? AND bl.start_utc < ?
    """
    block_params = [params[0], params[1]]
    if barber_filter is not None:
        block_sql += " AND bl.barber_id = ?"
        block_params.append(barber_filter["id"])
    block_sql += " ORDER BY bl.start_utc"
    blocks = conn.execute(block_sql, block_params).fetchall()

    day_stats = {
        "confirmed": sum(1 for a in appointments if a["status"] == "confirmed"),
        "cancelled": sum(1 for a in appointments if a["status"] == "cancelled"),
        "revenue_cents": sum(
            a["price_cents"] for a in appointments if a["status"] == "confirmed"
        ),
    }

    return render_template(
        "admin_dashboard.html",
        admin=admin,
        appointments=appointments,
        blocks=blocks,
        barbers=barbers,
        services=services,
        day=day,
        barber_filter=barber_filter,
        day_stats=day_stats,
        prev_day=(day - timedelta(days=1)).isoformat(),
        next_day=(day + timedelta(days=1)).isoformat(),
        today=now.date().isoformat(),
        now_local=now,
    )


@bp.route("/appointments/<int:appointment_id>/cancel", methods=("POST",))
@admin_required
def cancel_appointment(appointment_id: int):
    conn = get_db()
    with write_txn(conn):
        row = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
        if row is None:
            flash("That appointment no longer exists.", "error")
        elif row["status"] != "confirmed":
            flash(f"{row['reference']} is already cancelled.", "info")
        else:
            conn.execute(
                "UPDATE appointments SET status = 'cancelled', cancelled_at_utc = ? WHERE id = ?",
                (iso_utc(local_now()), appointment_id),
            )
            flash(f"Cancelled {row['reference']}. The slot is available again.", "success")
    return redirect(_back_to_dashboard())


@bp.route("/blocks", methods=("POST",))
@admin_required
def create_block():
    conn = get_db()
    barber = find_barber(conn, request.form.get("barber"))
    day = request.form.get("date") or ""
    start_local = _parse_local(day, request.form.get("start") or "")
    end_local = _parse_local(day, request.form.get("end") or "")
    reason = (request.form.get("reason") or "").strip()[:120]

    errors: list[str] = []
    if barber is None:
        errors.append("Choose a barber for the unavailable period.")
    if start_local is None or end_local is None:
        errors.append("Enter a valid start and end time.")
    elif end_local <= start_local:
        errors.append("The end time must be after the start time.")
    elif start_local.date() != end_local.date():
        errors.append("A block must start and end on the same day.")

    if not errors:
        start_utc, end_utc = to_utc(start_local), to_utc(end_local)
        clash = block_conflict(conn, barber["id"], start_utc, end_utc)
        if clash is not None:
            errors.append(
                f"{barber['name']} already has a confirmed appointment {clash['reference']} at "
                f"{fmt_datetime_long(parse_utc(clash['start_utc']))} "
                f"({clash['customer_name']}, {clash['service_name']}). "
                "Cancel that appointment first, then add this unavailable period."
            )

    if errors:
        for message in errors:
            flash(message, "error")
        return redirect(_back_to_dashboard())

    with write_txn(conn):
        conn.execute(
            "INSERT INTO blocks (barber_id, start_utc, end_utc, reason, created_at_utc)"
            " VALUES (?, ?, ?, ?, ?)",
            (barber["id"], iso_utc(start_utc), iso_utc(end_utc), reason, iso_utc(local_now())),
        )
    flash(
        f"Added unavailability for {barber['name']} on {day} "
        f"{fmt_time(start_local)}–{fmt_time(end_local)}.",
        "success",
    )
    return redirect(_back_to_dashboard())


@bp.route("/blocks/<int:block_id>/delete", methods=("POST",))
@admin_required
def delete_block(block_id: int):
    conn = get_db()
    with write_txn(conn):
        row = conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
        if row is None:
            flash("That unavailable period no longer exists.", "error")
        else:
            conn.execute("DELETE FROM blocks WHERE id = ?", (block_id,))
            flash("Removed the unavailable period.", "success")
    return redirect(_back_to_dashboard())


def _back_to_dashboard() -> str:
    target = url_for("admin_panel.dashboard")
    query = []
    if request.form.get("return_date"):
        query.append(f"date={request.form['return_date']}")
    if request.form.get("return_barber"):
        query.append(f"barber={request.form['return_barber']}")
    return f"{target}?{'&'.join(query)}" if query else target


@bp.app_context_processor
def inject_helpers():
    return {"fmt_dt": fmt_datetime_long, "fmt_hhmm": fmt_time}
