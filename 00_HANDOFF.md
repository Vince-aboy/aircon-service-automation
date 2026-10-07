# Handoff

## Current project state — 2026-10-08

- Customer self-bookings and staff team-intake jobs now share the same PostgreSQL `OperationalJob` and n8n `NotificationOutbox` reporting path.
- Commit `2f21837` adds the team-intake bridge. Clicking `Approve & Publish` creates one pending n8n outbox event per active intake row, while preserving the original team message wording in the service field.
- Migration `20261008_0013_shared_outbox_sources.py` allows an outbox event to belong to either a customer booking or a team-intake operational job.
- Team-intake events use the existing n8n payload shape and Google Sheets reporting branches. Provisional labels such as `Client_B13_U1234` are intentionally preserved until a real customer name is available.
- The VPS worker timer was verified active and running every minute. `AIRCON_AUTOMATIC_DELIVERY_ENABLED=true` was confirmed. The latest worker logs show no pending event was available; existing Oct. 7–8 jobs were published before this bridge and are not backfilled automatically.
- Next end-to-end verification: create a new intake → approve and publish → confirm `pending` → wait for the worker → confirm `recorded` → verify n8n and Google Sheets.
- Mobile/staff UX completed: sidebar hidden by default on small screens, draft schedule table remains horizontally scrollable, empty values display as `—`, and intake editing stacks on phone screens.
- Appointment and customer directories now include shared team-intake jobs, including provisional customers.
- Latest local verification after the bridge: `50 passed, 5 skipped`.

## Version 1 closeout — 2026-10-05

- Balik-Lamig Version 1 is functionally complete and ready to hand off before moving to the Web Profile project.
- The live website includes customer requests, waitlist handling, staff review, team scheduling, rescheduling, appointment lifecycle statuses, completed-job highlighting, customer history, team management, automation monitoring, activity history, and settings.
- The public and Owner Operations visual system now uses warm off-white surfaces, white cards, charcoal text, Balik-Lamig gold actions, and restrained green completion states.
- The protected n8n workflow now has four reporting branches: Daily Schedule, Client Summary, Service History, and Customer Directory. All four feed a four-input Merge and the final fixed `automation_status: processed` response.
- Customer Directory uses `customer_id` as its stable key. Jannet Aboy is `customer_id = 2` with four PostgreSQL booking requests; the Google Sheet count was verified as `4`.
- The application payload now includes `customer_booking_count`, calculated from PostgreSQL booking requests for the customer. n8n maps it to the Customer Directory `booking_count` column.
- Owner Operations now displays reporting status, last recorded sync, pending events, retrying events, and failed events on the Dashboard and Automation Monitor.
- Latest verification: `46 passed, 5 skipped`.
- Latest application commits: `6493618`, `3f282f2`, and `6f42fc3`.
- Final handoff action: publish the n8n workflow and run one controlled event confirming the existing Customer Directory row updates without duplication and the app outbox becomes `recorded`.
- Next project after this controlled verification: Web Profile.

## Current live snapshot — 2026-10-03

- The owner operations command center is deployed at `https://vinceaboy.com/balik-lamig/staff`.
- Current handoff date: 2026-10-04.
- The dashboard display name is `Boss EMER`, separate from the staff login username.
- The workspace includes dashboard, service requests, team schedule, appointments, customers, teams/technicians, automation, activity history, and settings.
- Safeguards include date-aware assignment, occupied-block protection, past-date protection, team/date/time rescheduling, required cancellation reasons, internal notes, audit history, safe deactivation, membership removal, and failed outbox-event requeue.
- The live SQL roster contains all 16 owner-provided employees. Fictional technicians were retired after existing appointments were transferred to the real Team A/Team B leads.
- Current leads are Pedro Ecleo for Team A and Brian Elipides for Team B. The other roster members remain active and can be assigned later.
- PostgreSQL remains authoritative; Google Sheets is an owner-reporting view. Customer messaging and payments remain disabled.
- Staff authentication is temporarily disabled for a supervised demonstration via `AIRCON_STAFF_AUTH_ENABLED=false`; restore `true` immediately afterward.
- Latest local verification: `44 passed, 5 skipped`.

