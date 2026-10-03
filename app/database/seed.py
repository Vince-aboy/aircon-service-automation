"""Idempotent seed command for service-reference data."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Appointment, ServiceTeam, ServiceType, TeamMembership, Technician
from app.database.session import create_database_engine


SERVICE_TYPES: tuple[tuple[str, int], ...] = (
    ("Aircon Cleaning", 90),
    ("Deep Cleaning", 150),
    ("Inspection and Diagnosis", 60),
)

TECHNICIAN_NAMES: tuple[str, ...] = (
    "Pedro Ecleo",
    "Brian Elipides",
    "John Harris",
    "Jestony Rollon",
    "Snowdon",
    "Mavien",
    "Richard",
    "Jommel",
    "Marlon",
    "Aweng",
    "Robert",
    "Ken",
    "Mark",
    "Joeking",
    "Dexter",
    "Clifford",
)

TEAM_ASSIGNMENTS: tuple[tuple[str, str], ...] = (
    ("Team A", "Pedro Ecleo"),
    ("Team B", "Brian Elipides"),
)


def seed_reference_data(session: Session) -> tuple[int, int, int, int]:
    """Add missing service, technician, and team reference records."""
    added_services = 0
    added_technicians = 0
    added_teams = 0
    added_memberships = 0

    for name, duration_minutes in SERVICE_TYPES:
        existing = session.scalar(select(ServiceType).where(ServiceType.name == name))
        if existing is None:
            session.add(ServiceType(name=name, duration_minutes=duration_minutes, active=True))
            added_services += 1

    for display_name in TECHNICIAN_NAMES:
        existing = session.scalar(select(Technician).where(Technician.display_name == display_name))
        if existing is None:
            session.add(Technician(display_name=display_name, active=True))
            added_technicians += 1

    session.flush()
    for team_name, technician_name in TEAM_ASSIGNMENTS:
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == team_name))
        if team is None:
            team = ServiceTeam(name=team_name, active=True)
            session.add(team)
            session.flush()
            added_teams += 1

        technician = session.scalar(select(Technician).where(Technician.display_name == technician_name))
        membership = session.scalar(
            select(TeamMembership).where(
                TeamMembership.service_team_id == team.id,
                TeamMembership.technician_id == technician.id,
            )
        )
        if membership is None:
            session.add(TeamMembership(service_team_id=team.id, technician_id=technician.id, is_lead=True))
            added_memberships += 1

    # Retire the original demo technicians without breaking existing appointments.
    # Existing jobs are transferred to the real lead for their current team first.
    real_leads = {
        team_name: session.scalar(
            select(Technician).where(Technician.display_name == technician_name)
        )
        for team_name, technician_name in TEAM_ASSIGNMENTS
    }
    legacy_names = ("Alex Reyes (fictional)", "Jamie Santos (fictional)")
    for legacy_name in legacy_names:
        legacy = session.scalar(select(Technician).where(Technician.display_name == legacy_name))
        if legacy is None:
            continue
        appointments = list(session.scalars(select(Appointment).where(Appointment.technician_id == legacy.id)).all())
        for appointment in appointments:
            team = session.get(ServiceTeam, appointment.service_team_id)
            replacement = real_leads.get(team.name if team else "")
            if replacement is not None:
                appointment.technician_id = replacement.id
        session.query(TeamMembership).filter(TeamMembership.technician_id == legacy.id).delete(synchronize_session=False)
        legacy.active = False

    session.commit()
    return added_services, added_technicians, added_teams, added_memberships


def main() -> None:
    engine = create_database_engine()
    with Session(engine) as session:
        added_services, added_technicians, added_teams, added_memberships = seed_reference_data(session)
    print(
        "Seed complete: "
        f"{added_services} service type(s), {added_technicians} technician(s), "
        f"{added_teams} team(s), and {added_memberships} team membership(s) added."
    )


if __name__ == "__main__":
    main()
