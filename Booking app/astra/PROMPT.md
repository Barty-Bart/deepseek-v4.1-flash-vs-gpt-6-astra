# Booking app benchmark — initial build

Build a complete, polished localhost appointment-booking website for a fictional barber shop called Northline Barber. Work autonomously without creative questions. This is a browser app, not a native Mac app. Deliver and verify the working implementation, not just a mockup or plan.

## Stack and operation
Use Python Flask, SQLite, server-rendered Jinja HTML, CSS and small amounts of vanilla JavaScript. Use a project-local virtual environment and pinned dependencies. No frontend framework, external database, paid services, generated media, email delivery or public deployment. Bind the server to 127.0.0.1. Read PORT from the environment (default 5181); start.sh must support PORT=5182 for a second simultaneous build. Preserve data on ordinary restarts. Provide explicit separate seed/reset commands; never reset on startup.

## Business and demo data
Timezone: Australia/Melbourne. Display dates and times clearly in that timezone and store timestamps consistently. Two barbers: Alex and Jordan. Services: Classic Cut (30 minutes, AUD45), Beard Trim (15 minutes, AUD25), Cut and Beard (45 minutes, AUD65). Shop opens Tuesday–Saturday, 09:00–17:00. Alex works those hours; Jordan starts at 10:00. Each takes a 12:30–13:00 break. Offer starts on a 15-minute grid, bookable from now through the next 30 days. Seed a small set of appointments and staff-specific blocked periods relative to the seed date, with fictional contact details.

## Customer journey
Choose service, barber, date and a genuinely available start time. Show duration and price before confirmation. Collect name and email with server-side validation. No customer registration. Confirm with a booking reference and an unguessable private management link. Let the customer view and cancel their own future appointment using that link. Explain that confirmation emails are not sent in this local demo. Do not show other customers' information. No payments or fake payment submission.

## Admin
One seeded admin account with credentials documented in README for local testing. Implement real server-side session authentication, password hashing, logout, and CSRF protection for mutations. Persist the application secret locally outside committed source. Protect both admin pages and every admin mutation endpoint. An unauthenticated request must not expose booking/customer information or change data.

Dashboard: daily bookings, filter by date and barber, view customer/service/time/status, cancel bookings, create and remove staff-specific unavailable periods. Reject a block that overlaps an existing confirmed appointment and explain which appointment must be handled first. Include sensible empty states and validation errors. No staff-management suite, CRM, analytics, password resets or external calendar integration.

## Scheduling correctness
Validate everything on the backend, regardless of client controls. Service duration must fit entirely inside working hours and outside breaks, blocks and confirmed appointments. Adjacent appointments are allowed. Different barbers can have overlapping bookings. Past slots and invalid service/staff choices must be rejected. Cancellation preserves the record and releases its slot. Prevent concurrent overlapping bookings transactionally in SQLite: two simultaneous attempts for an overlapping slot must not both succeed. Return a friendly conflict response and refresh availability. Treat time intervals as start-inclusive/end-exclusive. Use timezone-aware scheduling, including daylight-saving handling.

## Design
Create a coherent, attractive, restrained barber-shop identity with readable typography, intentional spacing and clear controls. Responsive desktop and mobile layouts; accessible labels, keyboard operation, visible focus, helpful error summaries and good contrast. Make date/time selection practical on a phone. Keep technical implementation details out of the customer flow except the clear local-demo limitations.

## Required verification
Write and run meaningful backend tests covering booking persistence across application restart, differing service durations, hours/breaks/blocks, concurrent conflicting requests (exactly one succeeds), cancellation releasing a slot, invalid and past requests, separate barber availability, and unauthenticated admin read/write protection. Check private links cannot enumerate or access another booking. Use an isolated temporary test database, never destroy the demo database.
Verify the rendered interface at desktop and mobile sizes where tools permit; document any inspection limitations honestly. Do not claim test success without execution. Do one focused verification pass, fix actual failures, and finish; avoid endless cosmetic or benchmark loops.

## Deliverables
Working source, requirements, start.sh, explicit seed command, tests, SQLite schema/migrations, README with setup/run/test instructions, local admin credentials, customer walkthrough and known limitations. Start the local preview on the configured port and report its URL. Preserve scripts and reports. Do not fabricate timing or API costs; those are logged externally.

## Scope boundary
Do not implement rescheduling in V1. A later benchmark revision will request it. No additional integrations or paid generation. Do not inspect the competing model's project or outputs. Work only in this project's folder for authored files, aside from ordinary dependency caches.
