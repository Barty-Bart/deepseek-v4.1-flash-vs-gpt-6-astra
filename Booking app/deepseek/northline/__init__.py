"""Northline Barber — a local appointment booking app for a fictional barber shop."""
from __future__ import annotations

import os
import secrets
from datetime import datetime
from pathlib import Path

import click
from flask import Flask, render_template, request

from . import admin_panel, auth, customer
from .config import Config
from .db import init_schema, open_standalone, write_txn

__version__ = "1.0.0"


def load_secret_key(path: Path) -> str:
    """Persist the session/CSRF secret locally, outside committed source.

    An explicit NORTHLINE_SECRET_KEY environment variable wins (used by tests);
    otherwise a 32-byte key is created on first run in the instance folder.
    """
    from_env = os.environ.get("NORTHLINE_SECRET_KEY")
    if from_env:
        return from_env
    path = Path(path)
    if path.exists():
        stored = path.read_text().strip()
        if stored:
            return stored
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(48)
    path.write_text(key + "\n")
    os.chmod(path, 0o600)
    return key


def create_app(config_object=Config, **overrides) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)
    app.config.update(overrides)

    app.config["DATABASE_PATH"] = Path(app.config["DATABASE_PATH"])
    app.config["INSTANCE_DIR"] = Path(app.config["INSTANCE_DIR"])
    app.config["SECRET_KEY"] = load_secret_key(Path(app.config["SECRET_KEY_FILE"]))

    from .db import init_app as init_db_app

    init_db_app(app)

    # Create any missing tables. Never seeds, never resets.
    with app.app_context():
        conn = open_standalone(app.config["DATABASE_PATH"])
        try:
            init_schema(conn)
        finally:
            conn.close()

    app.register_blueprint(customer.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin_panel.bp)

    register_csrf_guard(app)
    register_template_helpers(app)
    register_error_handlers(app)
    register_cli(app)
    return app


def register_csrf_guard(app: Flask) -> None:
    """Every unsafe request (POST/PUT/PATCH/DELETE) must carry a valid CSRF token."""
    from .security import csrf_protect

    @app.before_request
    def _csrf_guard():
        csrf_protect()


def register_template_helpers(app: Flask) -> None:
    from .scheduling import fmt_date_long, fmt_datetime_long, fmt_time, is_future, minutes
    from .security import csrf_token

    app.jinja_env.filters.update(
        local_dt=fmt_datetime_long,
        local_date=fmt_date_long,
        local_time=fmt_time,
        minutes=minutes,
        is_future=is_future,
    )
    app.jinja_env.globals["csrf_token"] = csrf_token


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", "That request could not be processed.")
        if request.path.startswith("/admin"):
            return render_template("error.html", title="Request rejected", message=message), 400
        return render_template("error.html", title="Something went wrong", message=message), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "error.html", title="Not allowed", message="You do not have access to that page."
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html",
            title="Page not found",
            message="That page or private link does not exist.",
        ), 404

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover - defensive
        return render_template(
            "error.html",
            title="Unexpected error",
            message="Something went wrong on our side. Please try again.",
        ), 500


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command():
        """Create any missing tables without touching existing data."""
        conn = open_standalone(app.config["DATABASE_PATH"])
        try:
            init_schema(conn)
        finally:
            conn.close()
        click.echo(f"Schema ready at {app.config['DATABASE_PATH']}")

    @app.cli.command("seed")
    def seed_command():
        """Insert reference data plus a small demo dataset (keeps existing data)."""
        from .seed import seed_database

        conn = open_standalone(app.config["DATABASE_PATH"])
        try:
            init_schema(conn)
            with write_txn(conn):
                created = seed_database(
                    conn, app.config["ADMIN_USERNAME"], app.config["ADMIN_PASSWORD"]
                )
        finally:
            conn.close()
        click.echo(
            "Seeded barbers, services and admin account. "
            f"Demo appointments created: {created['appointments']}, "
            f"demo blocks created: {created['blocks']}."
        )
        click.echo(f"Admin login: {app.config['ADMIN_USERNAME']} / {app.config['ADMIN_PASSWORD']}")

    @app.cli.command("reset")
    def reset_command():
        """Drop and rebuild every table, then re-seed. Destroys local data."""
        from .seed import drop_all, seed_database

        conn = open_standalone(app.config["DATABASE_PATH"])
        try:
            drop_all(conn)
            init_schema(conn)
            with write_txn(conn):
                created = seed_database(
                    conn, app.config["ADMIN_USERNAME"], app.config["ADMIN_PASSWORD"]
                )
        finally:
            conn.close()
        click.echo(
            f"Database reset at {app.config['DATABASE_PATH']}. "
            f"Demo appointments: {created['appointments']}, blocks: {created['blocks']}."
        )


def _abort_duplicate_process(port: int) -> None:
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(
                f"Port {port} on 127.0.0.1 is already in use. "
                "Start the other copy with a different PORT, for example PORT=5182 ./start.sh"
            )
    finally:
        probe.close()


def main() -> None:
    """Entry point for `python -m northline` / `./start.sh`."""
    port = int(os.environ.get("PORT", "5181"))
    host = "127.0.0.1"
    app = create_app()
    _abort_duplicate_process(port)
    click.echo(f"Northline Barber running at http://{host}:{port}/  (Ctrl-C to stop)")
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":  # pragma: no cover
    main()
