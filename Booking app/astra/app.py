import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, time, timedelta
from functools import wraps
from pathlib import Path

import click
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from db import close_db, get_db, init_database
from scheduling import BookingError, TZ, UTC, at_time, available_slots, choices, in_window, local, parse_day, slot_error, time_label, utc_string

ROOT = Path(__file__).resolve().parent


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=str(ROOT / '.local' / 'northline.sqlite3'),
        SECRET_KEY=None,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_NAME='northline_session',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=32 * 1024,
        NOW=lambda: datetime.now(TZ),
    )
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY']:
        secret_file = ROOT / '.local' / 'secret_key'
        secret_file.parent.mkdir(exist_ok=True)
        try:
            fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w') as stream:
                stream.write(secrets.token_hex(32))
        app.config['SECRET_KEY'] = secret_file.read_text().strip()
    init_database(app.config['DATABASE'])
    app.teardown_appcontext(close_db)

    def now():
        return app.config['NOW']().astimezone(TZ)

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    @app.context_processor
    def context():
        return {'csrf_token': csrf_token, 'current_year': now().year, 'time_label': time_label, 'local': local}

    @app.before_request
    def csrf_protect():
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            supplied = request.form.get('csrf_token', '')
            expected = session.get('csrf', '')
            if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
                abort(400, description='This form has expired. Refresh the page and try again.')

    @app.after_request
    def security_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            token = session.get('admin_session', '')
            active = get_db().execute('SELECT 1 FROM admin_sessions a JOIN admins u ON u.id = a.admin_id WHERE a.token_hash = ? AND a.expires_at > ?',
                                      (hashlib.sha256(token.encode()).hexdigest(), utc_string(now()))).fetchone() if token else None
            if not active:
                session.pop('admin_session', None)
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    def booking_page(values=None, errors=None, status=200):
        values = dict(values or {})
        current = now()
        db = get_db()
        services = db.execute('SELECT * FROM services ORDER BY id').fetchall()
        staff = db.execute('SELECT * FROM staff ORDER BY id').fetchall()
        try:
            service, barber = choices(db, values.get('service', 1), values.get('staff', 1))
        except BookingError:
            service, barber = services[0], staff[0]
        try:
            day = parse_day(values.get('date', current.date().isoformat()))
            in_window(day, current)
        except BookingError:
            day = current.date()
        # On a fresh visit start on the next day with availability.
        if not values:
            for offset in range(31):
                candidate = current.date() + timedelta(days=offset)
                if available_slots(db, service, barber, candidate, current):
                    day = candidate
                    break
        values.update(service=str(service['id']), staff=str(barber['id']), date=day.isoformat())
        slots = available_slots(db, service, barber, day, current)
        days = [current.date() + timedelta(days=i) for i in range(31)]
        return render_template('index.html', services=services, barbers=staff, selected_service=service,
                               selected_barber=barber, selected_date=day, values=values, slots=slots,
                               days=days, today=current.date(), max_date=days[-1], errors=errors or []), status

    @app.get('/')
    def index():
        return booking_page(request.args)

    @app.post('/availability')
    def refresh_booking():
        values = request.form.to_dict()
        values.pop('slot', None)
        return booking_page(values)

    @app.get('/api/availability')
    def availability():
        try:
            service, staff = choices(get_db(), request.args.get('service'), request.args.get('staff'))
            day = parse_day(request.args.get('date'))
            slots = available_slots(get_db(), service, staff, day, now())
            return jsonify(slots=slots, date=day.isoformat(), date_label=day.strftime('%A, %-d %B'), timezone='Australia/Melbourne')
        except BookingError as error:
            return jsonify(error=str(error)), error.status

    @app.post('/book')
    def book():
        values = request.form.to_dict()
        errors = []
        name = values.get('name', '').strip()
        email = values.get('email', '').strip()
        if not 2 <= len(name) <= 80 or any(ord(c) < 32 for c in name):
            errors.append('Enter your name using 2–80 characters.')
        if len(email) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>.]+(?:\.[^\s@<>.]+)+", email):
            errors.append('Enter a valid email address, such as you@example.com.')
        if errors:
            values.pop('slot', None)
            return booking_page(values, errors, 400)
        db = get_db()
        try:
            service, staff = choices(db, values.get('service'), values.get('staff'))
            day = parse_day(values.get('date'))
            start = at_time(day, values.get('slot'))
            db.execute('BEGIN IMMEDIATE')
            current = now()
            in_window(day, current)
            error = slot_error(db, service, staff, start, current)
            if error:
                raise BookingError(error, 409)
            token = secrets.token_urlsafe(32)
            reference = 'NL-' + secrets.token_hex(4).upper()
            db.execute('INSERT INTO bookings (reference, token_hash, service_id, staff_id, customer_name, customer_email, starts_at, ends_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (reference, hashlib.sha256(token.encode()).hexdigest(), service['id'], staff['id'], name, email,
                        utc_string(start), utc_string(start + timedelta(minutes=service['duration'])), utc_string(current)))
            db.commit()
        except BookingError as error:
            if db.in_transaction:
                db.rollback()
            values.pop('slot', None)
            return booking_page(values, [str(error)], error.status)
        except sqlite3.OperationalError:
            if db.in_transaction:
                db.rollback()
            values.pop('slot', None)
            return booking_page(values, ['The diary is busy just now. Refresh availability and try again.'], 409)
        flash('You’re booked in. We look forward to seeing you.', 'success')
        return redirect(url_for('manage', token=token), code=303)

    def private_booking(token):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            abort(404)
        booking = get_db().execute('SELECT b.*, s.name AS service_name, s.duration, s.price, st.name AS staff_name FROM bookings b JOIN services s ON s.id = b.service_id JOIN staff st ON st.id = b.staff_id WHERE b.token_hash = ?',
                                   (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if booking is None:
            abort(404)
        return booking

    @app.get('/booking/<token>')
    def manage(token):
        booking = private_booking(token)
        return render_template('manage.html', booking=booking, token=token,
                               can_cancel=booking['status'] == 'confirmed' and local(booking['starts_at']) > now())

    @app.post('/booking/<token>/cancel')
    def cancel_booking(token):
        db = get_db()
        db.execute('BEGIN IMMEDIATE')
        try:
            booking = private_booking(token)
            current = now()
            if booking['status'] != 'confirmed' or local(booking['starts_at']) <= current:
                flash('Only a confirmed future appointment can be cancelled.', 'error')
            else:
                db.execute("UPDATE bookings SET status = 'cancelled', cancelled_at = ? WHERE id = ?", (utc_string(current), booking['id']))
                flash('Your appointment is cancelled. The time is available again.', 'success')
            db.commit()
        except Exception:
            db.rollback()
            raise
        return redirect(url_for('manage', token=token), code=303)

    @app.route('/admin/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            admin = get_db().execute('SELECT * FROM admins WHERE username = ?', (request.form.get('username', ''),)).fetchone()
            if admin and check_password_hash(admin['password_hash'], request.form.get('password', '')):
                db = get_db()
                old_token = session.get('admin_session', '')
                db.execute('DELETE FROM admin_sessions WHERE token_hash = ? OR expires_at <= ?',
                           (hashlib.sha256(old_token.encode()).hexdigest(), utc_string(now())))
                token = secrets.token_urlsafe(32)
                db.execute('INSERT INTO admin_sessions (token_hash, admin_id, expires_at) VALUES (?, ?, ?)',
                           (hashlib.sha256(token.encode()).hexdigest(), admin['id'], utc_string(now().astimezone(UTC) + timedelta(hours=8))))
                session.clear()
                session['admin_session'] = token
                session.permanent = True
                return redirect(url_for('admin_dashboard'), code=303)
            error = 'The username or password is incorrect. Please try again.'
        return render_template('login.html', error=error), 401 if error else 200

    @app.post('/admin/logout')
    @admin_required
    def logout():
        get_db().execute('DELETE FROM admin_sessions WHERE token_hash = ?',
                         (hashlib.sha256(session['admin_session'].encode()).hexdigest(),))
        session.clear()
        return redirect(url_for('login'), code=303)

    def dashboard_data(values=None, errors=None):
        values = dict(values or request.args)
        db = get_db()
        errors = list(errors or [])
        try:
            day = parse_day(values.get('date', now().date().isoformat()))
            if not 2000 <= day.year <= 2100:
                raise BookingError('Choose a date between 2000 and 2100.')
        except BookingError as error:
            errors.append(str(error))
            day = now().date()
        barber_filter = values.get('staff', '')
        if barber_filter not in ('', '1', '2'):
            errors.append('Choose a valid barber filter.')
            barber_filter = ''
        start = datetime.combine(day, time.min, TZ)
        end = start + timedelta(days=1)
        params = [utc_string(start), utc_string(end)]
        where = 'b.starts_at >= ? AND b.starts_at < ?'
        if barber_filter:
            where += ' AND b.staff_id = ?'
            params.append(int(barber_filter))
        bookings = db.execute('SELECT b.*, s.name AS service_name, s.duration, s.price, st.name AS staff_name FROM bookings b JOIN services s ON s.id = b.service_id JOIN staff st ON st.id = b.staff_id WHERE ' + where + ' ORDER BY b.starts_at', params).fetchall()
        block_params = [utc_string(end), utc_string(start)]
        block_where = 'b.starts_at < ? AND b.ends_at > ?'
        if barber_filter:
            block_where += ' AND b.staff_id = ?'
            block_params.append(int(barber_filter))
        blocks = db.execute('SELECT b.*, st.name AS staff_name FROM blocks b JOIN staff st ON st.id = b.staff_id WHERE ' + block_where + ' ORDER BY b.starts_at', block_params).fetchall()
        return dict(bookings=bookings, blocks=blocks, date=day, staff_filter=barber_filter,
                    barbers=db.execute('SELECT * FROM staff').fetchall(), errors=errors,
                    form_values=values, now=now(), max_block_date=(now() + timedelta(days=30)).date(),
                    confirmed_count=sum(b['status'] == 'confirmed' for b in bookings))

    @app.get('/admin')
    @admin_required
    def admin_dashboard():
        data = dashboard_data()
        return render_template('admin.html', **data), 400 if data['errors'] else 200

    def admin_redirect():
        return redirect(url_for('admin_dashboard', date=request.form.get('date', now().date().isoformat()), staff=request.form.get('filter_staff', '')), code=303)

    @app.post('/admin/bookings/<int:booking_id>/cancel')
    @admin_required
    def admin_cancel(booking_id):
        db = get_db()
        db.execute('BEGIN IMMEDIATE')
        booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
        if booking is None:
            db.rollback()
            abort(404)
        current = now()
        if booking['status'] != 'confirmed' or local(booking['starts_at']) <= current:
            db.rollback()
            flash('Only a confirmed future appointment can be cancelled.', 'error')
        else:
            db.execute("UPDATE bookings SET status = 'cancelled', cancelled_at = ? WHERE id = ?", (utc_string(current), booking_id))
            db.commit()
            flash(f"Booking {booking['reference']} has been cancelled.", 'success')
        return admin_redirect()

    @app.post('/admin/blocks')
    @admin_required
    def create_block():
        db = get_db()
        try:
            _, staff = choices(db, 1, request.form.get('block_staff'))
            day = parse_day(request.form.get('date'))
            start = at_time(day, request.form.get('start'))
            end = at_time(day, request.form.get('end'))
            reason = request.form.get('reason', '').strip()
            if not 2 <= len(reason) <= 120 or any(ord(c) < 32 for c in reason):
                raise BookingError('Add a short reason using 2–120 characters.')
            if end <= start:
                raise BookingError('The end time must be after the start time.')
            db.execute('BEGIN IMMEDIATE')
            current = now()
            in_window(day, current)
            if start < current:
                raise BookingError('Unavailable periods must start in the future.')
            if day.weekday() not in (1, 2, 3, 4, 5) or start.time() < time(staff['start_hour']) or end.time() > time(17):
                raise BookingError(f"Choose a period within {staff['name']}’s Tuesday–Saturday working hours.")
            if start.minute % 15 or end.minute % 15:
                raise BookingError('Start and end times must be on the 15-minute grid.')
            params = (staff['id'], utc_string(end), utc_string(start))
            overlap = db.execute("SELECT reference, customer_name, starts_at FROM bookings WHERE staff_id = ? AND status = 'confirmed' AND starts_at < ? AND ends_at > ? ORDER BY starts_at LIMIT 1", params).fetchone()
            if overlap:
                raise BookingError(f"This overlaps {overlap['customer_name']}’s appointment ({overlap['reference']}) at {time_label(local(overlap['starts_at']))}. Cancel that appointment first if this time needs to be blocked.", 409)
            if db.execute('SELECT 1 FROM blocks WHERE staff_id = ? AND starts_at < ? AND ends_at > ?', params).fetchone():
                raise BookingError('This overlaps an existing unavailable period. Remove it first or choose another time.', 409)
            db.execute('INSERT INTO blocks (staff_id, starts_at, ends_at, reason, created_at) VALUES (?, ?, ?, ?, ?)',
                       (staff['id'], utc_string(start), utc_string(end), reason, utc_string(current)))
            db.commit()
        except BookingError as error:
            if db.in_transaction:
                db.rollback()
            return render_template('admin.html', **dashboard_data(request.form, [str(error)])), error.status
        except sqlite3.OperationalError:
            if db.in_transaction:
                db.rollback()
            return render_template('admin.html', **dashboard_data(request.form, ['The diary is busy. Please try again.'])), 409
        flash(f"Unavailable period added for {staff['name']}.", 'success')
        return admin_redirect()

    @app.post('/admin/blocks/<int:block_id>/delete')
    @admin_required
    def delete_block(block_id):
        cursor = get_db().execute('DELETE FROM blocks WHERE id = ?', (block_id,))
        if not cursor.rowcount:
            abort(404)
        flash('Unavailable period removed. Free times can be booked again.', 'success')
        return admin_redirect()

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def friendly_error(error):
        descriptions = {404: 'We couldn’t find that page. If you’re managing a booking, use the full private link you saved.',
                        413: 'That form is too large. Please use shorter details and try again.'}
        return render_template('error.html', code=error.code, message=descriptions.get(error.code, error.description)), error.code

    @app.cli.command('seed')
    def seed_command():
        """Add fictional demo appointments and the local admin; safe to repeat."""
        from seed import seed_database
        click.echo(seed_database(get_db(), now()))

    @app.cli.command('reset-demo')
    @click.option('--yes', is_flag=True, help='Required explicit confirmation that all bookings should be removed.')
    def reset_command(yes):
        """Destructively clear this database and reseed it. Never run at startup."""
        if not yes:
            raise click.ClickException('Reset removes all bookings, blocks and admins. Run reset-demo --yes to confirm.')
        from seed import seed_database
        db = get_db()
        db.execute('BEGIN IMMEDIATE')
        for table in ('bookings', 'blocks', 'admins'):
            db.execute(f'DELETE FROM {table}')
        db.commit()
        click.echo(seed_database(db, now()))

    return app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5181'))
    create_app().run(host='127.0.0.1', port=port, debug=False)