## Current state
- Status: Phase 6 synthetic n8n webhook bridge complete and manually verified; all external messaging remains disabled
- Latest evidence: synthetic event `AC-20260930-564E26DF` moved from local SQL outbox `pending` to `recorded` after authenticated delivery to the n8n test webhook. The `synthetic_only = false` rejection path was also verified.
- Current next step: add an explicit n8n response payload so the local app can distinguish `processed` from `rejected`; keep n8n unpublished and synthetic-only.
- Phase 7 implementation: the local bridge now parses n8n's JSON `automation_status`; `processed` records locally, `rejected` becomes local `failed`, and malformed results remain pending. Verification passed: `31 passed, 5 skipped`.
- Lifecycle evidence: synthetic job `AC-20260930-564E26DF` progressed through `confirmed` → `en_route` → `in_progress` → `completed`; its three pending lifecycle events were sent to n8n in order, and the completed event produced a dispatcher notice. No real message was sent.
- Current next step: complete Phase 9 retry/idempotency hardening. Phase 8 must replace the manual n8n send button with automatic delivery only after testing, security review, and explicit publishing approval.
- UX update: added a `Complete job now` shortcut for confirmed jobs. It advances through en_route, in_progress, and completed in one action while preserving all audit history and synthetic outbox events. Verification passed: `32 passed, 5 skipped`.
- Phase 8 implementation: when n8n returns a `dispatcher_message`, the local outbox now stores and displays it as a prepared dispatcher notice. No external delivery was added. Verification remains `32 passed, 5 skipped`.
- Phase 8 manual evidence: Jerome Galicia synthetic job `AC-20260930-132E4A43` was completed with the shortcut, its en_route/in_progress/completed events were sent to n8n one at a time, and the local outbox displayed the saved completed dispatcher notice.
- Phase 9 initial evidence: synthetic scheduled event `AC-20261001-F3D5DB1E` was sent once and recorded; a second send attempt was rejected locally with `no pending automation event is available`, preventing duplicate delivery.
- Phase 9 failure/retry evidence: Thalia synthetic scheduled event `AC-20261001-387113CE` remained pending after an HTTP 404 while n8n was not listening, then was retried successfully after the n8n test listener started. The local UI now shows a friendly retry message instead of raw JSON when delivery fails. Verification: `32 passed, 5 skipped`.
- Phase 9 complete evidence: Venice synthetic scheduled event `AC-20261001-235C0367` displayed `Delivery failed. The event remains pending and can be retried.`, stayed pending, then changed to recorded after n8n was started and the event was retried. n8n showed `Workflow executed successfully`; no customer message was delivered.
- Phase 10 started: automatic delivery design is documented in `07_PHASE_10_AUTOMATIC_DELIVERY_DESIGN.md`; automatic sending remains disabled pending outbox claim state, retry/idempotency safeguards, VPS/security review, and explicit publishing approval.
- Phase 10 implementation: outbox delivery-state columns and migration `20261001_0007_add_outbox_delivery_state.py` are applied to the local development database. Tests pass (`32 passed, 5 skipped`); automatic delivery remains disabled.
- Phase 10 claim foundation: local-only five-minute event claim leases and stable idempotency keys are implemented and tested (`33 passed, 5 skipped`). No automatic n8n delivery exists yet.
- Phase 10 delivery results: the manual test send now uses claim/result handling and the outbox shows attempt/error state. Temporary failure remains pending; success records; explicit rejection fails. Verification: `34 passed, 5 skipped`. Automatic delivery remains disabled.
- Phase 10 live evidence: `AC-20261001-22C2A472` failed with HTTP 404 on attempt 1, saved the error while pending, then was retried successfully on attempt 2 when n8n was listening. The event is recorded and its error cleared; no customer message was delivered.
- Phase 10 automatic-delivery safeguard: `AIRCON_AUTOMATIC_DELIVERY_ENABLED` defaults to disabled; the outbox displays this state. Retry timing is now calculated with a bounded delay, but no background worker exists and no automatic send was added. Verification: `35 passed, 5 skipped`.
- Phase 10 worker check: the outbox now has a no-send `Check due delivery worker` action. With automatic delivery disabled, it only counts due events and makes no change or webhook call. Verification: `36 passed, 5 skipped`.
- Phase 10 worker-check evidence: local UI reported `0 due event(s) found` and explicitly confirmed that automatic delivery was disabled, so no send occurred.
- Phase 10 VPS automation verified: the app was deployed at `https://vinceaboy.com/balik-lamig/`, n8n was published with a protected production webhook, and a systemd worker timer delivered a new synthetic event automatically. The event changed from `pending` to `recorded` with one delivery attempt; no customer message was sent.
- Documentation: visual completed-phase roadmap is available locally at `/staff/documentation/phases`; source diagram is `08_PHASES_0_TO_9_ROADMAP.md`. Verification: `37 passed, 5 skipped`.
- Project: 0009_AIRCON_SERVICE_AUTOMATION
- Goal: Build a realistic, portfolio-grade aircon cleaning and service automation prototype for a Philippine small business. Start with a simple MVP, synthetic data, and a controlled booking workflow; incrementally add validation, human review, notifications, appointment status, reminders, error handling, and documentation.

## Current Phase 11 snapshot

