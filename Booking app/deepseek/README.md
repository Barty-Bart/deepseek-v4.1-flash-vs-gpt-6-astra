# Northline Barber

A local appointment-booking site for a fictional Melbourne barber shop, built for a
benchmark run. Flask + SQLite + server-rendered Jinja, CSS and a small amount of
vanilla JavaScript. No frontend framework, no external services, no AI features.

The app runs only on `127.0.0.1` and keeps every record in a local SQLite file.

---

## Quick start

```bash
cd .

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Create the schema and load the demo data (run once).
.venv/bin/python -m flask --app northline:create_app seed

# Start the preview. PORT defaults to 5181.
PORT=5182 ./start.sh
```

Then open **<http://127.0.0.1:5182/>**.

`start.sh` uses the `PORT` environment variable, so a second copy of the project can
run at the same time on a different port:

```bash
PORT=5183 ./start.sh      # a third instance, next to the one on 5182
```

`start.sh` creates the virtual environment if it is missing and never resets or
re-seeds the database. If no database exists it prints the seed command and still
starts.

---

## Commands

| Command | What it does |
| --- | --- |
| `.venv/bin/python -m flask --app northline:create_app init-db` | Create any missing tables. Leaves existing data alone. |
| `.venv/bin/python -m flask --app northline:create_app seed` | Add reference data (barbers, services, admin) and, only when there are no appointments yet, a small set of demo appointments and staff blocks. Safe to re-run. |
| `.venv/bin/python -m flask --app northline:create_app reset` | **Destructive.** Drop and rebuild every table, then re-seed. |
| `.venv/bin/python -m pytest tests/ -q` | Run the backend test suite against a temporary database. |

Startup only creates missing tables. It never seeds and never resets.

---

## Local staff credentials

| Username | Password |
| --- | --- |
| `admin` | `northline-demo` |

Defined in `northline/config.py` and overridable with `NORTHLINE_ADMIN_USER` /
`NORTHLINE_ADMIN_PASSWORD` before a `reset` or `seed`. The password is stored as a
salted `scrypt` hash; the plaintext is never written to the database.

Sign in at <http://127.0.0.1:5182/admin/login>.

---

## Customer walkthrough

1. **Home** (`/`) — choose a service (Classic Cut 30 min AUD45, Beard Trim 15 min
   AUD25, Cut and Beard 45 min AUD65) and a barber (Alex or Jordan). Continue.
2. **Date and time** (`/book`) — pick a day from the horizontal date strip (or the
   date field), then a start time from the slots that are genuinely free. Slots are
   on a 15-minute grid and are computed around working hours, the 12:30–13:00 break,
   staff blocks and existing bookings. Each slot shows the time it ends.
3. **Your details** — name and email, validated on the server. The duration and the
   price are shown above the confirm button.
4. **Confirmation** (`/booked`) — a booking reference such as `NB-9NMKRU` and a
   private management link. The page states plainly that no email is sent.
5. **Manage** (`/manage/<private-token>`) — view the booking and cancel it. The
   private view shows only that one booking.

Private links carry 256 bits of randomness. They cannot be guessed, truncated or
enumerated, and one customer's link never exposes another customer's details.

### Local demo limitations

- **No confirmation emails are sent.** No mail service is configured or called.
- **No payments.** The price is displayed; nothing is ever charged and no card
  details are collected.
- **No password reset, no staff accounts beyond the single seeded admin, and no
  rescheduling** — rescheduling is deliberately out of scope for this version.
- **No external calendar sync.**

---

## Responsive layout and interaction

One codebase and one stylesheet serve desktop and phone; the phone layout is a set
of media queries at 900 px, 720 px and 560 px, not a separate app.

- **Sticky header.** The header is `position: sticky` with an opaque background at
  every width. JavaScript publishes its measured height as `--header-h`, which feeds
  `scroll-padding-top` on the document and `scroll-margin-top` on anchor targets, so
  jumping to `#book` or tabbing into a control never lands underneath it. The value
  is refreshed on resize and whenever the phone menu changes the header's height.
- **Phone menu.** At 720 px and below the three nav links collapse behind a
  disclosure button (`aria-expanded`, `aria-controls="site-nav"`). It closes on
  Escape with focus returned to the button, on a tap outside, and when the viewport
  becomes a desktop one. Without JavaScript the links simply remain visible.
- **Date and time fields.** Every `input[type=date]` and `input[type=time]` — the
  customer date field, the admin date and barber filters, and the unavailable-period
  date, from and to fields — opens its picker from a click anywhere on the field or
  its label, not just the small calendar icon. Where `showPicker()` does not exist
  the field takes focus instead, so the browser's own affordance and manual entry
  still work. Slot choice stays a fixed set of radio buttons; nothing becomes a
  free-form time field.
- **Phone refinements.** Single-column chooser cards, a three-across slot grid,
  full-width 46 px buttons and inputs, a compact Prev/Today/Next day-stepper, and the
  admin appointment table reflowed into one card per booking with its labels intact.
  Nothing overflows sideways at 393x852 or 402x874.

## Scheduling rules

- Shop hours Tuesday–Saturday, 09:00–17:00, in `Australia/Melbourne`.
- Alex works 09:00–17:00; Jordan starts at 10:00. Both break 12:30–13:00.
- Appointments start on a 15-minute grid and are bookable from now through the next
  30 days.
- Intervals are **start-inclusive, end-exclusive**, so a 13:00–13:30 booking and a
  13:30–14:00 booking are adjacent, not overlapping. Two barbers may be booked at
  the same time.
- A service must fit entirely inside working hours and outside the break, staff
  blocks and confirmed appointments.
- Timestamps are stored as ISO-8601 UTC and rendered in `Australia/Melbourne`.
  Daylight saving is handled through `zoneinfo`, including the October change.
