# Incremental Implementation Roadmap

Each phase has a testable exit condition. Do not start the next phase until its exit condition is met.

| Phase | Outcome | Exit evidence |
| --- | --- | --- |
| 0. Discovery and MVP planning | Approved scope, process, data model, and learning sequence | This plan plus a reviewed manual workflow |
| 1. Local foundation | Python project, local config, test runner, and PostgreSQL connection plan | Environment check and one passing test |
| 2. Data model | Migrated schema and synthetic seed data | Migration runs; seed data and relationship tests pass |
| 3. Controlled booking | Public booking page/API validates and creates reviewable requests | Valid/invalid booking tests pass |
| 4. Human review | Admin queue and appointment confirmation/cancellation | State-transition and capacity tests pass |
| 5. Service progress | Assigned appointments progress to completion with audit history | Status history test passes |
| 6. Automation simulation | n8n handles simulated reminder/follow-up events and failures | Local workflow test plus outbox evidence |
| 7. Portfolio finish and gated release | Documentation, screenshots, test report, security review, private GitHub repository, and optional VPS staging plan | Demo walkthrough, all tests, clean security review, and explicit approval for any external release |

## Proposed data model

| Entity | Purpose | Key fields |
| --- | --- | --- |
| `customers` | Synthetic request contact | id, full_name, mobile, email, created_at |
| `addresses` | Service location | id, customer_id, address_line, barangay, city, service_area_valid |
| `service_types` | Configurable work type | id, name, duration_minutes, active |
| `booking_requests` | Initial customer request | id, reference_code, customer_id, address_id, service_type_id, aircon_type, preferred_date, preferred_window, unit_count, notes, status |
| `booking_request_status_history` | Audited staff-review decisions | id, booking_request_id, from_status, to_status, actor_type, occurred_at, note |
| `technicians` | Fictional service personnel | id, display_name, active |
| `appointments` | Confirmed scheduled work | id, booking_request_id, service_team_id, technician_id, scheduled_start, scheduled_end, status |
| `appointment_status_history` | Audit trail | id, appointment_id, from_status, to_status, actor_type, occurred_at, note |
| `notification_outbox` | Simulated notifications only | id, booking_request_id, event_type, channel, recipient_masked, status, payload, created_at |

### Core rules

- A booking request must have valid contact, address, service type, unit count, future preferred date, and time window.
- Staff approval makes a request eligible for scheduling; a later scheduling action creates an appointment.
- One team cannot have two appointments starting in the same scheduled block.
- `completed` and `cancelled` are final states.
- Every appointment transition creates a history entry.
- Notification outbox entries are not delivered externally in this project stage.

## Learning sequence

1. Understand the business flow and scope before code.
2. Learn project setup, virtual environments, configuration, and automated tests.
3. Model relational data and run database migrations.
4. Build input validation and controlled request creation.
5. Build admin review and status transitions.
6. Automate only after the manual path is reliable.
7. Document and demo evidence honestly.
