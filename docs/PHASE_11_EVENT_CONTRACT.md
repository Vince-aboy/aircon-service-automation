# Phase 11 Event Contract

## Purpose

Define the canonical synthetic event that the Balik-Lamig application will send to n8n for owner reporting. This contract is the reference for the future Google Sheets workflow.

## Previous minimal payload

Before Phase 11 enrichment, the bridge sent only the following fields:

```json
{
  "event_type": "appointment_scheduled",
  "booking_reference": "AC-20261001-EXAMPLE",
  "status": "pending",
  "synthetic_only": true,
  "recipient_masked": "0950****456"
}
```

This is sufficient for the current synthetic n8n processor, but it does not contain enough information for an owner schedule or client summary.

## Target canonical payload

The owner-reporting event should contain the following shape:

```json
{
  "event_id": "synthetic-outbox-123",
  "idempotency_key": "synthetic-outbox-123",
  "event_type": "appointment_scheduled",
  "occurred_at": "2026-10-03T09:00:00+08:00",
  "booking_reference": "AC-20261003-EXAMPLE",
  "booking_status": "scheduled",
  "appointment_status": "confirmed",
  "synthetic_only": true,
  "client": {
    "name": "Fictional Client",
    "phone_masked": "0950****456",
    "email": null
  },
  "service": {
    "name": "Aircon Cleaning",
    "aircon_type": "Window Type",
    "unit_count": 1
  },
  "location": {
    "address_line": "Fictional Building 11 Unit 0411",
    "barangay": "Urban Deca Homes",
    "city": "Manila",
    "coverage_area": "Urban Deca Homes, Tondo"
  },
  "schedule": {
    "preferred_date": "2026-10-03",
    "scheduled_date": "2026-10-03",
    "time_window": "09:00-11:00",
    "team": "Team A",
    "technician": "Team A Lead (fictional)"
  },
  "delivery": {
    "outbox_status": "pending",
    "attempt_count": 0,
    "last_error": null,
    "next_attempt_at": null
  }
}
```

## Field rules

| Field | Source | Rule |
| --- | --- | --- |
| `event_id` | Notification outbox ID | Stable identifier for the event. |
| `idempotency_key` | Outbox ID | Must remain stable across retries. |
| `event_type` | Outbox event type | Use the existing lifecycle event names. |
| `occurred_at` | Event creation/history timestamp | Use ISO 8601 with the project timezone. |
| `booking_reference` | Booking request | Owner-facing reference code. |
| `booking_status` | Booking request | Current request status. |
| `appointment_status` | Appointment | Include when an appointment exists; otherwise `null`. |
| `synthetic_only` | Event safety marker | Must always be `true` in this project. |
| `client.name` | Customer | Fictional data only. |
| `client.phone_masked` | Customer mobile | Never send an unmasked phone to owner reporting. |
| `client.email` | Customer email | Optional; `null` when absent. |
| `service.*` | Booking request and service type | Use current database values. |
| `location.*` | Address | Use the configured synthetic coverage area. |
| `schedule.*` | Booking request and appointment | Scheduled fields are `null` before assignment. |
| `delivery.*` | Notification outbox | Supports owner-visible delivery troubleshooting. |

## Event types

- `request_submitted`
- `request_approved`
- `request_declined`
- `appointment_scheduled`
- `appointment_cancelled`
- `appointment_en_route`
- `appointment_in_progress`
- `appointment_completed`

## n8n validation rules

1. Reject the event unless `synthetic_only` is exactly `true`.
2. Reject the event if `event_id`, `idempotency_key`, `event_type`, or `booking_reference` is missing.
3. Treat a repeated `idempotency_key` as an already-processed event.
4. Keep dates and times in ISO format; display formatting belongs in Google Sheets.
5. Do not send messages, emails, or payments from this owner-reporting workflow.
6. Return a clear response containing `automation_status` and the event identifier.

## Google Sheets mapping

- `Daily Schedule`: booking reference, scheduled date, time window, client name, masked phone, service, team, appointment status, last update.
- `Client Summary`: booking reference, client name, masked phone, email, address, service, preferred date, current status, last update.
- `Service History`: event ID, booking reference, event type, previous status, new status, occurred time, note.
- `Cancelled Requests`: booking reference, client name, cancellation status, reason, occurred time.
- `Automation Log`: event ID, idempotency key, event type, n8n result, sheet result, attempts, error, processed time.

## Status

Documented and implemented in the application payload. No Google Sheets node or Google credential has been added yet.
