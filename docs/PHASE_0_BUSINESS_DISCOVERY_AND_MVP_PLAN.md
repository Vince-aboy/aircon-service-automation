# Phase 0 — Business Discovery and MVP Plan

## Source brief

Build a realistic, portfolio-grade aircon cleaning and service automation prototype for a Philippine small business. Use Python, PostgreSQL, and n8n; begin with synthetic data and a controlled booking workflow. Add validation, human review, notifications, appointment status, reminders, error handling, and documentation incrementally. Do not add Facebook/Meta integration, payments, AI, real customer data, or production deployment without explicit authorization.

## Business problem

A small aircon-service business commonly receives booking requests through calls, chat, or a simple form. Staff then copy details into notes, check availability manually, contact the customer, and track service status informally. This creates missed details, double booking risk, inconsistent follow-up, and poor visibility into the work queue.

## Target user and roles

| Role | Need | MVP responsibility |
| --- | --- | --- |
| Customer | Request a cleaning or service visit | Submit a controlled booking request |
| Admin / dispatcher | Verify details and choose a service slot | Review, confirm, cancel, and update appointments |
| Technician | Know assigned work and report outcome | View assigned appointment and mark it completed (later increment) |

## Assumptions

- The initial synthetic service area is Urban Deca Homes, Tondo, Manila.
- [UNCONFIRMED] The initial service is residential split-type aircon cleaning; repair diagnosis may be requested but is not scheduled automatically.
- [UNCONFIRMED] The business has a small team and uses manual approval before a booking becomes confirmed.
- [UNCONFIRMED] A service visit is booked in a time window, not an exact arrival minute.

## Confirmed operating defaults

- Service area: Urban Deca Homes, Tondo, Manila only.
- Working days: Monday through Saturday.
- Working hours: 09:00–17:00 Philippine time.
- Initial capacity: two appointment windows per technician each day.

## Recommended MVP

The MVP is a local, single-business booking and admin-review prototype.

### In scope

- Public booking form for synthetic customer details and one or more aircon units.
- Server-side validation, including required fields, Philippine mobile-number format, service-area rule, future date, and valid time window.
- A booking request starts as `pending_review`; it is not self-confirmed.
- Admin dashboard to review a request, assign a technician and appointment slot, then confirm or cancel it.
- Appointment status history: `pending_review` → `confirmed` → `en_route` → `completed`; cancellation is available from non-final states.
- Simulated notification and reminder records. They are stored in an outbox/log and never sent to real recipients.
- Synthetic seed data, automated tests for core rules, error handling, and basic documentation.

### Explicitly out of scope

- Facebook/Meta, WhatsApp, SMS, email delivery, payment gateways, AI, real customer data, public deployment, and production claims.
- Live route optimisation, inventory, accounting, multi-branch support, and automated repair quotation.

## Manual booking process mapped to the MVP

```text
Customer submits request
  → system validates and creates PENDING_REVIEW booking
  → admin checks address, units, request, and capacity
  → admin selects technician and slot
  → system marks appointment CONFIRMED and records simulated confirmation
  → reminder job identifies upcoming confirmed appointments and records simulated reminder
  → technician/admin progresses EN_ROUTE then COMPLETED
  → system records simulated follow-up eligibility
```

## Website flow

1. `/book` — customer enters contact, address, service, units, preferred date/window, and notes.
2. `POST /bookings` — server validates input and writes a `pending_review` booking.
3. `/booking-received` — shows a non-binding request reference and explains that staff will review it.
4. `/admin/bookings` — staff sees requests requiring review.
5. `/admin/bookings/{id}` — staff confirms/cancels, assigns a technician, and updates status.

## Success criteria for the MVP

- A valid synthetic booking can be created and appears in the admin review queue.
- Invalid input is rejected with understandable messages and no partial record.
- An admin can confirm one appointment and a capacity/conflict rule prevents an invalid confirmation.
- Each status change is recorded with time and actor type.
- A simulated notification/reminder is logged without sending a real message.
- Tests demonstrate the validation and booking-state rules.

## Technology decision

- Python 3.11 with FastAPI: the locally available, supported runtime; it provides clear request validation, a testable backend, and a professional portfolio fit.
- Jinja2 templates plus minimal CSS: fastest path to a real usable website without a separate frontend application.
- PostgreSQL: requested relational database and appropriate for bookings, conflicts, and audit history.
- SQLAlchemy + Alembic: database models and safe schema migrations.
- n8n, introduced after the core booking flow works: orchestrates local/simulated reminders and error paths without making it critical to the first increment.
- Pytest: automated verification of business rules.

## Guardrails

- Use fictional names, contact details, addresses, and technicians only.
- Treat a request as unconfirmed until an admin approves it.
- Never make external HTTP calls or send messages during the prototype without written authorization.
- Describe the result as a local prototype, never as production-ready.
