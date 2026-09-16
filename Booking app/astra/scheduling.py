"""All scheduling decisions live here; every stored instant is UTC."""
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Australia/Melbourne')
UTC = timezone.utc


class BookingError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def utc_string(value):
    return value.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def local(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(TZ)


def parse_day(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value or ''):
        raise BookingError('Choose a valid appointment date.')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise BookingError('Choose a valid appointment date.') from None


def at_time(day, value):
    if not re.fullmatch(r'\d{2}:\d{2}', value or ''):
        raise BookingError('Choose a valid start time.')
    try:
        naive = datetime.combine(day, time.fromisoformat(value))
        result = naive.replace(tzinfo=TZ)
    except ValueError:
        raise BookingError('Choose a valid start time.') from None
    # Reject skipped and ambiguous wall times, including the DST transition.
    if result.astimezone(UTC).astimezone(TZ).replace(tzinfo=None) != naive:
        raise BookingError('That time does not exist in Melbourne. Choose another time.')
    if result.utcoffset() != result.replace(fold=1).utcoffset():
        raise BookingError('That time is ambiguous in Melbourne. Choose another time.')
    return result


def choices(db, service_id, staff_id):
    try:
        service_id, staff_id = int(service_id), int(staff_id)
    except (ValueError, TypeError):
        raise BookingError('Choose a valid service and barber.') from None
    service = db.execute('SELECT * FROM services WHERE id = ?', (service_id,)).fetchone()
    staff = db.execute('SELECT * FROM staff WHERE id = ?', (staff_id,)).fetchone()
    if service is None or staff is None:
        raise BookingError('Choose a valid service and barber.')
    return service, staff


def in_window(day, now):
    if not now.date() <= day <= (now + timedelta(days=30)).date():
        raise BookingError('Choose a date from today through the next 30 days.')


def slot_error(db, service, staff, start, now):
    end = start + timedelta(minutes=service['duration'])
    if start < now:
        return 'That time has already passed. Please choose a future time.'
    if start > now + timedelta(days=30):
        return 'Appointments open up to 30 days ahead. Please choose an earlier time.'
    if start.minute % 15 or start.second or start.microsecond:
        return 'Choose a time on the 15-minute grid.'
    if start.weekday() not in (1, 2, 3, 4, 5):
        return 'The shop is closed on Sundays and Mondays. Choose Tuesday to Saturday.'
    if start.time() < time(staff['start_hour']) or end.date() != start.date() or end.time() > time(17):
        return f"Your full service must fit within {staff['name']}’s working hours."
    if start.time() < time(13) and end.time() > time(12, 30):
        return 'Our barbers take a break from 12:30 to 1:00 pm. Choose another time.'
    params = (staff['id'], utc_string(end), utc_string(start))
    if db.execute("SELECT 1 FROM bookings WHERE staff_id = ? AND status = 'confirmed' AND starts_at < ? AND ends_at > ?", params).fetchone():
        return 'That time has just been booked. Choose another available time below.'
    if db.execute('SELECT 1 FROM blocks WHERE staff_id = ? AND starts_at < ? AND ends_at > ?', params).fetchone():
        return 'Your barber is unavailable at that time. Choose another available time below.'
    return None


def available_slots(db, service, staff, day, now):
    in_window(day, now)
    slots = []
    for minute in range(staff['start_hour'] * 60, 17 * 60, 15):
        start = datetime.combine(day, time(minute // 60, minute % 60), TZ)
        if slot_error(db, service, staff, start, now) is None:
            slots.append({'value': start.strftime('%H:%M'), 'label': time_label(start)})
    return slots


def time_label(dt):
    return dt.strftime('%I:%M %p').lstrip('0').lower()
