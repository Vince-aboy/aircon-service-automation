# Artifact Register

- `07_PHASE_10_AUTOMATIC_DELIVERY_DESIGN.md` - Disabled-by-default automatic delivery design, retry/claim safeguards, and evidence.
- `08_PHASES_0_TO_9_ROADMAP.md` - Mermaid flowchart and completed-phase summary.
- `app/templates/phase_roadmap.html` - Browser-visible Phase 0–9 documentation roadmap.

## Purpose
- List important files, folders, and assets for the project.

## Categories
- Core memory files
- Source files
- Reference files
- Output files
- Assets and media

## Entries
- `00_HANDOFF.md`
- `01_PROJECT_MAP.md`
- `02_WORKLOG_HISTORY.md`
- `03_DECISIONS.md`
- `04_PHASE_SUMMARY.md`
- `05_RUNBOOK.md`
- `06_ARTIFACT_REGISTER.md`
- `docs/PHASE_0_BUSINESS_DISCOVERY_AND_MVP_PLAN.md` - business context, MVP scope, process map, and technology choices
- `docs/IMPLEMENTATION_ROADMAP.md` - phased learning/build roadmap and proposed data model
- `docs/OPEN_LOOPS.md` - unresolved business and local-environment questions
- `docs/VPS_AND_GITHUB_RELEASE_PLAN.md` - gated private-GitHub, VPS-staging, security, and portfolio-release plan
- `app/` - local Python application package
- `tests/test_project_info.py` - first passing automated test and production-boundary guard
- `pyproject.toml` - local Python/test-project definition
- `.gitignore` - prevents common secrets and generated local artifacts from being committed
- `README.md` - project overview
- Local PostgreSQL `aircon_service_dev` / `aircon_app` - dedicated development database and least-privilege application identity; no credentials stored
- `app/database/models.py` - eight-table SQLAlchemy controlled-booking schema
- `migrations/versions/20260930_0001_initial_booking_schema.py` - first reversible Alembic schema migration
- `migrations/versions/20260930_0002_add_coverage_area.py` - reversible migration that stores the Urban Deca Homes, Tondo coverage area
- `tests/test_booking_schema.py` - automated schema/business-rule checks
- `app/database/seed.py` - idempotent fictional service-type and technician seed command
- `app/database/session.py` - runtime-only database engine helper
- `tests/test_seed_reference_data.py` - seed-data scope and fictional-data checks
- `tests/integration/test_database_constraints.py` - rolled-back PostgreSQL constraint integration tests
- `app/booking/validation.py` - pre-database booking input validation and normalization
- `tests/test_booking_validation.py` - automated validation-rule tests
- `app/booking/service.py` - controlled validated-booking persistence service
- `tests/integration/test_booking_service.py` - rolled-back PostgreSQL tests for controlled booking creation
- `app/main.py` - local FastAPI health and controlled booking endpoints
- `tests/test_booking_api.py` - disposable in-memory API request/response tests
- `app/templates/booking_form.html` and `app/templates/booking_received.html` - local booking form and pending-review receipt
- `app/templates/staff_requests.html` - loopback-only read-only staff queue for pending requests
- `app/templates/automation_outbox.html` - local-only simulated automation event log and processor
- `app/booking/service.py` and `app/main.py` - opt-in one-event SQL outbox to n8n HTTPS bridge
- `09_PHASE_11_OWNER_REPORTING_AND_GOOGLE_SHEETS.md` - current owner-reporting scope, live workflow boundary, and deferred Google Sheets work
- `docs/PHASE_11_EVENT_CONTRACT.md` - event payload contract, including the owner-readable event note
- `docs/PHASE_11_N8N_GOOGLE_SHEETS_WORKFLOW.md` - target workflow design plus the verified live parallel reporting implementation
- `docs/PHASE_11_LIVE_N8N_REPORTING_VERIFICATION.md` - controlled evidence, acknowledgement safeguard, and operational recovery notes
- `migrations/versions/20260930_0004_add_booking_request_review_history.py` - reversible audited staff-review status-transition migration
- `migrations/versions/20260930_0005_add_two_team_dispatch.py` - reversible two-team and appointment-slot foundation migration
- `migrations/versions/20260930_0006_add_in_progress_appointment_status.py` - reversible field-job progress status migration
- `app/templates/dispatch_board.html` - loopback-only two-team dispatcher board
- `app/templates/appointment_details.html` and `app/templates/appointment_details_content.html` - loopback-only scheduled-job detail and local progress controls
- `app/static/dispatch_board.js` - local dispatcher-card modal behavior with full-page fallback
- `app/static/booking.css` - responsive local prototype styles
- `app/static/images/balik-lamig.png` - user-supplied Balik-Lamig prototype branding asset
- `https://www.rglairconditioning.com/contact-us` - public UX reference reviewed 2026-09-30 for minimalist contact-page booking flow; do not copy its content or branding
- `docs/BOOKING_UX_RESEARCH.md` - research-backed CTA, form-scope, and service-request-flow decision
- `docs/SCHEDULING_RESEARCH_AND_DEFAULTS.md` - researched two-team scheduling model and deliberately deferred scope
- `tests/test_booking_page.py` - isolated booking-form/receipt behavior tests
- `app/database/seed.py` - idempotent 16-person owner roster seed and safe fictional-technician cleanup
- `app/templates/staff_dashboard.html` - owner operations command center
- `app/templates/appointment_directory.html` and `app/templates/customer_directory.html` - operational records directories
- `app/templates/team_directory.html` - active workforce/team management
- `app/templates/activity_history.html` and `app/templates/staff_settings.html` - audit and deployment views
- `docs/SQL_LIVE_SYNC_RECORD.md` - applied VPS roster synchronization evidence
