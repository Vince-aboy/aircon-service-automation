# Balik-Lamig: Aircon Service Automation

## Current operational snapshot — 2026-10-03

The live VPS deployment is operating as the owner/dispatcher workspace at `https://vinceaboy.com/balik-lamig/staff`. The dashboard label is `Boss EMER`. The application includes dashboard counts, request review, dispatcher scheduling, appointment and customer directories, workforce management, audit history, safe rescheduling/cancellation controls, owner-reporting automation, and PostgreSQL as the source of truth.

The active technician roster contains the 16 owner-provided employees: Pedro Ecleo, Brian Elipides, John Harris, Jestony Rollon, Snowdon, Mavien, Richard, Jommel, Marlon, Aweng, Robert, Ken, Mark, Joeking, Dexter, and Clifford. Fictional technicians were retired after existing appointments were transferred to the real team leads.

For a supervised demonstration only, staff authentication is temporarily disabled with `AIRCON_STAFF_AUTH_ENABLED=false`. Re-enable it immediately afterward with `true` and restart the service. The default remains secure/authenticated.

A controlled aircon-service workflow with a safe local prototype mode and an explicitly enabled live owner-operations mode. It demonstrates how a service request can move from staff review through team scheduling, job progress, a durable outbox, and protected n8n reporting.

> **Safety boundary:** Live mode is opt-in, staff routes require credentials, customer messaging and payments remain disabled, and PostgreSQL remains authoritative.

## What it demonstrates

- Staff-reviewed service requests before scheduling
- Team-based scheduling using fixed service blocks
- Job lifecycle tracking: confirmed, en route, in progress, completed, or cancelled
- Immutable status history for traceability
- A transactional outbox for owner-reporting automation events
- A protected n8n webhook bridge with retry and failure evidence
- Responsive staff views, including a Phase 0-9 visual roadmap

## System flow

```text
Service request
  -> Staff review
  -> Team schedule
  -> Job progress
  -> Local SQL outbox
  -> Protected n8n test workflow
```

Local SQL remains the source of truth. The VPS deployment uses a protected n8n webhook and an owner-reporting delivery worker. Set `AIRCON_OPERATION_MODE=live` only after restricting the Google Sheet and configuring staff credentials. No customer messaging or payment processing is enabled.

## Tech stack

- Python 3.11+
- FastAPI and Jinja templates
- PostgreSQL and SQLAlchemy
- Alembic migrations
- Pytest
- n8n test webhook (Header Auth)

## Run locally

1. Create and activate a Python virtual environment.
2. Install the project with development tools:

   ```powershell
   pip install -e ".[dev]"
   ```

3. Supply `AIRCON_DATABASE_URL` only in the current terminal session, then apply migrations:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```

4. Start the local server:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

5. Open `http://127.0.0.1:8000`.

See [05_RUNBOOK.md](05_RUNBOOK.md) for the controlled local workflow and credential-handling guidance.

## Verification

```powershell
.\.venv\Scripts\pytest.exe -q
```

Latest local verification: **44 passed, 5 skipped**. Skipped integration tests require a terminal-only database configuration.

## Project documentation

- [Phase 0-9 visual roadmap](08_PHASES_0_TO_9_ROADMAP.md)
- [Phase 10 delivery design](07_PHASE_10_AUTOMATIC_DELIVERY_DESIGN.md)
- [Architecture and project map](01_PROJECT_MAP.md)
- [Decisions and safety boundaries](03_DECISIONS.md)
- [VPS and GitHub release plan](docs/VPS_AND_GITHUB_RELEASE_PLAN.md)
- [Phase 11 owner reporting status](09_PHASE_11_OWNER_REPORTING_AND_GOOGLE_SHEETS.md)
- [Phase 11 event contract](docs/PHASE_11_EVENT_CONTRACT.md)
- [Phase 11 n8n Google Sheets workflow](docs/PHASE_11_N8N_GOOGLE_SHEETS_WORKFLOW.md)
- [Phase 11 live reporting verification](docs/PHASE_11_LIVE_N8N_REPORTING_VERIFICATION.md)
- [Real-data operations mode](docs/REAL_DATA_OPERATIONS_MODE.md)

## Security and privacy

- Never commit `.env` files, database credentials, webhook keys, n8n credential exports, or private keys.
- Database and n8n values are supplied temporarily through environment variables.
- Keep staff routes and the owner Google Sheet restricted to approved staff.
- Full phone numbers are limited to authenticated owner reporting; public pages never display them.
- Credentials and webhook keys stay outside Git and chat.

## Status

Phases 0-10 are complete. Phase 11 core owner reporting is live: Daily Schedule and Client Summary upserts plus append-only Service History, all acknowledged by the published protected n8n workflow. Customer Directory backfill and non-core reporting tabs remain deferred; customer messaging and payments remain out of scope.
