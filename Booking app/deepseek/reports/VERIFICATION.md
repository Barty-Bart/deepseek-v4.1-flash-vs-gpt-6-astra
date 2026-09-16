# Verification report — Northline Barber

Date: 15 September 2026 · Host: macOS (arm64) · Python 3.14.3 · Flask 3.1.0 · SQLite (stdlib)
Last revision: sticky header, click-anywhere date/time pickers, phone layout and menu

Everything below was executed. No result here is projected or assumed.

---

## 1. Backend test suite

```
$ .venv/bin/python -m pytest tests/ -q
..............................................................           [100%]
62 passed in 5.07s          (real 5.42s)
```

Isolation: every test builds its own database under pytest's `tmp_path` and passes
`DATABASE_PATH` into the app factory. The demo database was hashed before and after a
full run — the digest was identical, so the suite never touches `instance/northline.sqlite`.

| Required check | Test |
| --- | --- |
| Booking persistence across an application restart | `test_booking_persists_across_application_restart` builds a second app over the same file and reads the booking through its private link |
| Differing service durations | `test_durations_change_what_fits` (15 / 30 / 45 min), `test_combo_rejected_when_it_would_cross_closing` |
| Working hours | `test_slots_respect_working_hours_and_break`, `test_off_grid_and_out_of_hours_requests_rejected` |
| Breaks | `test_break_is_enforced_on_the_backend` |
| Blocks | `test_seeded_block_removes_slots_and_rejects_backend_requests`, `test_block_creation_and_removal` |
| Concurrent conflicting requests (exactly one succeeds) | `test_concurrent_overlapping_requests_only_one_wins` (2 HTTP clients), `test_many_connections_racing_the_same_slot` (8 SQLite connections → 1 ok, 7 conflict) |
| Cancellation releasing a slot | `test_cancellation_releases_the_slot`, `test_admin_cancel_releases_the_slot` |
| Invalid and past requests | `test_past_and_closed_days_rejected`, `test_horizon_is_thirty_days`, `test_invalid_service_or_barber_rejected`, `test_validation_errors_are_shown_and_nothing_is_saved` |
| Separate barber availability | `test_jordan_starts_later_than_alex`, `test_barbers_are_independent`, `test_blocks_belong_to_one_barber_only` |
| Unauthenticated admin read/write protection | `test_unauthenticated_dashboard_redirects_and_leaks_nothing`, `test_unauthenticated_mutations_change_nothing`, `test_admin_pages_return_no_customer_data_to_anonymous_callers` |
| Private links cannot enumerate or access another booking | `test_private_link_cannot_be_enumerated_or_accessed_by_another_customer` (truncated, uppercased, padded and random 43-character tokens all 404) |
| Timezone / daylight saving | `test_daylight_saving_offset_is_applied` — 09:00 on 6 October 2026 (AEDT) stores as `2026-10-05T22:00:00Z` and renders back as `Tue 6 Oct 2026, 09:00` |
| CSRF on mutations | `test_csrf_is_required_for_booking_and_cancelling`, `test_admin_mutations_require_csrf`, `test_login_requires_csrf` |
| Password hashing | `test_password_is_hashed_in_the_database` (salted scrypt, never the plaintext) |

One failure was found and fixed during the pass: `admin_required` linked to a
non-existent `admin.dashboard` endpoint, which broke every authenticated admin page.
After the fix the whole suite passed.

---

## 2. Live HTTP walkthrough (running server, not the test client)

Against `http://127.0.0.1:5182` with a cookie jar:

```
csrf: QiMuqC8VPw3b...
POST /book -> 302
GET /booked -> 200
NB-N2HCQK
private link: /manage/2NuNyLXq2NyYrskDUldzNdCfcvODmQtTvWTYpVhn4XA
GET /manage/... -> 200
POST cancel -> 200   →  "Booking cancelled"
GET /admin/ -> 302   →  no customer data in the response body
```

---

## 3. Persistence across an ordinary restart

1. Booking `NB-N2HCQK` created and cancelled through the live server; its private
   link returned `200` before the restart.
2. Server stopped (`Ctrl-C`), started again with `PORT=5182 ./start.sh`.
3. `GET /manage/2NuNyL…` returned `200` and still showed `Curl Walker` with status
   `Cancelled`.

The SQLite file and the session secret both live in `instance/` and survive restarts;
startup only creates missing tables.

## 4. Two instances at once

```
PORT=5181 ./start.sh   → http://127.0.0.1:5181
PORT=5182 ./start.sh   → http://127.0.0.1:5182
5182: 200
5181: 200
```

Both respond simultaneously and share one SQLite file (WAL mode). `start.sh` reads
`PORT` from the environment and defaults to 5181.

---

## 5. Browser check

```
$ NORTHLINE_INSTANCE_DIR=/tmp/northline-verify PORT=5190 ./start.sh &
$ PORT=5190 .venv/bin/python reports/browser_check.py
90/90 checks passed          (real 72.16s)
26 screenshots written to reports/screenshots
```

Headless Chrome 152.0.7977.83 driven over the ChromeDriver HTTP API, against an
**isolated instance** (`NORTHLINE_INSTANCE_DIR=/tmp/northline-verify`) so the demo
database on port 5182 was never opened. Phone viewports are set with the DevTools
device-metrics override: a real macOS Chrome window cannot be narrower than about
500 px, so window sizing alone would silently test a 500 px layout.

`getComputedStyle` alone is not treated as proof for the touch targets — widths and
heights are read from `getBoundingClientRect`.

