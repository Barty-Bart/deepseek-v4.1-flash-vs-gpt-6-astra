PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    duration INTEGER NOT NULL CHECK (duration > 0),
    price INTEGER NOT NULL CHECK (price >= 0)
);
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    start_hour INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_sessions (
    token_hash TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    token_hash TEXT NOT NULL UNIQUE,
    service_id INTEGER NOT NULL REFERENCES services(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL CHECK (ends_at > starts_at),
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    created_at TEXT NOT NULL,
    cancelled_at TEXT
);
CREATE INDEX IF NOT EXISTS bookings_schedule ON bookings(staff_id, status, starts_at, ends_at);
CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL CHECK (ends_at > starts_at),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS blocks_schedule ON blocks(staff_id, starts_at, ends_at);

INSERT OR IGNORE INTO services VALUES (1, 'Classic Cut', 30, 45);
INSERT OR IGNORE INTO services VALUES (2, 'Beard Trim', 15, 25);
INSERT OR IGNORE INTO services VALUES (3, 'Cut and Beard', 45, 65);
INSERT OR IGNORE INTO staff VALUES (1, 'Alex', 9);
INSERT OR IGNORE INTO staff VALUES (2, 'Jordan', 10);
INSERT OR IGNORE INTO schema_version(version) VALUES (1);
