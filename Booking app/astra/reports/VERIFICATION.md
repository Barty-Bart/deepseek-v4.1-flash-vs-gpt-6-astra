# Verification record

Verified on 15 September 2026. The working preview is **http://127.0.0.1:5181**, using the provided `PORT=5181` environment variable.

## Executed results

| Check | Result | Evidence |
| --- | --- | --- |
| Backend integration/security/scheduling suite | **65 passed** | `backend-tests.txt`, `backend-tests.xml` |
| Chromium customer and staff journeys | **10 checks passed** | `browser-verification.json`, `browser-verification.txt` |
| Desktop layout | **Inspected at 1440×1000** | `desktop-booking.png`, `desktop-confirmation.png`, `desktop-login.png`, `desktop-admin.png` |
| Mobile layout | **Inspected at 390×844** | `mobile-booking.png`, `mobile-confirmation.png`, `mobile-admin.png` |
| Real preview restart | **Records and signing secret preserved** | `operation-verification.json` |
| Concurrent preview processes | **HTTP 200 on 5181 and 5183** | `operation-verification.json`, `alternate-port.log` |
| Secret file permissions | **0600** | `operation-verification.json` |
| Installed dependency consistency | **`pip check` passed** | Pinned requirements match the installed environment |

The backend suite uses fresh temporary SQLite databases, including independent connections for threaded race tests. Exact and partially overlapping concurrent booking attempts return exactly one success and one conflict. A booking racing an admin block also has exactly one winner. Restart persistence, duration boundaries, breaks, staff-specific blocks, adjacency, cancellation, invalid/past requests, independent barbers, daylight-saving conversion, CSRF, private links and authenticated admin access are covered. Saved admin cookies cannot restore access after logout, and server-side expiry is enforced.

The browser pass captured the live preview without adding or cancelling its appointments. All functional mutations ran against a separate temporary app/database. It verified customer selection/confirmation, mobile private-link cancellation and released availability, date controls and closed days, admin sign-in/filtering/block conflict/create/remove/logout, keyboard focus, lack of page overflow, and a complete booking with JavaScript disabled. It recorded **no uncaught JavaScript errors and no HTTP 5xx responses**. The seven final screenshots listed above were inspected visually.

The live demo still has its original **six seeded appointments and two staff blocks**. A real preview restart and starting a second process preserved all booking, block and admin records and the local signing secret.

## Findings handled during verification

- The initial past-cancellation test attempted to extract a token from a cancellation form after it was correctly hidden. The test now saves the token before moving the clock forward and verifies rejection of a direct cancellation request.
- A screen-reader-only label in the horizontally scrollable admin table extended the mobile page width. Positioning the scroll container fixed the overflow. The region is also keyboard-focusable.
- The browser harness initially used string evaluation blocked by the application's Content Security Policy. It now uses locator assertions without weakening the policy. The JavaScript-disabled navigation check uses an explicit navigation wait.
- Server-side admin session records were added and tested so logout revokes saved cookies and expiry is checked against server state.

Earlier diagnostic output and the overflow inspection image are preserved alongside the final passing reports. Files containing `initial`, `failure`, `details` or `inspection` document intermediate findings, not the final status.

## Inspection limits

Port **5182 was already in use** when the second process was attempted. The existing process was not stopped or inspected. The runner correctly read `PORT=5182` and reported the bind conflict; simultaneous operation was then verified with `PORT=5183`. See `port-5182-unavailable.log` and `operation-5182-attempt.txt`. `PORT=5182 ./start.sh` is supported whenever that port is free.

Browser checks used desktop Chromium and Chromium's mobile viewport/touch emulation. They do not substitute for physical iOS/Android devices, Safari/Firefox testing or a comprehensive screen-reader audit. No email delivery, payments, external services or public deployment were tested or added.

## Reproduce

From the project root, with the preview running on `PORT`:

```sh
.venv/bin/python -m pytest -q --junitxml=reports/backend-tests.xml
.venv/bin/python scripts/verify_ui.py
VERIFY_ALT_PORT=5183 .venv/bin/python scripts/verify_operation.py
```

The operation script starts and stops only the alternate preview it owns. Its record-preservation checks are read-only. The optional local restart snapshot belongs to this verification run; remove `.local/restart-snapshot.json` before rerunning operation verification after intentionally changing demo records.
