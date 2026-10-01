from app.database.seed import SERVICE_TYPES, TEAM_ASSIGNMENTS, TECHNICIAN_NAMES


def test_seed_service_types_are_fictional_reference_options() -> None:
    assert SERVICE_TYPES == (
        ("Aircon Cleaning", 90),
        ("Deep Cleaning", 150),
        ("Inspection and Diagnosis", 60),
    )


def test_seed_technicians_are_explicitly_fictional() -> None:
    assert len(TECHNICIAN_NAMES) == 2
    assert all("(fictional)" in name for name in TECHNICIAN_NAMES)


def test_seed_teams_have_one_fictional_lead_each() -> None:
    assert TEAM_ASSIGNMENTS == (
        ("Team A", "Alex Reyes (fictional)"),
        ("Team B", "Jamie Santos (fictional)"),
    )
