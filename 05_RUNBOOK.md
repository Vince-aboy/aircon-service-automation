# Runbook

## Purpose
- Record operational steps, repeatable procedures, and run instructions.

## Work session workflow
1. Run startup and select or create the project.
2. Run the work prompt for the active project.
3. Apply the memory keeper prompt during active work.
4. Read `00_HANDOFF.md` first.
5. Read `01_PROJECT_MAP.md` next.
6. Check `03_DECISIONS.md` for durable rules.
7. Check `06_ARTIFACT_REGISTER.md` for important files.
8. Do the actual build work.
9. Record meaningful progress in `02_WORKLOG_HISTORY.md`.
10. Update `03_DECISIONS.md` if a lasting rule changes.
11. Update `06_ARTIFACT_REGISTER.md` if a new important file or asset appears.
12. Update `00_HANDOFF.md` at the end of the session.

## Entries

- VPS deploy and restart
  - Pull reviewed code: `cd /home/aboy/apps/balik-lamig && git pull --ff-only origin main`
  - Restart after code or environment changes: `sudo systemctl restart balik-lamig`
  - Check health: `sudo systemctl status balik-lamig --no-pager -l`

- VPS SQL roster synchronization
  - Run the idempotent roster/legacy-cleanup seed through the protected systemd environment: `sudo bash -c 'set -a; . /etc/balik-lamig/balik-lamig.env; set +a; cd /home/aboy/apps/balik-lamig; .venv/bin/python -m app.database.seed'`
  - Current result: `0 service type(s), 0 technician(s), 0 team(s), and 0 team membership(s) added.` Existing appointments remain preserved while legacy fictional assignments are transferred to real leads.

- Temporary supervised demonstration access
  - Set `AIRCON_STAFF_AUTH_ENABLED=false` only in `/etc/balik-lamig/balik-lamig.env`, restart, and supervise the session.
  - Restore `AIRCON_STAFF_AUTH_ENABLED=true` and restart immediately afterward.
- Local booking-page preview
  - PASTE THIS — WINDOWS POWERSHELL
  - Expected prompt: `PS D:\0.1_NEW_PROFILE\1. PROJECTS\0009_AIRCON_SERVICE_AUTOMATION>`
  - Use temporary `PGPASSWORD` and password-free `AIRCON_DATABASE_URL` variables as in the local migration procedure, then run: `.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
  - Open `http://127.0.0.1:8000/book` on the same machine. Keep the host as `127.0.0.1`; do not use `0.0.0.0` or publish the local server.
  - Stop with `Ctrl+C`, then clear the terminal credential variables.

- Local migration with terminal-only credentials
  - Set `PGPASSWORD` only for the current PowerShell session through `Get-Credential`; set `AIRCON_DATABASE_URL` without a password; run `.\.venv\Scripts\python -m alembic upgrade head`; clear both environment variables afterward.
  - Do not put an encoded password into `AIRCON_DATABASE_URL`: Alembic configuration interpolation can disclose it in an error message.

- Local database identity check
  - PASTE THIS — WINDOWS POWERSHELL
  - Expected prompt: `PS C:\Users\vince>`
  - Run: `psql -U aircon_app -d aircon_service_dev`
  - Enter the password only at the hidden prompt; do not save or paste it into project files.
  - At the PostgreSQL prompt, run: `SELECT current_user, current_database();`

- Local automated test
  - PASTE THIS — WINDOWS POWERSHELL
  - Expected prompt: `PS D:\0.1_NEW_PROFILE\1. PROJECTS\0009_AIRCON_SERVICE_AUTOMATION>`
  - Run: `.\.venv\Scripts\python -m pytest -q`
  - Expected current result: `1 passed`.
