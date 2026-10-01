# Scheduling Research and Two-Team MVP Defaults

## Purpose

Define a realistic but bounded dispatch model before implementing team calendars or appointment assignment.

## Research findings

- HVAC dispatch is more than filling a calendar. Real operators consider job skill, geography, travel/buffer time, customer arrival windows, current workload, and urgent calls.
- A practical dispatch board shows each deployable resource, its booked work, open time, and an unassigned queue. Customers are normally promised an arrival window; dispatch chooses the actual team and working time.
- Back-to-back bookings without travel and job-overrun buffers make schedules fail. A reserved same-day/afternoon capacity rule is common for urgent work.
- Mature field-service systems support people, teams, skills, availability, exact appointments, and fast reassignment. This prototype will implement only the smallest useful manual subset first.

Sources reviewed on 2026-09-30:

- Microsoft Dynamics 365 Field Service capability overview: https://info.microsoft.com/rs/157-GQE-382/images/microsoft-dynamics-365-for-field-service-product-capabilities-factsheet-en-gb.pdf
- TeamServ, *HVAC Dispatch Scheduling Guide*: https://www.teamserv.org/seo/hvac-dispatch-scheduling-guide
- The Growth Room, *HVAC Dispatch & Scheduling: A Practical Playbook*: https://hvacgrowthroom.com/guides/hvac-dispatch-scheduling-guide-2026

## Recommended MVP operating model

This is an informed prototype default, not a claim about the real Balik-Lamig operation.

| Item | MVP default |
| --- | --- |
| Deployable teams | 2: Team A and Team B |
| Initial staffing representation | One fictional lead technician per team: Alex Reyes and Jamie Santos |
| Operating days | Monday-Saturday |
| Dispatch board day | 09:00-17:00 |
| Planned service blocks per team | 09:00-11:00, 11:30-13:30, 14:00-16:00 |
| Standard planned capacity | 3 jobs per team/day; 6 across both teams |
| Protected capacity | 16:00-17:00 is not pre-booked; dispatcher may use it only for a short urgent/overflow decision in a later increment |
| Customer promise | Preferred date only in the current form; a separate staff decision selects a specific appointment block |
| Assignment rule | An approved request can be assigned only to one active team and one free block; overlapping appointments for the same team are rejected |

The two-hour blocks include the current 90-minute cleaning reference duration plus a modest buffer for access, wrap-up, and local movement. Longer or diagnostic work will need different duration rules in a later improvement.

## Required data-model increment before scheduling UI

1. Add `service_teams` for Team A / Team B.
2. Add `team_memberships` so a team can later have multiple technicians.
3. Associate an appointment with one `service_team` and an exact start/end time.
4. Validate that the team is active and has no overlapping appointment.
5. Keep the current individual technician records as fictional team leads; do not add real staff data.

## Explicitly deferred

- Maps, route optimization, real-time GPS, live travel estimates
- Customer SMS/email confirmations and arrival alerts
- Google Calendar, Meta, payments, and public access
- Actual staff rosters, customer records, or production availability
- Automatic optimization or AI dispatch
