# Phase 11 — Owner Reporting and Google Sheets Synchronization

## Purpose

Create an owner-facing reporting layer for the synthetic Balik-Lamig workflow. PostgreSQL remains the source of truth. Google Sheets becomes a readable operations view updated through n8n.

This phase begins with mapping and documentation. Workflow implementation starts only after the data contract, sheet structure, and edge cases are reviewed.

The detailed payload contract is documented in [docs/PHASE_11_EVENT_CONTRACT.md](docs/PHASE_11_EVENT_CONTRACT.md).

## Proposed flow

```text
Balik-Lamig event -> validate synthetic event -> normalize data
  -> identify event type -> upsert Google Sheets records
  -> update daily schedule -> write automation log
  -> return processed or rejected response
```

## Existing source data

| Reporting field | Existing source |
| --- | --- |
| Booking ID | `BookingRequest.reference_code` |
| Client name | `Customer.full_name` |
| Phone | Customer mobile; mask in reporting where appropriate |
| Email | Customer email, when supplied |
| Address | Service address |
| Service | Service type |
| Aircon type | Booking request |
| Preferred date | Booking request |
| Assigned date/time | Appointment schedule |
| Team | Service team |
| Current status | Booking and appointment status |
| Event history | Booking, appointment, and outbox history |
| Delivery result | Outbox status, attempts, errors, and retry time |

## Proposed Google Sheets tabs

- `Daily Schedule` — owner’s primary view of scheduled work.
- `Client Summary` — one current row per synthetic client/request.
- `Service History` — status changes and completed work.
- `Cancelled Requests` — cancelled records and reasons.
- `Automation Log` — event ID, event type, result, attempts, and errors.
- `Lists` — controlled teams, statuses, services, and reference values.

## Event-to-sheet map

| Event | Owner reporting action |
| --- | --- |
| Request submitted | Add or update the client summary as pending review. |
| Request approved | Update the review status. |
| Request declined | Add or move the record to cancelled requests. |
| Appointment scheduled | Add or update the daily schedule. |
| Appointment cancelled | Mark the schedule row cancelled and log the reason. |
| Job en route | Update current status and service history. |
| Job in progress | Update current status and service history. |
| Job completed | Update status and completion time. |
| Delivery failed | Add the error to the automation log. |
| Duplicate event | Ignore safely using the stable event ID. |

## Edge cases to map before implementation

- Duplicate event delivery.
- Same client submits another request.
- Appointment rescheduling.
- Cancellation after scheduling.
- Two appointments on one date.
- Occupied team or time block.
- n8n unavailable.
- Google Sheets unavailable.
- Missing optional email.
- Invalid or non-synthetic event.
- Events arriving out of order.
- Retry after partial processing.
- Existing target sheet row.
- Multiple historical bookings for one client.

## Design rules

- PostgreSQL is authoritative.
- Google Sheets is a reporting and visibility layer.
- n8n synchronizes events; it does not become the booking database.
- Every event needs a stable idempotency key before a sheet write.
- Sheet writes must be repeatable without duplicate owner records.
- Scope remains synthetic-only; no real messaging, payments, or customer data.
- Use one normalized event path with small, documented branches.

## Acceptance criteria

- Event contract, sheet schemas, and edge cases are documented first.
- Every current lifecycle event has a defined sheet action.
- Duplicate, retry, reschedule, cancellation, and failure behavior is defined.
- A synthetic event can update owner reporting without changing PostgreSQL source data.
- The owner can see the day’s schedule and current request status in one place.
- n8n executions and sheet errors remain traceable in the automation log.

## Status

Planning started. No Google Sheets connection or n8n workflow change has been made yet.
