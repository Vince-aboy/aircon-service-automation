# Customer Directory n8n branch handoff

This is the remaining n8n change for Balik-Lamig Version 1. The application already sends `customer_id` at the top level of every owner-reporting event. PostgreSQL remains authoritative; this branch only maintains a readable Google Sheets view.

## Workflow edit

In the published workflow, add a fourth parallel branch from `Mark Processed`:

```text
Mark Processed
  ├─ Upsert Daily Schedule Row
  ├─ Upsert Client Summary
  ├─ Append Service History
  └─ Upsert Customer Directory Row
           ↓
Merge (Append, 4 inputs)
  → Return Processed Response
```

Keep the final response node after the Merge. It must return exactly:

```json
{"automation_status":"processed"}
```

## Google Sheets node

Node name: `Upsert Customer Directory Row`

Operation: `Append or Update Row`

Target sheet: `Customer Directory`

Lookup key: `customer_id`

Map values from the webhook body:

| Sheet column | n8n expression |
|---|---|
| `customer_id` | `$json.body.customer_id` |
| `client_name` | `$json.body.client.name` |
| `phone` | `$json.body.client.phone` |
| `email` | `$json.body.client.email` |
| `address` | `$json.body.location.display` |
| `barangay` | `$json.body.location.barangay` |
| `city` | `$json.body.location.city` |
| `coverage_area` | `$json.body.location.coverage_area` |
| `booking_count` | `$json.body.customer_booking_count` |
| `latest_booking_reference` | `$json.body.booking_reference` |
| `latest_booking_status` | `$json.body.booking_status` |
| `latest_service` | `$json.body.service.name` |
| `last_event_id` | `$json.body.event_id` |
| `last_update` | `$json.body.occurred_at` |

If `booking_count` or another customer aggregate is not present in the live event payload, leave that column unchanged or calculate it in n8n from the existing row. Do not use `booking_reference` as the customer key.

## Controlled verification

1. Save and publish the workflow.
2. Generate one controlled schedule or reschedule event for an existing customer.
3. Confirm one Customer Directory row is updated, not duplicated.
4. Confirm Daily Schedule, Client Summary, and Service History still update.
5. Confirm the final response remains `automation_status: processed`.
6. Confirm the application Automation page changes the outbox event to `recorded`.
