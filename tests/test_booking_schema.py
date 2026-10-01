from app.database.base import Base
from app.database import models  # noqa: F401 - register all tables


def test_initial_schema_contains_all_booking_workflow_tables() -> None:
    assert set(Base.metadata.tables) == {
        "customers",
        "addresses",
        "service_types",
        "booking_requests",
        "booking_request_status_history",
        "technicians",
        "service_teams",
        "team_memberships",
        "appointments",
        "appointment_status_history",
        "notification_outbox",
    }


def test_booking_request_requires_a_positive_unit_count_and_review_status() -> None:
    constraints = {constraint.name: str(constraint.sqltext) for constraint in Base.metadata.tables["booking_requests"].constraints if constraint.name}

    assert constraints["ck_booking_requests_positive_unit_count"] == "unit_count > 0"
    assert "pending_review" in constraints["ck_booking_requests_status"]
    assert "approved_for_scheduling" in constraints["ck_booking_requests_status"]
    assert "scheduled" in constraints["ck_booking_requests_status"]


def test_notification_outbox_is_simulation_only() -> None:
    constraints = {constraint.name: str(constraint.sqltext) for constraint in Base.metadata.tables["notification_outbox"].constraints if constraint.name}

    assert constraints["ck_notification_outbox_simulated_channel"] == "channel = 'simulated'"
