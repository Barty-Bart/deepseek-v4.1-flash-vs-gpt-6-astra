"""Application configuration and shared constants."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Timezone -----------------------------------------------------------------
SHOP_TZ = ZoneInfo("Australia/Melbourne")
SHOP_TZ_NAME = "Australia/Melbourne"

# --- Scheduling rules ---------------------------------------------------------
OPEN_TIME = "09:00"          # shop opens Tuesday–Saturday
CLOSE_TIME = "17:00"
BREAK_START = "12:30"        # every barber's unpaid break
BREAK_END = "13:00"
OPEN_WEEKDAYS = {1, 2, 3, 4, 5}   # Monday=0 → Tuesday..Saturday
SLOT_STEP_MINUTES = 15
BOOKING_HORIZON_DAYS = 30


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


class Config:
    # Instance folder holds the SQLite file and the local application secret.
    # It is deliberately outside the committed source tree.
    INSTANCE_DIR = _env_path("NORTHLINE_INSTANCE_DIR", PROJECT_ROOT / "instance")
    DATABASE_PATH = _env_path("NORTHLINE_DB", INSTANCE_DIR / "northline.sqlite")
    SECRET_KEY_FILE = _env_path("NORTHLINE_SECRET_FILE", INSTANCE_DIR / "secret_key")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "northline_session"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours
    MAX_CONTENT_LENGTH = 256 * 1024

    ADMIN_USERNAME = os.environ.get("NORTHLINE_ADMIN_USER", "admin")
    ADMIN_PASSWORD = os.environ.get("NORTHLINE_ADMIN_PASSWORD", "northline-demo")
