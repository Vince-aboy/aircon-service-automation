# SQL Live Synchronization Record

## Applied — 2026-10-03

The VPS PostgreSQL database was synchronized using the repository’s idempotent seed command:

```bash
sudo bash -c 'set -a; . /etc/balik-lamig/balik-lamig.env; set +a; cd /home/aboy/apps/balik-lamig; .venv/bin/python -m app.database.seed'
```

The command completed successfully with:

```text
Seed complete: 0 service type(s), 0 technician(s), 0 team(s), and 0 team membership(s) added.
```

This confirms the 16-person roster and Team A/Team B records already existed. The seed also performed legacy cleanup:

- Existing appointments assigned to `Alex Reyes (fictional)` or `Jamie Santos (fictional)` were transferred to the real lead for their current team.
- The fictional technicians were marked inactive.
- Their team memberships were removed.
- No appointments, customers, booking requests, status history, or outbox events were deleted.

## Current roster

Pedro Ecleo, Brian Elipides, John Harris, Jestony Rollon, Snowdon, Mavien, Richard, Jommel, Marlon, Aweng, Robert, Ken, Mark, Joeking, Dexter, and Clifford.

## Source of truth

PostgreSQL is authoritative. The Google Sheet is an owner-reporting view synchronized from SQL events; it is not used to edit the booking database.
