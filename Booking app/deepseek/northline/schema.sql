-- Northline Barber — SQLite schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS barbers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    work_start  TEXT    NOT NULL,           -- local 'HH:MM'
    work_end    TEXT    NOT NULL,           -- local 'HH:MM'
    active      INTEGER NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS services (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL UNIQUE,
    duration_minutes INTEGER NOT NULL,
    price_cents      INTEGER NOT NULL,
    active           INTEGER NOT NULL DEFAULT 1,
    sort_order       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    reference        TEXT    NOT NULL UNIQUE,
    manage_token     TEXT    NOT NULL UNIQUE,
    barber_id        INTEGER NOT NULL REFERENCES barbers(id),
    service_id       INTEGER NOT NULL REFERENCES services(id),
    customer_name    TEXT    NOT NULL,
    customer_email   TEXT    NOT NULL,
    start_utc        TEXT    NOT NULL,      -- ISO-8601 UTC
    end_utc          TEXT    NOT NULL,      -- ISO-8601 UTC, exclusive
    status           TEXT    NOT NULL DEFAULT 'confirmed'
                     CHECK (status IN ('confirmed', 'cancelled')),
    created_at_utc   TEXT    NOT NULL,
    cancelled_at_utc TEXT
);

CREATE INDEX IF NOT EXISTS idx_appointments_barber_start
    ON appointments (barber_id, start_utc);
CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON appointments (status, start_utc);

CREATE TABLE IF NOT EXISTS blocks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id  INTEGER NOT NULL REFERENCES barbers(id),
    start_utc  TEXT    NOT NULL,
    end_utc    TEXT    NOT NULL,
    reason     TEXT    NOT NULL DEFAULT '',
    created_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_blocks_barber_start
    ON blocks (barber_id, start_utc);

CREATE TABLE IF NOT EXISTS admin_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at_utc TEXT   NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