| Required check | Evidence |
| --- | --- |
| Sticky header, desktop and mobile | `position: sticky`; `getBoundingClientRect().top === 0` after scrolling to y=900 at 1440, 393 and 402 px |
| Header does not cover content | at 393 px the `#book` anchor settles at y=161 with the header bottom at y=67 |
| Header does not cover focused controls | focusing `#date-input` after `scrollIntoView` leaves it below the header bottom at every width |
| Header height stays in sync | `--header-h` equals the measured header height (67 px phone, matching `scroll-padding-top: 80.6px`), refreshed on resize and when the menu expands it |
| No horizontal overflow | `documentElement.scrollWidth <= window.innerWidth` on home, booking, manage, admin login and admin dashboard at 1440, 393 and 402 px; elements inside a deliberately scrollable strip are excluded by name |
| Menu opens/closes accessibly | `aria-expanded` false → true on tap; `aria-controls="site-nav"`; Escape closes it and returns focus to the button (`document.activeElement.id === "nav-toggle"`); a tap outside closes it; links are 46 px tall |
| Click anywhere on a date/time field | a real WebDriver click in the middle of `#date-input`, `#f-date`, `#b-start` and `#b-end` calls `showPicker()`, and clicking the field's `<label>` does too |
| Fallback without `showPicker()` | shadowing `showPicker` with `undefined` and clicking leaves the field focused, so native affordance and manual entry still work |
| Thumb targets | every visible control measured at 393/402 px is at least 44 px tall (nav button, slots, summary button, filter and day-stepper buttons, card actions, date and time inputs) |
| Admin rows on a phone | the appointment table resolves to one card per booking (`display: grid`, `thead` hidden, explicit ARIA roles retained), 330 px wide inside a 393 px viewport |
| Booking | completed through the real form on the phone viewport; `NB-XXXXXX` reference and private link rendered |
| Cancellation | the private view cancels the booking and the slot is offered again afterwards |
| Double-booking protection | a second submission of the same slot is refused with "that time was just taken", and the re-rendered availability no longer lists it |
| Single-row step indicators | the four step pills occupy one row at both phone widths |

### Screenshots

`reports/screenshots/` holds 26 images at 1440x1000, 393x852 and 402x874:

- `home-desktop`, `book-desktop`, `manage-entry-desktop`, `admin-login-desktop`, `admin-dashboard-desktop`
- `home-*`, `book-*`, `manage-entry-*`, `admin-login-*`, `admin-dashboard-*` for `phone-393x852` and `phone-402x874`
- `header-sticky-desktop`, `header-sticky-phone-393x852`, `header-sticky-phone-402x874` — the page scrolled, header still pinned
- `header-menu-open-phone-393x852`, `header-menu-open-phone-402x874`, `admin-dashboard-*-menu-open` — the expanded menu
- `booking-confirmed-phone-393x852`, `manage-phone-393x852`, `manage-cancelled-phone-393x852`
- `double-booking-conflict-phone-393x852`

### Defects found and fixed during this revision

1. **The phone viewport was not actually 393 px.** `setWindowRect` bottoms out around
   500 px on macOS, so the first run measured a 500 px layout and only appeared to
   pass the overflow check. Fixed by switching phone viewports to
   `Emulation.setDeviceMetricsOverride`, and a `viewport really is 393x852` check was
   added so this cannot regress silently.
2. **The step pills wrapped to two rows** at 393 px, leaving "4 Your details" alone.
   Font size, letter spacing and padding were tightened, and a one-row check added.
3. **`.btn-small` measured 42 px tall** on phones — under the 44 px touch guideline.
   Raised to 44 px and the check now measures it.
4. **The concurrency tests were wall-clock dependent.** They assert on fixed dates
   (2026-09-15) but the `app` fixture did not freeze time, so they only passed while
   the run happened before the 14:30 slot had passed. Re-running the suite at 17:08
   produced two failures that had nothing to do with the change. The `app` fixture now
   depends on `freeze_time`, so the whole suite runs on the pinned clock.

### Inspection limitations, honestly stated

### Inspection limitations, honestly stated

- Rendering was verified in Chrome only. Safari and Firefox were not run; they
  matter most for the picker fallback, which is implemented (focus + select) but only
  exercised here through a simulated missing `showPicker()`.
- The phone viewports are DevTools device-metrics emulation, not physical hardware:
  no real touch events, iOS wheel pickers, notch safe areas or on-screen keyboard.
- No screen reader was run. Accessibility is assessed by construction and by DOM
  assertions (labels, `aria-expanded`/`aria-controls`, `aria-current`, focus return on
  Escape, skip link, visible focus, ARIA roles preserved on the reflowed table). That
  is not an assistive-technology audit.
- The header's `ResizeObserver`/resize behaviour is verified by measurement at three
  widths, not by rotating a real device.
- The fallback check manipulates `HTMLInputElement.prototype` in-page, which proves
  the code path but is not the same as running an old browser.
- Exit criteria are computed from live DOM values, so a future CSS change that breaks
  the layout will fail the check — but a purely visual regression (for example a
  colour contrast change) would not.

---

## 6. Scope boundaries honoured

- No rescheduling anywhere in the app or the API.
- No database reset during this revision: `instance/northline.sqlite` is byte
  identical before and after (sha256 prefix `03750a2116261d71`), still 5 appointments
  and 3 blocks. All new verification ran against an isolated instance.
- No payments, no fake payment submission.
- No email delivery, and the confirmation page says so.
- No external integrations, no generated media, no paid services.
- Descript was not used at any point.
