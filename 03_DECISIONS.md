# Decisions

## Purpose
- Record durable rules, decisions, and constraints for the project.

## Use
- Add only decisions that should remain true across sessions.
- Avoid temporary notes or noisy task details here.

## Entries
- `2026-09-30` - Field-work progress uses the controlled local sequence confirmed -> en route -> in progress -> completed. Cancelled may be selected before completion. Completed and cancelled appointments are final. Each transition must create an `appointment_status_history` audit row and must not send a customer message.
- `2026-09-30` - The first n8n workflow is a draft synthetic-event processor only. It must validate `synthetic_only` before marking an event processed; non-synthetic events are rejected. Keep it unpublished and disconnected until the application-to-n8n transport, VPS security, authentication, and real-notification approvals are separately reviewed.
- `2026-09-30` - Start scheduling with two fictional deployable teams, Team A and Team B. Use three planned two-hour blocks per team (09:00-11:00, 11:30-13:30, 14:00-16:00), with 16:00-17:00 held out of normal advance booking. Customers request a date; staff later assigns an approved request to a team and exact block. See `docs/SCHEDULING_RESEARCH_AND_DEFAULTS.md`.
- `2026-09-30` - Staff approval is intentionally named `approved_for_scheduling`, not `confirmed`, because no technician/time appointment exists yet. Local staff decline uses `cancelled`. Both transitions require a persisted audit row; neither action sends a message or creates an appointment.
- `2026-09-30` - The primary customer CTA is `Request Service` / `Send service request`. Do not use `Book Now` or imply instant confirmation until the system has verified live availability and explicitly authorized notification delivery.
- `2026-09-30` - Use RGL Air Conditioning's contact-page booking flow only as a high-level UX reference: prefer a concise, single-page request form while retaining this project's stricter validation, human review, synthetic-data-only scope, and distinct Balik-Lamig branding.
- `2026-09-30` - Use the user-supplied Balik-Lamig branding asset for the local prototype UI. This does not change the synthetic-data-only, non-production scope or imply authorization to publish the business brand publicly.
- `2026-09-30` - Controlled booking validation accepts only Urban Deca Homes, Tondo, Manila requests; Philippine mobile numbers are normalized to `09XXXXXXXXX`, dates must be future, windows are `09:00-12:00` or `13:00-16:00`, and unit count is 1–10. Unknown fields are rejected before database access.
- `2026-09-30` - Supply local migration credentials only through temporary terminal variables: keep the database URL password-free and use `PGPASSWORD` for the current command session, then clear both variables. Never place a database password in source, `.env.example`, or a shared screenshot.
- `2026-09-30` - Use local PostgreSQL database `aircon_service_dev` with restricted application role `aircon_app`. The application must not use the `postgres` superuser, and the password must not be stored in this workspace.
- `2026-09-30` - Use a repository-specific, read-only GitHub SSH deploy key for VPS source access. Do not store personal GitHub credentials or tokens on the VPS.
- `2026-09-30` - Use a private GitHub repository named `aircon-service-automation` as the initial source-control destination. Any public repository must be a separately reviewed, sanitized release and requires explicit approval.
- `2026-09-30` - Treat VPS deployment as a Phase 7 gated activity: deploy only a reviewed Git commit to private staging after a current security audit, then request separate approval before public exposure.
- `2026-09-30` - Use dedicated least-privilege VPS and PostgreSQL identities for this application; never store secrets in Git, project Markdown, or portfolio evidence.
- `2026-09-30` - Use the installed Python 3.11 runtime for the local prototype; do not install Node.js/n8n until the core booking workflow has passed its tests.
- `2026-09-30` - Use Urban Deca Homes, Tondo, Manila as the initial synthetic service area, with Monday–Saturday 09:00–17:00 operations and two appointment windows per technician each day.
- `2026-09-30` - Use a local, single-business MVP: FastAPI, Jinja2, PostgreSQL, SQLAlchemy/Alembic, Pytest, and n8n only after the core booking flow is proven.
- `2026-09-30` - A booking starts as `pending_review`; staff must approve, assign a technician, and select an appointment slot before it becomes confirmed.
- `2026-09-30` - Notifications and reminders are simulated through a local outbox/log until explicit authorization for real delivery is received.
- `2026-09-30` - Begin with synthetic data and a controlled booking workflow; defer Facebook/Meta integration, payments, AI, real customer data, and production deployment until explicitly authorized.
- `2026-09-30` - Build incrementally and test each major feature before moving to the next stage.
- `2026-10-01` - Vince approved the intended public portfolio route `https://vinceaboy.com/balik-lamig/` beside the existing `/profiles/` site. This approves the target URL only; VPS deployment, reverse-proxy changes, and always-on automation still require separate implementation and verification.
- `2026-10-01` - Verified synthetic-only VPS staging at `https://vinceaboy.com/balik-lamig/`. The n8n production webhook is protected by Header Auth, and a one-minute systemd worker automatically delivers pending outbox events. Automatic delivery remains limited to synthetic events; no customer message channel is connected.
- `2026-10-03` - Phase 11 owner reporting will use PostgreSQL as the source of truth and Google Sheets as an owner-facing reporting view synchronized through n8n. Document the event contract, sheet schema, and edge cases before adding Google Sheets nodes. Keep all data synthetic until separately approved.
