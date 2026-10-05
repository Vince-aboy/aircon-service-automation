# Project Map

## Purpose
- List the important folders and files for this project.

## Version 1 closeout
- Runtime application: `app/main.py` and `app/booking/service.py` contain the booking, scheduling, outbox, n8n payload, and reporting-health behavior.
- Owner Operations UI: `app/templates/admin_base.html`, `app/templates/staff_dashboard.html`, `app/templates/automation_outbox.html`, and the related staff templates provide the final operational workspace.
- Shared visual theme: `app/static/light-theme.css` applies the warm off-white, charcoal, gold, and muted-green palette to the public and staff workflows.
- n8n handoff: `docs/PHASE_11_CUSTOMER_DIRECTORY_UPSERT_HANDOFF.md` contains the Customer Directory node mapping, four-input Merge requirement, and controlled verification steps.
- Current destination after Version 1: Web Profile project.

## Structure
- `00_HANDOFF.md` - current project state and next step
- `01_PROJECT_MAP.md` - folder and file map
- `02_WORKLOG_HISTORY.md` - chronological work log
- `03_DECISIONS.md` - durable decisions and rules
- `04_PHASE_SUMMARY.md` - milestone summaries if used
- `05_RUNBOOK.md` - operational steps and procedures if used
- `06_ARTIFACT_REGISTER.md` - important files and assets
- `docs/` - business planning, implementation roadmap, release/security plan, and unresolved project questions
- `09_PHASE_11_OWNER_REPORTING_AND_GOOGLE_SHEETS.md` - owner reporting, event map, sheet plan, and edge cases for the next phase
- `docs/PHASE_11_EVENT_CONTRACT.md` - current and target n8n event payload, validation rules, and sheet mappings
- `app/` - Python application package; currently contains stable prototype metadata
- `app/database/` - SQLAlchemy table definitions for the controlled booking workflow
- `app/templates/` and `app/static/` - local booking form, receipt, staff-review queue, dispatcher board, job-progress controls, local automation outbox, and responsive prototype styling
- `tests/` - automated tests for project and later business-rule behavior
- `migrations/` - Alembic database migrations; `20260930_0006` is the current local job-progress schema head
- `alembic.ini` - migration-tool configuration; database credentials are supplied only at run time
- `pyproject.toml` - Python project metadata and test configuration
- `.gitignore` - exclusions for secrets, local environments, generated data, and editor files
- `README.md` - concise project overview and current local scope
- `0009_AIRCON_SERVICE_AUTOMATION.md` - full historical chat export and project transcript; reference/archive only, not the canonical current-state memory
- Local PostgreSQL: `aircon_service_dev` database with restricted `aircon_app` application role; credentials are intentionally not stored in the workspace

## Notes
- The project is initialized with the standard memory files.
- Application source, database definitions, workflow exports, tests, and documentation will be added incrementally as the project is built.
