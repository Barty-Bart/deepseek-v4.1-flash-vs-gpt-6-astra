"""CSRF protection and admin session helpers."""
from __future__ import annotations

import hmac
import secrets
from functools import wraps

from flask import abort, redirect, request, session, url_for

CSRF_SESSION_KEY = "_csrf_token"
ADMIN_SESSION_KEY = "admin_user_id"


def csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session[CSRF_SESSION_KEY] = token
    return token


def csrf_protect() -> None:
    """Reject any unsafe request whose token does not match the session."""
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
    expected = session.get(CSRF_SESSION_KEY)
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(400, description="Your session expired or the form was stale. Please reload the page and try again.")


def current_admin():
    from .db import get_db

    admin_id = session.get(ADMIN_SESSION_KEY)
    if not admin_id:
        return None
    return get_db().execute(
        "SELECT id, username FROM admin_users WHERE id = ?", (admin_id,)
    ).fetchone()


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_admin() is None:
            # Never leak whether a resource exists to an unauthenticated caller.
            return redirect(url_for("admin.login", next=request.path)), 302
        return view(*args, **kwargs)

    return wrapper
