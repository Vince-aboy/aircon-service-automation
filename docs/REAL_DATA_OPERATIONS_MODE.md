# Real-data operations mode

## Boundary

Live owner operations are enabled only when `AIRCON_OPERATION_MODE=live` is set in the protected VPS environment file. The default remains `local_prototype`.

## Required VPS settings

```text
AIRCON_OPERATION_MODE=live
AIRCON_STAFF_USERNAME=<owner username>
AIRCON_STAFF_PASSWORD=<long random password>
```

The staff username and password must never be committed to Git or sent through chat. When live mode is enabled, all `/staff/*` routes require HTTP Basic Auth. If credentials are missing, staff routes fail closed with HTTP 401 rather than becoming public.

## Data handling

- PostgreSQL remains the source of truth.
- The owner-reporting event includes the full phone only in live mode; public pages never display it.
- The Google Sheet must be restricted to the owner/staff account and must not use “Anyone with the link”.
- Address reporting combines address line, barangay, city, and coverage area.
- Internal event timestamps remain ISO 8601 and include a Manila-readable display value.
- Customer messaging and payments remain disabled.
- n8n must be updated to accept `operation_mode=live_owner_reporting` and must not reject the event solely because `synthetic_only` is false.

## Activation checklist

1. Restrict Google Sheet sharing to approved owner/staff accounts.
2. Set the live-mode environment variables on the VPS.
3. Restart the app and verify `/staff/*` prompts for authentication.
4. Update n8n mappings: `client.phone`, `location.display`, and `occurred_at_display`.
5. Send one controlled test request and verify the owner sheet.
6. Keep customer messaging and payment nodes disabled until separately approved.