- The protected, published n8n workflow now reports owner-facing synthetic events to Google Sheets after the local worker delivers them.
- Verified reporting tabs are `Daily Schedule` (current assignment), `Client Summary` (one current row per booking reference), and `Service History` (append-only event history).
- The live success path is `Webhook -> safety If nodes -> Mark Processed -> parallel Google Sheets nodes -> Merge (3 inputs, Append) -> Return Processed Response`.
- `Return Processed Response` must return exactly `automation_status: processed`. Google Sheets node output must not be returned directly, because it does not contain the application acknowledgement and would leave local events pending for retry.
- Controlled evidence: Jannet Aboy booking `AC-20261003-CC71C4CB` was scheduled, rescheduled, and rescheduled back. The sheet views updated correctly and Service History recorded `outbox-8` with the event note.
- `Customer Directory` was created and backfilled with 11 synthetic PostgreSQL customer rows. It is keyed by stable `customer_id`; duplicate names remain separate customers and `booking_reference` is not used as identity.
- The exact live tab list was reviewed and Vince explicitly approved removal of `Cancelled Requests` and `Automation Log`; both tabs were deleted. The app outbox and n8n executions remain the technical trace.

## Next step

- `Customer Directory` was backfilled and verified with 11 rows from PostgreSQL, and the application payload includes `customer_id`. Next: add and test the fourth n8n Google Sheets upsert branch, expand the Merge to four inputs, and preserve the fixed processed response. Keep PostgreSQL authoritative, use `customer_id` rather than `booking_reference`, and keep customer messaging and payments disabled.

## Notes
- Phase 6 implementation started: local scheduling and job-progress changes now create simulated pending outbox events. `GET /staff/automation` displays them, and its local simulation control marks them `recorded` without delivering any message. Verification passed: `30 passed, 5 skipped`.
- n8n Phase 6 evidence: the VPS n8n draft workflow `AIRCON - Phase 6 - Synthetic Event Processor` was manually executed successfully. It accepts a synthetic test event, routes `synthetic_only = true` to `Mark Processed`, and routes `false` to `Reject Event`. It is not published and has no external connections.
- n8n webhook evidence: the separate draft `AIRCON - Phase 6 - Webhook Synthetic Inbound` received a synthetic POST through its test URL, passed the safety check, and returned `automation_status: processed`. Its timestamp was corrected to the project timezone using `Asia/Manila` (`+08:00`). It is still unpublished and test-only.
- n8n authentication evidence: the webhook was changed from unauthenticated test mode to Header Auth, the initially exposed test key was rotated, and a new synthetic POST passed authentication and was processed successfully. The secret is not recorded.
- Application bridge implementation: added an opt-in `/staff/automation/push` action that sends exactly one pending synthetic SQL outbox event to the HTTPS n8n webhook using temporary `AIRCON_N8N_WEBHOOK_URL` and `AIRCON_N8N_WEBHOOK_KEY` variables. Without both variables, no network call occurs. Verification passed: `31 passed, 5 skipped`; manual end-to-end app-to-n8n push remains pending.
- VPS n8n clarification: Vince states that n8n is already installed on the personal VPS. Its present security and configuration state remain unverified for this project; do not connect the app, publish a webhook, or add external credentials until a fresh read-only audit and explicit confirmation.
- Phase 5 evidence: the user applied migration `20260930_0006` and manually moved a scheduled job from confirmed to en route, in progress, and completed. Each board update confirmed that no customer message was created.
- Next phase: Phase 6 will simulate n8n automation with local synthetic events only. Do not connect Facebook/Meta, customer messaging, calendars, or production services.

