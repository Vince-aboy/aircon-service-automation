# Open Loops

## Before Phase 1

- Resolved 2026-09-30: Use Urban Deca Homes, Tondo, Manila, Monday–Saturday, 09:00–17:00, and two appointment windows per technician as the initial synthetic defaults.
- Resolved 2026-09-30: Python 3.11, Git, PostgreSQL 17 client/server, and Docker are installed. The PostgreSQL service is running. Node.js and n8n are not installed; Docker Desktop is not running.
- [UNCONFIRMED] Identify the local PostgreSQL database role and credential method before connecting. No password will be requested, exposed, or stored in this project.
- Resolved 2026-09-30: Vince states n8n is already installed on the personal VPS. Do not assume its current security/configuration state or connect this project until a fresh read-only audit and explicit approval.
- [UNCONFIRMED] Decide whether the local admin area will use a demo-only password in Phase 4 or remain accessible only on localhost without authentication during earlier learning stages.

## Release planning

- [UNCONFIRMED] Confirm the current VPS security, n8n, and service state with a read-only audit immediately before any project connection or deployment; existing findings are historical.
- Deferred until Phase 7: create the private `aircon-service-automation` repository, choose the private staging route/subdomain, and approve any VPS user/database/reverse-proxy changes.
- Deferred until after staging: decide whether to create a separately sanitized public GitHub repository or expose a public portfolio demo.

## Security follow-up

- Resolved 2026-09-30: The local `aircon_app` password that appeared in a failed-migration traceback was rotated. The migration was then applied with a password-free URL plus temporary `PGPASSWORD`. Do not record or reproduce any password in project files, screenshots, Git, or messages.
