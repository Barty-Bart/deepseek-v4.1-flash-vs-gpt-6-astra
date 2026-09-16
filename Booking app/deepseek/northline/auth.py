"""Admin authentication: password hashing, login, logout, session lifecycle."""
from __future__ import annotations

import secrets

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .security import (
    ADMIN_SESSION_KEY,
    admin_required,
    current_admin,
    rotate_csrf_token,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")

# A real dummy hash keeps login timing similar for unknown usernames.
_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(24))


def _safe_next(target: str | None) -> str:
    """Only ever redirect back into our own admin area."""
    if target and target.startswith("/admin") and not target.startswith("//"):
        return target
    return url_for("admin_panel.dashboard")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_admin() is not None:
        return redirect(url_for("admin_panel.dashboard"))

    error = None
    username = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        row = get_db().execute(
            "SELECT id, username, password_hash FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            check_password_hash(_DUMMY_HASH, password)
            error = "Incorrect username or password."
        elif not check_password_hash(row["password_hash"], password):
            error = "Incorrect username or password."
        else:
            session.clear()
            session[ADMIN_SESSION_KEY] = row["id"]
            session.permanent = True
            rotate_csrf_token()
            return redirect(_safe_next(request.args.get("next")))

    return render_template("admin_login.html", error=error, username=username), (401 if error else 200)


@bp.route("/logout", methods=("POST",))
@admin_required
def logout():
    session.clear()
    return redirect(url_for("admin.login"))
