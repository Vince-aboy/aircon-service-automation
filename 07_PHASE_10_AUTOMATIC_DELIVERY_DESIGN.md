# Phase 10 — Automatic Delivery Design

## Scope

Phase 10 defines the future automatic delivery path from the local appointment workflow to the protected n8n webhook. The design remains disabled and synthetic-only until security review and explicit publishing approval.

## Current safe boundary

- Appointment scheduling and status changes already create one local `NotificationOutbox` row per transition.
- The local database remains the source of truth.
- The manual `Send one synthetic event to n8n` action is test-only.
- n8n remains unpublished and no customer message is delivered.

## Proposed automatic flow

1. A staff status change commits the appointment history and one pending outbox event in the same database transaction.
2. A future delivery worker selects the oldest eligible pending event and claims it before sending.
3. The worker sends only synthetic, HTTPS, Header-Auth-protected payloads to n8n.
4. A processed response records the event and any dispatcher notice locally.
5. A temporary delivery failure leaves the event retryable with an attempt count and next-attempt time.
6. A permanent rejection records the rejection reason and stops automatic retries.

## Required safeguards before enabling

- Explicit feature flag defaulting to disabled.
- Outbox claim/in-flight state so two workers cannot send the same event concurrently.
- Attempt count, last error, and next-attempt timestamp.
- Stable idempotency key derived from the local outbox event ID.
- n8n validation of synthetic-only payloads and idempotency key.
- Retry limits and operator-visible failure status.
- Read-only VPS/security review.
- Explicit approval before publishing n8n or enabling automatic delivery.

## Phase 10 acceptance criteria

- No automatic external send occurs while the feature flag is disabled.
- Every appointment transition still creates exactly one local event.
- A worker cannot claim the same event twice concurrently.
- Retryable failures remain visible and retryable.
- Successful delivery is recorded once, with no duplicate dispatcher notice.
- All verification uses synthetic data only.

## Implementation status

- Added `attempt_count`, `last_error`, `next_attempt_at`, and `claimed_at` to the local outbox model.
- Added migration `20261001_0007_add_outbox_delivery_state.py` with a delivery-queue index.
- Applied migration `20261001_0007` successfully to the local development database on 2026-10-01.
- Added a local-only event-claim helper with a five-minute lease and stable idempotency-key helper.
- Verified one claim at a time and stale-claim recovery in automated tests.
- Manual n8n sends now claim one eligible event before delivery and persist the result: success clears retry state, temporary failure preserves `pending` with a saved error, and explicit rejection marks `failed`.
- The outbox displays delivery-attempt and last-error details for new delivery attempts.
- Added `AIRCON_AUTOMATIC_DELIVERY_ENABLED`, which defaults to disabled and is shown in the outbox. No background worker is installed or started.
- Temporary failures now receive a bounded future retry time (1, 2, 4 … up to 30 minutes). Manual staff retry remains available for controlled testing.
- Added a visible `Check due delivery worker` action. It counts due pending events but cannot claim, modify, or send them while automatic delivery is disabled.
- Live evidence: the worker check reported `0 due event(s) found` while automatic delivery was disabled and made no delivery.
- Live evidence: event `AC-20261001-22C2A472` failed with HTTP 404 on attempt 1, remained pending with the saved error, then was retried against the n8n test listener and recorded on attempt 2. No customer message was delivered.
- Automatic delivery remains disabled.
