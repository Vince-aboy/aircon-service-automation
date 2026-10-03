# Open Loops

## Before Phase 1

- Resolved 2026-09-30: Use Urban Deca Homes, Tondo, Manila, Monday–Saturday, 09:00–17:00, and two appointment windows per technician as the initial synthetic defaults.
- Resolved 2026-09-30: Python 3.11, Git, PostgreSQL 17 client/server, and Docker are installed. The PostgreSQL service is running. Node.js and n8n are not installed; Docker Desktop is not running.
- [UNCONFIRMED] Identify the local PostgreSQL database role and credential method before connecting. No password will be requested, exposed, or stored in this project.
- Resolved 2026-09-30: Vince states n8n is already installed on the personal VPS. Do not assume its current security/configuration state or connect this project until a fresh read-only audit and explicit approval.
- [UNCONFIRMED] Decide whether the local admin area will use a demo-only password in Phase 4 or remain accessible only on localhost without authentication during earlier learning stages.

## Release planning

- Resolved 2026-10-03: Added and synchronized the 16-person owner employee roster in PostgreSQL; retired fictional technicians without deleting appointment history.
- Resolved 2026-10-03: Completed the owner operations workspace and dispatcher controls; local verification is `44 passed, 5 skipped`.
- Open 2026-10-03: Assign the remaining active technicians to Team A or Team B as the owner decides. Only Pedro Ecleo and Brian Elipides are currently designated team leads.
- Open 2026-10-03: Re-enable staff authentication after the supervised demonstration by restoring `AIRCON_STAFF_AUTH_ENABLED=true` and restarting the service.

- [UNCONFIRMED] Confirm the current VPS security, n8n, and service state with a read-only audit immediately before any project connection or deployment; existing findings are historical.
- Resolved 2026-10-01: Created and pushed the public portfolio repository `Vince-aboy/aircon-service-automation` at commit `9d02f79`.
- Resolved 2026-10-01: Deployed and verified synthetic-only staging at `https://vinceaboy.com/balik-lamig/`; the n8n production webhook and one-minute VPS worker automatically processed a fictional outbox event.
- Resolved 2026-10-03: The published protected n8n workflow now updates the three core owner-reporting views: Daily Schedule, Client Summary, and append-only Service History. Its final response is a fixed `automation_status: processed` acknowledgement after all three paths merge.
- Open 2026-10-03: Create `Customer Directory` in the owner spreadsheet and implement a safe SQL-backed one-time backfill plus a future upsert path. It must be keyed by stable customer identity, not booking reference.
- Open 2026-10-03: Review the exact live Google Sheets tab list before deleting or repurposing any tab. Potentially deferred tabs include Cancelled Requests, Automation Log, and blank/default tabs; none may be deleted until explicitly approved.
- Open 2026-10-03: Finish the final-response behavior for the `Prepare Dispatcher Notice` and `Reject Event` n8n branches before activating event types that route through either branch.
- Open 2026-10-03: This Codex conversation does not currently have access to the user's connected Google Drive, although another VS Code Codex conversation does. Use a Drive-connected session for tab listing, creation, or deletion.

## Security follow-up

- Resolved 2026-09-30: The local `aircon_app` password that appeared in a failed-migration traceback was rotated. The migration was then applied with a password-free URL plus temporary `PGPASSWORD`. Do not record or reproduce any password in project files, screenshots, Git, or messages.
