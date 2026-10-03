# Phase 11 Live n8n Reporting Verification

## Purpose

Record the actual owner-reporting workflow that was published and tested on 2026-10-03. This is an operations handoff, not a substitute for the broader Phase 11 design.

## Live workflow

```text
Webhook -> If -> If1 -> Mark Processed
                         -> Upsert Daily Schedule Row
                         -> Upsert Client Summary
                         -> Append Service History
                         -> Merge (Append, 3 inputs)
                         -> Return Processed Response
```

The three Google Sheets nodes are parallel branches from `Mark Processed`. The Merge waits for all three node results. The final Edit Fields/Set node returns a fixed value:

```json
{"automation_status":"processed"}
```

## Why the final response matters

The local worker accepts only the expected acknowledgement. Google Sheets nodes output their own result rows, not `automation_status: processed`. Returning a Sheets result directly made the local worker preserve events as `pending` and retry them even though the Sheets operation had succeeded. The final response node corrected this; four affected pending events became recorded.

## Sheet node configuration

| Node | Operation | Target | Key / behavior |
| --- | --- | --- | --- |
| Upsert Daily Schedule Row | Append or Update Row | `Daily Schedule` | Match `booking_reference` |
| Upsert Client Summary | Append or Update Row | `Client Summary` | Match `booking_reference` |
| Append Service History | Append Row | `Service History` | One row per delivered event |

All mappings use the incoming webhook event as `$json.body...`; parallel routing preserves that payload for every Sheets node.

## Service History mappings

| Column | Mapping |
| --- | --- |
| `event_id` | `$json.body.event_id` |
| `idempotency_key` | `$json.body.idempotency_key` |
| `occurred_at` | `$json.body.occurred_at` |
| `booking_reference` | `$json.body.booking_reference` |
| `event_type` | `$json.body.event_type` |
| `booking_status` | `$json.body.booking_status` |
| `appointment_status` | `$json.body.appointment_status` |
| `note` | `$json.body.note` |
| `synthetic_only` | `$json.body.synthetic_only` |

## Controlled evidence

| Event | Result |
| --- | --- |
| Jannet booking schedule | Created the current Daily Schedule and Client Summary reporting state. |
| Reschedule (`outbox-7`) | Updated Client Summary to Team A / Pedro Ecleo / confirmed and changed Daily Schedule to the new time. |
| Reschedule back (`outbox-8`) | Restored the intended time block and appended a Service History row for `appointment_rescheduled`, including the internal note. |

No customer notification, payment, or external dispatcher delivery was enabled or sent.

## Operational check after any n8n edit

1. Publish the workflow.
2. Generate one controlled synthetic scheduling/rescheduling event.
3. Allow the VPS worker interval to deliver it, or use the approved controlled retry path.
4. Confirm the app Automation page changes the event to `recorded` rather than `pending` or `failed`.
5. Confirm exactly one intended current row in Daily Schedule and Client Summary, plus one new append-only Service History row.
6. If the event remains pending with an unexpected-response error, inspect the final n8n response first; it must be the fixed processed JSON after the Merge.

## Remaining work

- Customer Directory creation, SQL-backed backfill, and upsert design.
- Exact tab inventory and approved cleanup only; no unreviewed tab deletion.
- Final responses for the dispatcher-notice and rejection branches before their routes are activated.

