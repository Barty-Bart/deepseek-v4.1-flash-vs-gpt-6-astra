# Northline Barber

A complete localhost appointment book for a fictional Melbourne barber shop. Built with Flask, SQLite, server-rendered Jinja templates, local CSS and vanilla JavaScript. No external services, fonts, payments, email delivery or generated media.

## Setup and preview

Use Python 3.11 or later with the system IANA timezone database (verified here with Python 3.14.3 on macOS).

```sh
cd /path/to/astra
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app:create_app seed
./start.sh
```

Open **http://127.0.0.1:5181**. The server always binds to `127.0.0.1`, reads `PORT`, and defaults to `5181`.

For a second simultaneous process:

```sh
PORT=5182 ./start.sh
```

That process is available at http://127.0.0.1:5182. Processes started from this same project directory share its persistent database; a separate project checkout has its own database and secret. Use a separate browser profile for independent admin sessions when running the same app on two ports, since browser cookies are shared across ports on one hostname.

`start.sh` creates the project virtual environment if needed, installs the pinned runtime requirements, and starts Flask without debug mode. It never seeds or resets appointment data. Stop with Ctrl+C; start it again to continue with the same diary.

## Local staff account

- Sign in: **http://127.0.0.1:5181/admin**
- Username: **`admin`**
- Password: **`NorthlineLocal!2026`**

These are deliberate demo credentials created by the explicit seed command. The database stores a salted scrypt password hash, not the password. Login creates an opaque random session token whose hash and eight-hour expiry are stored in SQLite. Flask's signed, HTTP-only, SameSite=Lax cookie carries that token. Every admin request checks the server-side session record and expiry. Login rotates the session; logout revokes the database record, so replaying a saved cookie cannot restore access. All admin reads and mutations require authentication. All mutations, including customer booking/cancellation and login, require a session-bound CSRF token.

The application creates a cryptographically random persistent signing secret at `.local/secret_key` with owner-only permissions. It is outside source and excluded from Git. Neither ordinary startup nor seeding rotates it. The default SQLite database is `.local/northline.sqlite3`; `.local/` is excluded from Git too.

## Seed and reset

Add the admin, six fictional appointments, and two barber-specific unavailable periods relative to the seed date:

```sh
.venv/bin/python -m flask --app app:create_app seed
```

Appointments fall on the next three open days and use `example.com` addresses. Seeding is idempotent: if the seeded admin exists, it leaves existing records and credentials alone. It skips appointment slots that are already occupied. Seeded appointments intentionally do not disclose their private customer links; manage them through the admin dashboard.

To deliberately remove **all bookings, blocks and admins in this project's database**, then populate a fresh demo:

```sh
.venv/bin/python -m flask --app app:create_app reset-demo --yes
```

Without `--yes`, reset refuses to run. Reset is never part of startup or tests against the demo database. Stop preview processes before a manual reset.

## Customer walkthrough

1. Choose Classic Cut (30 min / AUD45), Beard Trim (15 min / AUD25), or Cut and Beard (45 min / AUD65).
2. Choose Alex or Jordan. Both work Tuesday–Saturday; Alex starts at 9 am, Jordan at 10 am, and both finish at 5 pm. Both take a 12:30–1 pm break.
3. Use the date strip or date picker, then choose an available time. Times are in Australia/Melbourne. Selection changes refresh availability and the appointment summary.
4. Enter a name and email, then confirm. The price and duration are visible before submission. No account or payment is required.
5. Save the private management link from the confirmation page. The local demo sends no email. The link shows only that appointment and permits cancellation before its start.
6. To cancel, open the link, expand the cancellation section and confirm. The record remains in the diary as cancelled and its time becomes available again.

The link contains a random 256-bit token, and only its SHA-256 hash is stored. Booking references and sequential database IDs cannot be used to look up customer bookings. Anyone with a private link can manage its appointment, so the page explains that the link should be kept private. Customer pages use no-store caching and no-referrer headers.

JavaScript is an enhancement. With it disabled, change your service/barber/date and press **Update available times**, then choose a time and confirm. This refresh uses POST so entered contact information stays out of query strings. The displayed private link can be copied manually.

## Admin walkthrough

Sign in through Staff access in the footer. Select a date and optionally a barber to see daily appointments, contact details, services, times, references and statuses. Future confirmed appointments can be cancelled. The cancelled record remains visible.

Use **Set some time aside** to add a barber-specific unavailable period on the 15-minute grid. An overlap with a confirmed appointment is rejected, identifying its customer, reference and start time so staff can handle it first. Overlapping unavailable periods are rejected too. Remove a block to release any otherwise available times. Standard working hours and breaks always apply.

The desktop appointment table becomes labelled appointment cards on phones, using the same markup and server routes. Customer details, time, service, barber, status and cancellation actions remain visible without horizontal scrolling. Block forms and filters use full-width phone controls with clear labels.

## Responsive navigation and date/time controls

The shared header stays visible while scrolling on every route. Its measured height sets the document's anchor clearance and the appointment sidebar's sticky offset. Focus scrolling keeps form controls and error summaries below the header, including reverse keyboard navigation. Reduced-motion preferences are respected.

Phones use a hamburger disclosure with an announced open/closed state. Tab and Shift+Tab move through its links, Escape closes it and returns focus, and clicking outside or moving focus into the page closes it. Changing to a desktop viewport restores the ordinary navigation. Without JavaScript, navigation links remain visible and retain header clearance.

Clicking anywhere inside a date/time input opens its selector. Chromium uses `showPicker()` directly during the user's click/tap; missing or rejected calls open an accessible calendar or a list of 15-minute times. WebKit uses that accessible selector directly because some WebKit versions expose the native method without reliably opening date/time UI. The adjacent calendar/clock button always offers the same explicit alternative, including in browsers whose native picker silently fails. Inputs remain editable by keyboard; Alt+Down or F4 opens their selector. Customer appointment times remain validated availability-only radio choices, never free-form time inputs.