- Every rule is re-validated on the server; the browser controls are a convenience
  only. Past slots, off-grid times, unknown services/barbers and closed days are all
  rejected server-side.
- Cancelling preserves the row, marks it `cancelled` and releases the slot.

### Concurrency

`create_appointment` opens a single `BEGIN IMMEDIATE` transaction and re-checks for
overlaps inside it. SQLite serialises the writers, so of two simultaneous requests
for an overlapping slot exactly one commits; the other is rejected with a friendly
"that time was just taken" message and a freshly rendered list of free times. A test
races eight independent connections at the same slot and asserts a single winner.

---

## Admin

The staff area is protected by a real server session (`admin_user_id` in a signed,
HttpOnly, SameSite=Lax cookie), a hashed password, and a CSRF token that every
unsafe request must carry. Both the admin pages and every admin mutation endpoint
are guarded; an unauthenticated request is redirected to the login form and never
sees or changes booking data.

The dashboard shows one day at a time, filterable by date and barber, with each
booking's customer, service, time, reference and status. Staff can:

- cancel a booking (the slot is released immediately),
- add a staff-specific unavailable period,
- remove an unavailable period.

A block that would overlap a confirmed appointment is rejected with the reference
of the appointment that must be handled first. Blocks, invalid times and missing
fields all report a clear error and change nothing.

---

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

62 tests across five files, all against an isolated temporary SQLite database
(`tmp_path`); the demo database is never opened or modified by the suite.

| File | Coverage |
| --- | --- |
| `tests/test_scheduling.py` | Working hours, the 12:30–13:00 break, seeded blocks, the 15-minute grid, service durations, the 30-day horizon, closed days, past slots, adjacent bookings, independent barbers, the daylight-saving offset. |
| `tests/test_booking.py` | Booking persistence across an application restart, confirmation, cancellation releasing the slot, double-cancellation, past appointments, validation errors, CSRF, private-link enumeration and isolation, and the friendly unknown-link message. |
| `tests/test_concurrency.py` | Two simultaneous HTTP requests for one slot (exactly one wins), adjacent concurrent requests (both win), eight connections racing at the database layer, conflict-page refresh. |
| `tests/test_admin.py` | Unauthenticated read and write protection, login failures, session rotation, hashed passwords, CSRF enforcement, dashboard filters, cancellation, block validation and block creation/removal. |
| `tests/test_layout.py` | Structural guards for the responsive work: the sticky-header and anchor-offset CSS, the menu button's ARIA wiring on every page, the no-JS fallback, the card-reflow hooks on the admin table, and that date/time controls stay native while slots stay fixed radios. |

### Browser check

```bash
# Point it at an isolated instance so the demo database is never touched:
NORTHLINE_INSTANCE_DIR=/tmp/northline-verify .venv/bin/python -m flask --app northline:create_app seed
NORTHLINE_INSTANCE_DIR=/tmp/northline-verify PORT=5190 ./start.sh &
PORT=5190 .venv/bin/python reports/browser_check.py
```

Drives headless Chrome over the ChromeDriver HTTP API against a running server. It
writes screenshots to `reports/screenshots/` **and** runs real assertions, exiting
non-zero if any fail:

- the header is `position: sticky`, stays pinned after scrolling, publishes
  `--header-h`, and its `scroll-padding` clears it for anchors and focused fields
- no page scrolls sideways at 1440 px, 393x852 or 402x874
- the phone menu opens, closes on Escape with focus restored, and closes on an
  outside tap
- clicking the middle of a date/time field — or its label — opens the picker, and
  the field still takes focus when the browser has no `showPicker()`
- interactive controls meet the 44 px touch target on phones
- the admin table reflows to one card per booking on phones and stays a table on
  desktop
- a booking completes through the real form, the booked slot leaves availability,
  a second attempt at the same slot is refused, and cancelling releases it again

Phone viewports are set with the DevTools protocol device-metrics override, because
a real macOS window cannot be narrower than about 500 px. The script finds (and, if
necessary, downloads into `reports/.cache/`) a ChromeDriver matching the installed
Chrome, and creates demo bookings in whatever database the target server uses.

---

## Layout

```
northline/
  __init__.py       app factory, secret handling, error pages, CLI commands
  config.py         timezone, hours, break, grid, horizon, paths
  db.py             connections, schema bootstrap, BEGIN IMMEDIATE helper
  schema.sql        SQLite schema
  scheduling.py     timezone maths, availability, backend validation
  bookings.py       validation and creation/cancellation of appointments
  security.py       CSRF, admin session helpers
  auth.py           admin login/logout
  admin_panel.py    staff dashboard, cancellations, unavailable periods
  customer.py       the customer booking journey
  seed.py           demo data and reset helpers
  templates/        Jinja templates
  static/           CSS, a small enhancement script, favicon
tests/              pytest suite with an isolated temporary database
reports/            browser check script, rendered screenshots, verification report
instance/           local SQLite database and secret key (git-ignored)
```

The Flask session secret is generated on first run and stored in
`instance/secret_key` with `0600` permissions. It lives outside the committed source
tree, so sessions survive ordinary restarts but no key is ever checked in.

## Known limitations

- Flask's development server is used deliberately; this is a localhost demo, not a
  deployment.
- The staff dashboard shows one calendar day at a time.
- Chrome is the browser the layout and picker behaviour were verified in; Safari and
  Firefox were not exercised here. `showPicker()` is used where available and the
  field falls back to focus + select where it is not.
- Only Alex and Jordan exist, with fixed working hours; there is no staff-management
  UI, by design.
- Recurring blocks (for example "every Tuesday morning") are not supported — each
  unavailable period is entered individually.