- 2026-10-04: Verified the published n8n four-branch workflow with synthetic bookings `AC-20261004-2935E916` and `AC-20261004-60BF5C0A`. `Daily Schedule`, `Client Summary`, `Service History`, and `Customer Directory` received the events; `customer_id` is now populated for new directory rows. Normalized phone columns to text with Philippine leading zeros and converted Customer Directory booking/date-time fields to native readable date formats.
- Phase 5 next action: apply migration `20260930_0006`, then open a scheduled card on `/staff/dispatch`. Confirm the modal can move a job through confirmed, en route, work in progress, and completed; each update must appear in local workflow history.
- Phase 5 scope: scheduled jobs may move only from `confirmed` to `en_route`, then `in_progress`, then `completed`; cancellation is allowed until completion. Every valid transition is written to `appointment_status_history`. No messages are created.
- This file is the main live snapshot for the project
- Keep it short, current, and easy to scan
- Scope constraints: defer Facebook/Meta integration, payments, AI, real customer data, and production deployment until explicitly authorized.
- Phase 0 plan: `docs/PHASE_0_BUSINESS_DISCOVERY_AND_MVP_PLAN.md`.
- Confirmed synthetic operating defaults: Urban Deca Homes, Tondo, Manila; Monday–Saturday, 09:00–17:00; two appointment windows per technician daily.
- Local foundation findings: Python 3.11, Git, PostgreSQL 17 server/client available; Node.js/n8n deferred until Phase 6.
- Release direction: local-first → private GitHub → security-reviewed private VPS staging → separately approved public release. See `docs/VPS_AND_GITHUB_RELEASE_PLAN.md`.
- Test evidence: isolated `.venv` created; `tests/test_project_info.py` passed on 2026-09-30.
- Local database evidence: `aircon_service_dev` uses the restricted `aircon_app` role; its password is not recorded in project files.
- Phase 2 evidence: migration `20260930_0001` applied successfully; eight-table schema exists locally and four pre-migration automated tests passed.
- Seed scope: three fictional service types and two fictional technicians only; no customer or booking records.
- Seed execution evidence: 3 service types and 2 fictional technicians added on 2026-09-30.
- Verification evidence: all three seeded services and two fictional technicians were queried successfully as `aircon_app`.
- Constraint evidence: PostgreSQL integration tests passed (`3 passed`); rejected writes were rolled back.
- Validation evidence: 13 non-database tests pass; booking input is validated before any database write.
- Controlled-write evidence: booking service creates only `pending_review` requests, checks service availability before record creation, and passed five live PostgreSQL integration tests.
- API evidence: local FastAPI health and booking endpoints passed isolated request/response tests.
- Page evidence: `/book` form and receipt templates passed isolated request/response tests; direct browser inspection is pending because no workspace browser is currently available.
- Coverage migration evidence: Alembic reports `20260930_0002 (head)`.
- Post-migration integration evidence: 5 PostgreSQL tests passed after coverage-area migration.
- Browser evidence: `http://127.0.0.1:8000/book` rendered locally with Balik-Lamig branding and Urban Deca Homes, Tondo, Manila coverage.
- UX decision: use honest `Request Service` wording and a staff-review flow, not an instant `Book Now` promise. See `docs/BOOKING_UX_RESEARCH.md`.
- UX presentation: keep the customer-facing form minimalist; the visible page uses one concise instruction while detailed prototype limitations remain in project documentation.
- Form-design checkpoint: the experimental underline-field reference styling was rolled back at user request. Keep the compact working form until the required customer fields are agreed.
- Visible location field: `Full Address / Decca Address` only. Barangay, City, and coverage area are controlled internal defaults for the single-area prototype.
- Visible service fields: Aircon type (default `Window Type`), Choose service (default `Aircon Cleaning`), and Preferred date only. The backend supplies the temporary single-unit and morning-window defaults; no visible notes field.
- Staff queue: `GET /staff/requests` is a loopback-only, read-only queue for `pending_review` requests. It deliberately has no confirm, decline, schedule, notification, or public-access behavior.
- Staff queue evidence: browser inspection showed one request, `AC-20260930-51AB3A76`, in `pending_review` with the intended service details.
- Staff-review controls: approve transitions `pending_review` to `approved_for_scheduling`; decline transitions it to `cancelled`. Each writes a local-staff audit row. Neither action creates an appointment, sends a notification, or exposes the system publicly.
- Staff-review evidence: the synthetic request was manually approved. Browser feedback confirmed no appointment/message was created, and the pending queue became empty.
- Scheduling decision: use two fictional teams and three planned two-hour blocks per team/day; reserve 16:00-17:00 outside normal advance booking. See `docs/SCHEDULING_RESEARCH_AND_DEFAULTS.md`.
- Dispatcher-board controls: only `approved_for_scheduling` requests can be assigned; assignment creates one appointment, changes the request to `scheduled`, writes audit history, and rejects reuse of the same team/time block. No message is sent.
- Dispatcher-board evidence: the approved synthetic request `AC-20260930-51AB3A76` was assigned to Team A, 09:00-11:00 on 2026-10-10. The board showed the assignment and the remaining five blocks as open.
- Job-detail modal: scheduled dispatcher cards open a local in-page modal containing the request’s contact, address, service, team/time, and staff-review/scheduling audit history. A full read-only URL remains only as a non-JavaScript fallback.
- Receipt evidence: local form submission rendered a receipt with reference `AC-20260930-51AB3A76` and status `pending_review`; it correctly states that staff review is required and that no message or appointment was created.
- Migration evidence: user applied `20260930_0003` successfully; Alembic reports `20260930_0003 (head)`.
- Receipt evidence: local form submission rendered a receipt with reference `AC-20260930-51AB3A76` and status `pending_review`; it correctly states that staff review is required and that no message or appointment was created.
- Brand asset: user-supplied `Balik-Lamig.png` is copied into the local app and identifies the prototype as Balik-Lamig Air-Conditioning and Refrigeration Services.