The calendar supports month/year selection, keyboard arrow navigation, Escape and focus return. Date limits and shop-closed days are reflected in the calendar. Admin time choices respect the selected barber's opening hour and the 15-minute grid. The existing backend still checks all schedule rules and conflicts before accepting a booking or unavailable period.

## Scheduling and storage

- All persisted appointment/block instants use fixed-format UTC timestamps: `YYYY-MM-DDTHH:MM:SSZ`. All calendar rules and display use `zoneinfo.ZoneInfo('Australia/Melbourne')`.
- Starts must be on a 15-minute grid and between the current instant and the same local time 30 calendar days ahead. On the final date, later starts are unavailable. The entire service must fit within the barber's working hours and avoid breaks, blocks and confirmed appointments.
- Intervals are start-inclusive and end-exclusive. Adjacent appointments/blocks are allowed. Each barber has an independent schedule.
- `BEGIN IMMEDIATE` acquires SQLite's write lock **before** rechecking availability and inserting a booking or block. Competing overlapping requests cannot both commit. WAL mode and a 15-second busy timeout allow short concurrent transactions. A losing booking request gets a friendly HTTP 409 page with refreshed availability and preserved contact details.
- Cancellation checks and writes happen in a transaction, keep the original record and release its slot. Appointments that have started cannot be cancelled.
- Melbourne daylight-saving offsets are calculated for each date; skipped and ambiguous local input times are explicitly rejected. Scheduled shop hours do not fall within the transition hours.
- SQL is parameterized. Jinja escapes rendered data. Service, staff, date, start, contact details, block reason and permissions are checked on the server regardless of browser controls.
- `schema.sql` is the version-1 additive migration. `schema_version` records its application. Startup creates missing tables and fixed service/staff catalog entries only; it does not delete or reseed bookings. Future schema changes should add explicit ordered migrations.

## Verification

Install the pinned test/browser dependencies:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q --junitxml=reports/backend-tests.xml
```

Backend tests use an isolated temporary SQLite database for each test. They exercise restart persistence, service durations, hours/breaks/blocks, adjacency, exact and partial-overlap concurrent bookings, a concurrent block/booking race, cancellation, invalid/past requests, independent barbers, DST, CSRF, authentication, private-link isolation, filtering and explicit seed/reset behavior.

For the current responsive browser pass, keep the preview running on `PORT`, then run:

```sh
.venv/bin/python -m playwright install chromium webkit
.venv/bin/python scripts/verify_responsive.py
```

The responsive browser script checks Chromium and WebKit at desktop 1440×1000 and phone 393×852 / 402×874 sizes. It verifies sticky-header position, anchor/focus clearance, menu interaction and resize behaviour, field clicks at three positions, native-picker exceptions/missing support, fallback selection, manual entry, booking, stale-slot conflicts, cancellation, and admin blocked-period handling. It also checks a complete phone booking and cancellation with JavaScript disabled. Customer/admin mutation checks run against an isolated temporary database, removed afterwards. The actual preview is only inspected read-only; database records and the signing secret are compared before/after. Screenshots, raw results, a JSON report and measured verification runtime are saved in `reports/responsive-update/`. The original `scripts/verify_ui.py` and initial-build reports are preserved.

To verify simultaneous processes without changing appointment data, run `VERIFY_ALT_PORT=5183 .venv/bin/python scripts/verify_operation.py` while the main preview is running. The script starts and stops its own alternate preview, checks both responses, checks secret permissions and compares stored records. It defaults to alternate port 5182; this environment already had that port occupied, so the executed check used 5183. The optional `.local/restart-snapshot.json` is a baseline from the initial verification; remove it before rechecking after intentionally changing demo records.

Current results and browser limitations are recorded in [reports/responsive-update/VERIFICATION.md](reports/responsive-update/VERIFICATION.md). The original build's [verification record](reports/VERIFICATION.md) remains available. Raw output, JUnit XML, browser JSON, screenshots and verification scripts are preserved.

## Project files

| Path | Purpose |
| --- | --- |
| `app.py` | Application factory, public/admin routes, validation, sessions, CSRF and CLI commands |
| `scheduling.py` | Timezone conversion and shared availability rules |
| `db.py`, `schema.sql` | SQLite lifecycle, indexes and initial additive migration |
| `seed.py` | Explicit demo data and local staff credentials |
| `templates/` | Accessible server-rendered customer and staff screens |
| `static/` | Shared styles, responsive refinements, native/fallback controls, booking JavaScript and locally authored SVG illustration |
| `tests/` | Isolated backend integration and concurrency tests |
| `scripts/verify_responsive.py`, `scripts/verify_ui.py`, `reports/` | Reproducible browser checks and saved verification artifacts |
| `start.sh`, `requirements*.txt` | Local runner and pinned dependencies |

## Known limitations

This is a localhost V1 demo. It uses Flask's development server and a documented shared demo admin account. There are no confirmation emails, online payments, customer accounts, rescheduling, external calendars, staff management, CRM, analytics, password resets or public deployment.

Availability can change while a page is open. Final confirmation always checks the database again and returns refreshed times on conflict. Browser inspection covers Chromium and WebKit at the documented viewport sizes; it is not a physical iPhone, OS picker, software-keyboard or full screen-reader audit. Native Chromium picker activation is instrumented, while the in-page fallback selectors are exercised directly; OS-owned popup appearance is not claimed as visually verified. Font rendering uses system fonts and Georgia. Runtime needs the system IANA timezone database; macOS and mainstream Linux distributions provide it.
