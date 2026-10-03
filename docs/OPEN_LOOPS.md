# Open Loops

## Before Phase 1

- Resolved 2026-09-30: Use Urban Deca Homes, Tondo, Manila, Monday–Saturday, 09:00–17:00, and two appointment windows per technician as the initial synthetic defaults.
- Resolved 2026-09-30: Python 3.11, Git, PostgreSQL 17 client/server, and Docker are installed. The PostgreSQL service is running. Node.js and n8n are not installed; Docker Desktop is not running.
- [UNCONFIRMED] Identify the local PostgreSQL database role and credential method before connecting. No password will be requested, exposed, or stored in this project.
- Resolved 2026-09-30: Vince states n8n is already installed on the personal VPS. Do not assume its current security/configuration state or connect this project until a fresh read-only audit and explicit approval.
- [UNCONFIRMED] Decide whether the local admin area will use a demo-only password in Phase 4 or remain accessible only on localhost without authentication during earlier learning stages.

## Release planning

- [UNCONFIRMED] Confirm the current VPS security, n8n, and service state with a read-only audit immediately before any project connection or deployment; existing findings are historical.
- Resolved 2026-10-01: Created and pushed the public portfolio repository `Vince-aboy/aircon-service-automation` at commit `9d02f79`.
- Resolved 2026-10-01: Deployed and verified synthetic-only staging at `https://vinceaboy.com/balik-lamig/`; the n8n production webhook and one-minute VPS worker automatically processed a fictional outbox event.
- Open 2026-10-03: Complete the Phase 11 event contract, Google Sheets column schema, and edge-case review before creating the owner-reporting n8n workflow.

## Security follow-up

- Resolved 2026-09-30: The local `aircon_app` password that appeared in a failed-migration traceback was rotated. The migration was then applied with a password-free URL plus temporary `PGPASSWORD`. Do not record or reproduce any password in project files, screenshots, Git, or messages.
