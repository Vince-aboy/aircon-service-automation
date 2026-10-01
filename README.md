# Balik-Lamig: Aircon Service Automation

A local, synthetic-data portfolio prototype for a controlled aircon-service workflow. It demonstrates how a service request can move from staff review through team scheduling, job progress, a durable outbox, and a protected n8n test workflow.

> **Prototype boundary:** This project contains fictional data only. It does not send customer messages, accept payments, or claim production use.

## What it demonstrates

- Staff-reviewed service requests before scheduling
- Team-based scheduling using fixed service blocks
- Job lifecycle tracking: confirmed, en route, in progress, completed, or cancelled
- Immutable status history for traceability
- A transactional outbox for synthetic automation events
- A protected n8n test-webhook bridge with retry and failure evidence
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

Local SQL remains the source of truth. The VPS staging deployment uses a protected n8n webhook and a one-minute synthetic-only delivery worker. No customer messaging or production booking is enabled.

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

Latest local verification: **37 passed, 5 skipped**. Skipped integration tests require a terminal-only database configuration.

## Project documentation

- [Phase 0-9 visual roadmap](08_PHASES_0_TO_9_ROADMAP.md)
- [Phase 10 delivery design](07_PHASE_10_AUTOMATIC_DELIVERY_DESIGN.md)
- [Architecture and project map](01_PROJECT_MAP.md)
- [Decisions and safety boundaries](03_DECISIONS.md)
- [VPS and GitHub release plan](docs/VPS_AND_GITHUB_RELEASE_PLAN.md)

## Security and privacy

- Never commit `.env` files, database credentials, webhook keys, n8n credential exports, or private keys.
- Database and n8n values are supplied temporarily through environment variables.
- Do not use customer information: every displayed record is fictional and masked where appropriate.
- A public demo or always-on delivery worker requires a separate reviewed deployment decision.

## Status

Phases 0-9 are complete. Phase 10 has established delivery state, failure tracking, retry timing, and automatic synthetic-only VPS delivery. The public route is portfolio staging only; customer messaging, payments, and production claims remain out of scope.
