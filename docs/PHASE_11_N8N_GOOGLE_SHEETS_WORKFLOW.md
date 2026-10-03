# Phase 11 n8n → Google Sheets Workflow

## Goal

Create an owner-facing reporting workflow for Balik-Lamig events in either local prototype mode or live owner-reporting mode. PostgreSQL remains authoritative; Google Sheets is only a readable operations view. This workflow must not send customer messages, make payments, or change booking records.

## n8n node order

```text
Webhook
  → Validate Synthetic Event
  → Normalize Event
  → Check Automation Log (idempotency)
  → Duplicate?
      ├─ yes → Log Duplicate → Respond 200 idempotent
      └─ no → Route Event Type
                  ├─ request/review events → Upsert Client Summary
                  ├─ scheduled/status events → Upsert Client Summary
                  │                              → Upsert Daily Schedule
                  ├─ cancelled events → Upsert Client Summary
                  │                       → Upsert Cancelled Requests
                  └─ all valid events → Append Service History
                                        → Append Automation Log
                                        → Respond 200 processed
```

## Node responsibilities

1. **Webhook** — receive the protected HTTPS production webhook from the application.
2. **Validate Event** — require `event_id`, `idempotency_key`, `event_type`, `booking_reference`, and `operation_mode`. Accept `synthetic_only=true` for local prototype events and `operation_mode=live_owner_reporting` for approved live owner reporting.
3. **Normalize Event** — flatten nested client, service, location, schedule, and delivery fields into a consistent internal object. Keep ISO values for storage; use Sheets formatting for display.
4. **Check Automation Log** — search `Automation Log` by `idempotency_key`.
5. **Duplicate?** — if found, do not write business rows again. Record a duplicate result and return a successful idempotent response.
6. **Route Event Type** — use a Switch node for lifecycle events, not separate copies of the full workflow.
7. **Upsert Client Summary** — one current row per booking reference. Update the row instead of appending another row.
8. **Upsert Daily Schedule** — one row per appointment. Use `booking_reference + scheduled_date + time_window` as the operational key.
9. **Upsert Cancelled Requests** — maintain a cancellation view without deleting historical events.
10. **Append Service History** — append one immutable event row for every accepted event.
11. **Append Automation Log** — record the event, n8n result, sheet result, attempts, and any error.
12. **Respond to Webhook** — return JSON such as `{ "automation_status": "processed", "event_id": "..." }`.

## Sheet keys and columns

### Daily Schedule

Stable key: `booking_reference + scheduled_date + time_window`

`schedule_key`, `scheduled_date`, `time_window`, `booking_reference`, `client_name`, `phone`, `service`, `aircon_type`, `unit_count`, `address`, `team`, `technician`, `appointment_status`, `booking_status`, `last_event_id`, `last_update`

### Client Summary

Stable key: `booking_reference`

`booking_reference`, `client_name`, `phone`, `email`, `address`, `barangay`, `city`, `coverage_area`, `service`, `aircon_type`, `preferred_date`, `scheduled_date`, `time_window`, `current_status`, `team`, `technician`, `last_event_id`, `last_update`

### Service History

Append-only key: `event_id`

`event_id`, `idempotency_key`, `occurred_at`, `booking_reference`, `event_type`, `booking_status`, `appointment_status`, `note`, `synthetic_only`

### Cancelled Requests

Stable key: `booking_reference`

`booking_reference`, `client_name`, `phone_masked`, `service`, `scheduled_date`, `time_window`, `cancellation_status`, `reason`, `last_event_id`, `occurred_at`

### Automation Log

Stable key: `idempotency_key`

`event_id`, `idempotency_key`, `event_type`, `booking_reference`, `received_at`, `n8n_result`, `sheet_result`, `delivery_attempts`, `error`, `processed_at`, `operation_mode`, `synthetic_only`

## Event routing

| Event type | Required sheet actions |
| --- | --- |
| `request_submitted` | Upsert Client Summary; append Service History; log event |
| `request_approved` | Upsert Client Summary; append Service History; log event |
| `request_declined` | Upsert Client Summary; upsert Cancelled Requests; append history; log event |
| `appointment_scheduled` | Upsert Client Summary; upsert Daily Schedule; append history; log event |
| `appointment_cancelled` | Update Client Summary; upsert Daily Schedule as cancelled; upsert Cancelled Requests; append history; log event |
| `appointment_en_route` | Update Daily Schedule and Client Summary; append history; log event |
| `appointment_in_progress` | Update Daily Schedule and Client Summary; append history; log event |
| `appointment_completed` | Update Daily Schedule and Client Summary; append history; log event |

## Failure and edge-case behavior

- Invalid events are rejected with HTTP 400 and written to `Automation Log` when possible.
- Duplicate deliveries return HTTP 200 with `automation_status: duplicate`.
- Google Sheets errors do not modify PostgreSQL; the webhook should return a failure response so the outbox worker can retry.
- A partial Sheets update is recoverable because every business row has a stable key and the event log is idempotent.
- Events arriving out of order must not replace a newer row. Compare `occurred_at` before updating current-state tabs.
- Reschedules update the current schedule key and preserve the old state in `Service History`.
- Missing email remains blank.
- In live owner-reporting mode, `client.phone` is full and must only be written to the restricted owner sheet. In local prototype mode, use `client.phone_masked`.
- No outbound customer communication or payment processing is permitted in this workflow.

## Credential and activation boundary

The Google Sheets credential is created only inside n8n. It must not be placed in Git, the VPS environment file, application code, or this documentation. Before live activation, confirm the spreadsheet ID, exact tab names, restricted sharing scope, and the live field mappings. Start with one controlled request, then allow normal delivery after the test passes.

## Implementation status

Application payload enrichment and the controlled live-mode boundary are implemented locally. Update the existing n8n Google Sheets nodes to use the live mappings before enabling live operation.
