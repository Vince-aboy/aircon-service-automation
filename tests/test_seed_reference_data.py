from app.database.seed import SERVICE_TYPES, TEAM_ASSIGNMENTS, TECHNICIAN_NAMES


def test_seed_service_types_are_fictional_reference_options() -> None:
    assert SERVICE_TYPES == (
        ("Aircon Cleaning", 90),
        ("Deep Cleaning", 150),
        ("Inspection and Diagnosis", 60),
    )


def test_seed_technicians_match_the_owner_employee_roster() -> None:
    assert len(TECHNICIAN_NAMES) == 16
    assert TECHNICIAN_NAMES[:3] == ("Pedro Ecleo", "Brian Elipides", "John Harris")


def test_seed_teams_have_one_roster_lead_each() -> None:
    assert TEAM_ASSIGNMENTS == (
        ("Team A", "Pedro Ecleo"),
        ("Team B", "Brian Elipides"),
    )
