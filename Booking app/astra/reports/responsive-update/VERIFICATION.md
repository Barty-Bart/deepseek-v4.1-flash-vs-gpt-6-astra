# Responsive booking revision — verification

Completed against the existing Northline Barber application on 15 September 2026. Preview: **http://127.0.0.1:5181**. The server remains bound to localhost.

## Delivered changes

- A shared sticky header on customer, confirmation/cancellation, login, error and admin pages. Measured header clearance protects anchor destinations, focused form controls and error summaries. The desktop sidebar uses the same offset.
- An accessible phone navigation disclosure with announced state, explicit pointer focus for Safari, Tab/Shift+Tab navigation, Escape/focus return, outside-click/focus dismissal and breakpoint handling. With JavaScript disabled, links stay visible and anchor clearance accounts for the expanded header.
- Whole-input date/time activation for the customer booking/availability date, diary filter date, blocked-period date, start time and end time. Chromium uses native `showPicker()` during user activation. Missing or rejected native calls use the in-page selector. WebKit uses the in-page selector directly to avoid native methods that can return without showing UI. An adjacent selector button is always available as an explicit alternative.
- Keyboard/manual entry remains supported. The accessible calendar has month/year controls, date bounds, closed days, keyboard day navigation, Escape and focus return. Admin time lists retain 15-minute intervals and staff opening hours. Customer appointment times remain genuine availability-only slot radios.
- Shared responsive service/barber rows, readable text, controls with comfortable touch targets, labelled mobile admin appointment cards, full-width actions and block forms. One codebase and one set of server routes; no duplicate phone app or rescheduling.

## Executed results

| Check | Result |
| --- | --- |
| Backend suite using isolated temporary SQLite databases | **65 passed** |
| Responsive browser suite | **24 grouped checks passed** |
| Engines | Chromium 140 / Playwright WebKit 26 |
| Desktop viewport | 1440×1000 |
| Phone viewports | **393×852 and 402×874**, both engines |
| Whole-field positions | Left/value area, centre, right padding on all five fields at all three viewport sizes |
| Picker activation | 45 native Chromium calls with active user gestures; 45 direct WebKit fallback openings |
| Native capability failure simulations | All five fields selectable when `showPicker` is missing or throws, in both engines |
| Layout/focus | Sticky positioning, anchor clearance, reverse focus, menu actions/resizing, touch targets, no horizontal page overflow |
| Customer flow | Service/barber selection, booking, price/duration, private-link cancellation, released slots, stale-form HTTP 409 conflict |
| Admin flow | Login/filtering, labelled cards, manual date editing, block overlap error, block creation/removal, logout |
| JavaScript disabled | Phone booking/cancellation and sticky-header anchor clearance passed |
| JavaScript/HTTP health | No uncaught page errors or HTTP 5xx responses |
| Preview/data | HTTP 200; original **6 bookings and 2 blocks**, admin records and signing secret preserved |

The backend concurrency tests send exact and partially overlapping booking requests from separate threads/connections and require exactly one success. They also cover a simultaneous block/booking race. Cancellation, persistence, hours/breaks/blocks, invalid inputs, CSRF, admin authentication and private-link isolation remain covered. No test resets or mutates the demo database.

## Measured runtime

- Backend test run: **6.48 seconds**, as recorded by pytest in `backend-tests.txt`.
- Final complete browser verification run: **34.62 seconds**, measured with Python's monotonic clock.

These are executed check durations, not a claim about total authoring time or time spent interrupted. API costs are logged externally and are not estimated here.

## Inspection and browser limits

Representative desktop booking/admin and phone booking, confirmation, menu, calendar and admin screenshots were visually inspected. The full viewport matrix was checked programmatically. Screenshots and raw reports are in this directory.

Playwright's mobile viewport/touch emulation is **not a physical iPhone 15 Pro or 16 Pro**. Actual iOS software-keyboard behaviour, device safe areas and OS-owned picker popup appearance were not visually verified. Native Chromium picker calls were instrumented, and the selectable in-page fallback UI was exercised directly. This is not a full screen-reader audit or a Firefox test.

## Corrections during verification

Safari's pointer activation did not focus the menu button, causing subsequent keyboard navigation to begin in the previous form control. The shared disclosure now explicitly focuses its trigger and supports consistent keyboard movement. Calendar month navigation also keeps focus on an enabled control at range boundaries.

Harness corrections wait for media-query state and focus-restoration frames, click visible choice labels instead of forcing hidden one-pixel radios, and avoid animation-frame waits with JavaScript disabled. Earlier diagnostic reports are preserved; `browser-verification.json` and `browser-verification.txt` contain the final passing run.

## Reproduce

```sh
.venv/bin/python -m pytest -q --junitxml=reports/responsive-update/backend-tests.xml
.venv/bin/python -m playwright install chromium webkit
.venv/bin/python scripts/verify_responsive.py
```

The browser script owns a temporary localhost server and temporary SQLite database for mutations. It inspects the assigned preview read-only and compares demo records and the secret before/after. The update baseline is `.local/responsive-update-before.json`; to repeat the same preservation check after intentionally changing demo records, refresh that local baseline using `scripts.verify_operation.snapshot()`.
