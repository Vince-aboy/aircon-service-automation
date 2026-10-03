# Phase 11 — Owner Reporting and Google Sheets Synchronization

## Current status

Phase 11 core reporting is live and verified for the synthetic owner-operations workflow. PostgreSQL remains authoritative. Google Sheets is a restricted, readable reporting layer updated by the protected n8n webhook; it is not a booking database, customer-messaging system, or payment system.

The detailed event shape is in [docs/PHASE_11_EVENT_CONTRACT.md](docs/PHASE_11_EVENT_CONTRACT.md). The original broader workflow design and the current live implementation are distinguished in [docs/PHASE_11_N8N_GOOGLE_SHEETS_WORKFLOW.md](docs/PHASE_11_N8N_GOOGLE_SHEETS_WORKFLOW.md). Controlled live evidence is recorded in [docs/PHASE_11_LIVE_N8N_REPORTING_VERIFICATION.md](docs/PHASE_11_LIVE_N8N_REPORTING_VERIFICATION.md).

## Verified live reporting scope

| Tab | Purpose | Write pattern | Key |
| --- | --- | --- | --- |
| `Daily Schedule` | Current operational appointment assignment | Upsert | `booking_reference` |
| `Client Summary` | Current state of one booking/request | Upsert | `booking_reference` |
| `Service History` | Owner-readable event timeline | Append | one row per delivered event |

The current `Client Summary` is deliberately not a master customer directory: a single customer can have multiple bookings. A later `Customer Directory` will be keyed by stable customer identity and safely backfilled from PostgreSQL.

## Verified n8n path

```text
Protected Webhook
  -> synthetic/safety If nodes
  -> Mark Processed
  -> parallel reporting fanout
       -> Upsert Daily Schedule Row
       -> Upsert Client Summary
       -> Append Service History
  -> Merge (Append mode; 3 inputs)
  -> Return Processed Response
```

`Return Processed Response` returns the fixed JSON acknowledgement `automation_status: processed`. This final node is required: a Google Sheets node returns sheet-row data rather than the acknowledgement expected by the local delivery worker. Returning sheet data directly makes the worker retain a successfully delivered event as pending and retry it.

## Source and reporting boundaries

| Reporting data | Authoritative source |
| --- | --- |
| Booking reference, client, service, address | PostgreSQL booking/customer records |
| Appointment date, time, team, technician | PostgreSQL appointment records |
| Current lifecycle state | PostgreSQL booking and appointment records |
| Event ID, idempotency key, occurrence time, note | PostgreSQL outbox event |
| Technical delivery state and retries | PostgreSQL outbox and n8n execution history |

The app payload includes `note`, so Service History can show the operator-readable event explanation without fabricating it in n8n.

## Controlled verification evidence

Jannet Aboy booking `AC-20261003-CC71C4CB` was used only as a controlled synthetic operations test:

1. It was scheduled for Team A.
2. It was rescheduled to another time block and the current-state reporting rows updated.
3. It was rescheduled back to the intended block. Service History appended `outbox-8`, event type `appointment_rescheduled`, with the recorded internal note.

The app outbox showed the earlier acknowledgement defect as pending events. Once the final response was corrected, all four affected events became recorded. No customer message was sent at any stage.

## Deferred work and safety rules

- Create `Customer Directory` only after defining its stable key, columns, one-time SQL backfill, and future upsert behavior.
- Do not delete, rename, or repurpose Sheets tabs until the exact live tab list has been reviewed and deletion is explicitly approved. Potential deferred tabs include `Cancelled Requests`, `Automation Log`, and blank/default tabs.
- `Cancelled Requests` and owner-facing `Automation Log` are not part of the present core reporting scope. Technical delivery review belongs in the app Automation page and n8n executions.
- The `Prepare Dispatcher Notice` and `Reject Event` branches require their own final-response handling before enabling event types that route through them.
- Keep Google credential material only in n8n; never place it in Git, application environment files, or project documentation.
