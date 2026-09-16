"""Explicit, idempotent demo seed. Nothing here runs during server startup."""
import hashlib
import secrets
from datetime import timedelta

from werkzeug.security import generate_password_hash

from scheduling import at_time, available_slots, slot_error, utc_string

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'NorthlineLocal!2026'


def seed_database(db, now):
    db.execute('BEGIN IMMEDIATE')
    try:
        if db.execute('SELECT 1 FROM admins WHERE username = ?', (ADMIN_USERNAME,)).fetchone():
            db.rollback()
            return 'Demo already seeded. Existing appointments and credentials were preserved.'
        db.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)',
                   (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)))
        days = []
        for offset in range(1, 8):
            day = now.date() + timedelta(days=offset)
            if day.weekday() in (1, 2, 3, 4, 5):
                days.append(day)
            if len(days) == 3:
                break
        people = [('Sam Taylor', 'sam.taylor@example.com'), ('Charlie Lee', 'charlie.lee@example.com'),
                  ('Riley Morgan', 'riley.morgan@example.com'), ('Casey Park', 'casey.park@example.com'),
                  ('Jamie Ellis', 'jamie.ellis@example.com'), ('Drew Wilson', 'drew.wilson@example.com')]
        count = 0
        for index, (name, email) in enumerate(people):
            service = db.execute('SELECT * FROM services WHERE id = ?', (index % 3 + 1,)).fetchone()
            staff = db.execute('SELECT * FROM staff WHERE id = ?', (index % 2 + 1,)).fetchone()
            day = days[index // 2]
            slots = available_slots(db, service, staff, day, now)
            if not slots:
                continue
            start = at_time(day, slots[min(4 + index, len(slots) - 1)]['value'])
            db.execute('INSERT INTO bookings (reference, token_hash, service_id, staff_id, customer_name, customer_email, starts_at, ends_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       ('NL-' + secrets.token_hex(4).upper(), hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest(),
                        service['id'], staff['id'], name, email, utc_string(start),
                        utc_string(start + timedelta(minutes=service['duration'])), utc_string(now)))
            count += 1
        for staff_id, day, begin, finish, reason in [(1, days[0], '14:00', '15:00', 'Equipment maintenance'),
                                                    (2, days[1], '15:00', '16:00', 'Personal appointment')]:
            start, end = at_time(day, begin), at_time(day, finish)
            staff = db.execute('SELECT * FROM staff WHERE id = ?', (staff_id,)).fetchone()
            if slot_error(db, {'duration': 60}, staff, start, now) is None:
                db.execute('INSERT INTO blocks (staff_id, starts_at, ends_at, reason, created_at) VALUES (?, ?, ?, ?, ?)',
                           (staff_id, utc_string(start), utc_string(end), reason, utc_string(now)))
        db.commit()
        return f'Seeded {count} fictional appointments, staff blocks and the local admin. See README.md for credentials.'
    except Exception:
        db.rollback()
        raise
