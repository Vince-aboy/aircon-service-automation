from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models import Appointment, AppointmentStatusHistory, BookingRequest, BookingRequestStatusHistory, Customer, NotificationOutbox, ServiceTeam, ServiceType, TeamMembership, Technician
from app.booking.service import (
    automatic_delivery_enabled,
    claim_next_eligible_outbox_event,
    due_outbox_event_count,
    next_retry_time,
    outbox_idempotency_key,
    record_delivery_success,
    record_permanent_delivery_rejection,
    record_retryable_delivery_failure,
    run_due_delivery_worker_check,
)
from app.main import app, get_session, staff_auth_enabled


def create_test_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(ServiceType(name="Aircon Cleaning", duration_minutes=90, active=True))
    session.add_all((
        Technician(display_name="Team A Lead (fictional)", active=True),
        Technician(display_name="Team B Lead (fictional)", active=True),
    ))
    session.commit()
    team_a_lead = session.scalar(select(Technician).where(Technician.display_name == "Team A Lead (fictional)"))
    team_b_lead = session.scalar(select(Technician).where(Technician.display_name == "Team B Lead (fictional)"))
    session.add_all((ServiceTeam(name="Team A", active=True), ServiceTeam(name="Team B", active=True)))
    session.commit()
    team_a = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
    team_b = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team B"))
    session.add_all((
        TeamMembership(service_team_id=team_a.id, technician_id=team_a_lead.id, is_lead=True),
        TeamMembership(service_team_id=team_b.id, technician_id=team_b_lead.id, is_lead=True),
    ))
    session.commit()

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app), session


def valid_form_data() -> dict[str, str]:
    return {
        "full_name": "Synthetic Form Customer",
        "mobile": "09171234567",
        "email": "synthetic.form@example.test",
        "address_line": "123 Fictional Street",
        "barangay": "Sample Barangay",
        "city": "Manila",
        "coverage_area": "Urban Deca Homes, Tondo",
        "service_type_id": "1",
        "preferred_date": str(date.today() + timedelta(days=1)),
        "aircon_type": "Window Type",
    }


def test_staff_authentication_switch_defaults_secure(monkeypatch) -> None:
    monkeypatch.delenv("AIRCON_STAFF_AUTH_ENABLED", raising=False)
    assert staff_auth_enabled() is True
    monkeypatch.setenv("AIRCON_STAFF_AUTH_ENABLED", "false")
    assert staff_auth_enabled() is False


def test_staff_dashboard_uses_shared_owner_operations_navigation() -> None:
    client, session = create_test_client()
    try:
        response = client.get("/staff")

        assert response.status_code == 200
        assert "Operations command center" in response.text
        assert "Service requests" in response.text
        assert "Team schedule" in response.text
        assert "Automation health" in response.text
        assert "Available teams" in response.text
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_admin_directories_render_and_customer_search_finds_booking() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        customer = session.scalar(select(Customer))

        appointments = client.get("/staff/appointments")
        customers = client.get("/staff/customers?q=Synthetic")
        customer_details = client.get(f"/staff/customers/{customer.id}")
        teams = client.get("/staff/teams")
        activity = client.get("/staff/activity")
        settings = client.get("/staff/settings")

        assert appointments.status_code == 200
        assert "Search and manage every scheduled job" in appointments.text
        assert customers.status_code == 200
        assert "Synthetic Form Customer" in customers.text
        assert customer_details.status_code == 200
        assert "Service history" in customer_details.text
        assert teams.status_code == 200
        assert "Maintain the people and team leads" in teams.text
        assert activity.status_code == 200
        assert "Activity history" in activity.text
        assert settings.status_code == 200
        assert "Read-only operational configuration" in settings.text
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_create_team_and_assign_a_lead() -> None:
    client, session = create_test_client()
    try:
        technician_response = client.post(
            "/staff/technicians",
            data={"display_name": "New Technician"},
            follow_redirects=False,
        )
        team_response = client.post(
            "/staff/teams",
            data={"name": "Team C"},
            follow_redirects=False,
        )
        technician = session.scalar(select(Technician).where(Technician.display_name == "New Technician"))
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team C"))
        member_response = client.post(
            f"/staff/teams/{team.id}/members",
            data={"technician_id": technician.id, "is_lead": "true"},
            follow_redirects=False,
        )
        membership = session.scalar(
            select(TeamMembership).where(
                TeamMembership.service_team_id == team.id,
                TeamMembership.technician_id == technician.id,
            )
        )

        assert technician_response.status_code == 303
        assert team_response.status_code == 303
        assert member_response.status_code == 303
        assert membership is not None
        assert membership.is_lead is True
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_booking_page_lists_active_services() -> None:
    client, session = create_test_client()
    try:
        response = client.get("/book")

        assert response.status_code == 200
        assert "Request a Balik-Lamig service" in response.text
        assert "Choose a service and your preferred schedule" in response.text
        assert "Full Address / Decca Address" in response.text
        assert '<label>Email <span class="optional">(optional)</span>' in response.text
        assert '<input name="barangay" type="hidden" value="Urban Deca Homes">' in response.text
        assert '<input name="city" type="hidden" value="Manila">' in response.text
        assert '<input name="coverage_area" type="hidden" value="Urban Deca Homes, Tondo">' in response.text
        assert "Current prototype coverage" not in response.text
        assert "balik-lamig.png" in response.text
        assert "Aircon Cleaning" in response.text
        assert "Window Type" in response.text
        assert 'name="unit_count"' not in response.text
        assert 'name="preferred_window"' not in response.text
        assert 'name="notes"' not in response.text
        assert "synthetic data only" in response.text
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_phase_roadmap_displays_completed_phases() -> None:
    client, session = create_test_client()
    try:
        response = client.get("/staff/documentation/phases")

        assert response.status_code == 200
        assert "Completed phases 0&ndash;9" in response.text
        assert "Phase 0" in response.text
        assert "Phase 9" in response.text
        assert "n8n test workflow" in response.text
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_valid_form_submission_shows_pending_review_receipt() -> None:
    client, session = create_test_client()
    try:
        response = client.post("/book", data=valid_form_data())

        assert response.status_code == 201
        assert "Service request received" in response.text
        assert "pending_review" in response.text
        assert session.scalar(select(func.count()).select_from(Customer)) == 1
        assert session.scalar(select(func.count()).select_from(BookingRequest)) == 1
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_invalid_form_submission_re_renders_with_an_error() -> None:
    client, session = create_test_client()
    try:
        form_data = valid_form_data()
        form_data["city"] = "Quezon City"
        response = client.post("/book", data=form_data)

        assert response.status_code == 422
        assert '<form method="post" action="/book"' in response.text
        assert session.scalar(select(func.count()).select_from(Customer)) == 0
        assert session.scalar(select(func.count()).select_from(BookingRequest)) == 0
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_queue_lists_pending_requests_without_modifying_them() -> None:
    client, session = create_test_client()
    try:
        submit_response = client.post("/book", data=valid_form_data())
        queue_response = client.get("/staff/requests")

        assert submit_response.status_code == 201
        assert queue_response.status_code == 200
        assert "Pending service requests" in queue_response.text
        assert "Synthetic Form Customer" in queue_response.text
        assert "Aircon Cleaning" in queue_response.text
        assert "Window Type" in queue_response.text
        assert "pending_review" in queue_response.text
        assert session.scalar(select(func.count()).select_from(BookingRequest)) == 1
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_approve_a_pending_request_without_creating_an_appointment() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        response = client.post(
            f"/staff/requests/{booking.id}/review",
            data={"decision": "approve"},
            follow_redirects=False,
        )

        session.refresh(booking)
        history = session.scalar(select(BookingRequestStatusHistory))
        assert response.status_code == 303
        assert response.headers["location"] == "/staff/requests?reviewed=approved_for_scheduling"
        assert booking.status == "approved_for_scheduling"
        assert history.from_status == "pending_review"
        assert history.to_status == "approved_for_scheduling"
        assert history.actor_type == "local_staff"
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_decline_a_pending_request_with_an_audit_record() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        response = client.post(
            f"/staff/requests/{booking.id}/review",
            data={"decision": "decline"},
            follow_redirects=False,
        )

        session.refresh(booking)
        history = session.scalar(select(BookingRequestStatusHistory))
        assert response.status_code == 303
        assert booking.status == "cancelled"
        assert history.from_status == "pending_review"
        assert history.to_status == "cancelled"
        assert "no appointment created" in history.note
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_dispatch_board_schedules_an_approved_request_once() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))

        response = client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
            follow_redirects=False,
        )

        session.refresh(booking)
        appointment = session.scalar(select(Appointment))
        assert response.status_code == 303
        assert booking.status == "scheduled"
        assert appointment.service_team_id == team.id
        assert appointment.scheduled_start.hour == 9
        assert appointment.scheduled_end.hour == 11
        assert session.scalar(select(func.count()).select_from(BookingRequestStatusHistory)) == 2
        assert session.scalar(select(func.count()).select_from(AppointmentStatusHistory)) == 1
        outbox_event = session.scalar(select(NotificationOutbox))
        assert outbox_event.event_type == "appointment_scheduled"
        assert outbox_event.status == "pending"
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_dispatch_board_rejects_a_team_block_that_is_already_assigned() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        first_booking = session.scalar(select(BookingRequest))
        second_form = valid_form_data()
        second_form.update({"full_name": "Second Synthetic Customer", "mobile": "09181234567"})
        client.post("/book", data=second_form)
        second_booking = session.scalar(
            select(BookingRequest).join(Customer).where(Customer.mobile == "09181234567")
        )
        client.post(f"/staff/requests/{first_booking.id}/review", data={"decision": "approve"})
        client.post(f"/staff/requests/{second_booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        form = {
            "booking_request_id": first_booking.id,
            "service_team_id": team.id,
            "appointment_date": str(date.today() + timedelta(days=1)),
            "slot_key": "09:00",
        }
        client.post("/staff/dispatch/assign", data=form)
        form["booking_request_id"] = second_booking.id
        response = client.post("/staff/dispatch/assign", data=form)

        assert response.status_code == 422
        assert "that team time block is already assigned" in response.text
        assert session.scalar(select(func.count()).select_from(Appointment)) == 1
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_scheduled_card_opens_read_only_appointment_details() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        appointment = session.scalar(select(Appointment))
        response = client.get(f"/staff/appointments/{appointment.id}")
        fragment_response = client.get(f"/staff/appointments/{appointment.id}/fragment")

        assert response.status_code == 200
        assert fragment_response.status_code == 200
        assert "Scheduled Job Details" in response.text
        assert "Synthetic Form Customer" in response.text
        assert "123 Fictional Street" in response.text
        assert "Team A" in response.text
        assert "09:00-11:00" in response.text
        assert "approved_for_scheduling" in response.text
        assert "scheduled" in response.text
        assert "Mark en route" in response.text
        assert "<html" not in fragment_response.text
        assert "123 Fictional Street" in fragment_response.text
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_progress_a_scheduled_job_with_an_audit_record() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        appointment = session.scalar(select(Appointment))

        response = client.post(
            f"/staff/appointments/{appointment.id}/status",
            data={"next_status": "en_route"},
            follow_redirects=False,
        )
        session.refresh(appointment)
        history = list(session.scalars(select(AppointmentStatusHistory).order_by(AppointmentStatusHistory.id)).all())

        assert response.status_code == 303
        assert "job_updated=en_route" in response.headers["location"]
        assert appointment.status == "en_route"
        assert [(entry.from_status, entry.to_status) for entry in history] == [
            (None, "confirmed"),
            ("confirmed", "en_route"),
        ]

        invalid_response = client.post(
            f"/staff/appointments/{appointment.id}/status",
            data={"next_status": "completed"},
        )
        assert invalid_response.status_code == 422
        assert "cannot move from en_route to completed" in invalid_response.text
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_move_confirmed_job_to_another_team_and_add_internal_note() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team_a = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        team_b = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team B"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team_a.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        appointment = session.scalar(select(Appointment))

        response = client.post(
            f"/staff/appointments/{appointment.id}/reschedule",
            data={
                "service_team_id": team_b.id,
                "appointment_date": str(date.today() + timedelta(days=2)),
                "slot_key": "11:30",
            },
            follow_redirects=False,
        )
        note_response = client.post(
            f"/staff/appointments/{appointment.id}/notes",
            data={"note": "Bring the long ladder."},
            follow_redirects=False,
        )
        session.refresh(appointment)
        history = list(session.scalars(select(AppointmentStatusHistory).order_by(AppointmentStatusHistory.id)).all())

        assert response.status_code == 303
        assert note_response.status_code == 303
        assert appointment.service_team_id == team_b.id
        assert appointment.scheduled_start.hour == 11
        assert "Team A" in history[-2].note and "Team B" in history[-2].note
        assert history[-1].note == "Internal note: Bring the long ladder."
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_cancelling_an_appointment_requires_a_reason() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        appointment = session.scalar(select(Appointment))

        missing_reason = client.post(
            f"/staff/appointments/{appointment.id}/status",
            data={"next_status": "cancelled", "staff_note": ""},
        )
        cancelled = client.post(
            f"/staff/appointments/{appointment.id}/status",
            data={"next_status": "cancelled", "staff_note": "Customer requested another provider."},
            follow_redirects=False,
        )
        session.refresh(appointment)
        final_history = session.scalar(
            select(AppointmentStatusHistory).order_by(AppointmentStatusHistory.id.desc())
        )
        dispatch_board = client.get(f"/staff/dispatch?selected_date={appointment.scheduled_start.date()}")

        assert missing_reason.status_code == 422
        assert cancelled.status_code == 303
        assert appointment.status == "cancelled"
        assert "Customer requested another provider" in final_history.note
        assert booking.reference_code not in dispatch_board.text

        replacement_form = valid_form_data()
        replacement_form.update({"full_name": "Replacement Synthetic Customer", "mobile": "09189998888"})
        client.post("/book", data=replacement_form)
        replacement = session.scalar(
            select(BookingRequest).order_by(BookingRequest.id.desc())
        )
        client.post(f"/staff/requests/{replacement.id}/review", data={"decision": "approve"})
        replacement_response = client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": replacement.id,
                "service_team_id": appointment.service_team_id,
                "appointment_date": str(appointment.scheduled_start.date()),
                "slot_key": "09:00",
            },
            follow_redirects=False,
        )
        assert replacement_response.status_code == 303
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_complete_confirmed_job_with_shortcut_and_full_history() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        appointment = session.scalar(select(Appointment))

        response = client.post(
            f"/staff/appointments/{appointment.id}/status",
            data={"next_status": "completed_now"},
            follow_redirects=False,
        )
        session.refresh(appointment)
        history = list(session.scalars(select(AppointmentStatusHistory).order_by(AppointmentStatusHistory.id)).all())
        events = list(session.scalars(select(NotificationOutbox).order_by(NotificationOutbox.id)).all())

        assert response.status_code == 303
        assert "job_updated=completed" in response.headers["location"]
        assert appointment.status == "completed"
        assert [(entry.from_status, entry.to_status) for entry in history] == [
            (None, "confirmed"),
            ("confirmed", "en_route"),
            ("en_route", "in_progress"),
            ("in_progress", "completed"),
        ]
        assert [event.event_type for event in events] == [
            "appointment_scheduled",
            "appointment_en_route",
            "appointment_in_progress",
            "appointment_completed",
        ]
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_local_automation_simulation_records_pending_events_without_delivery() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )

        page_response = client.get("/staff/automation")
        process_response = client.post("/staff/automation/process", follow_redirects=False)
        event = session.scalar(select(NotificationOutbox))

        assert page_response.status_code == 200
        assert "Automation outbox" in page_response.text
        assert "appointment scheduled" in page_response.text
        assert process_response.status_code == 303
        assert process_response.headers["location"] == "/staff/automation?processed=1"
        assert event.status == "recorded"
        assert event.channel == "simulated"
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_n8n_push_is_disabled_without_runtime_configuration(monkeypatch) -> None:
    client, session = create_test_client()
    try:
        monkeypatch.delenv("AIRCON_N8N_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("AIRCON_N8N_WEBHOOK_KEY", raising=False)
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )

        response = client.post("/staff/automation/push", follow_redirects=False)
        event = session.scalar(select(NotificationOutbox))

        assert response.status_code == 303
        assert response.headers["location"] == "/staff/automation?push_error=1"
        page = client.get(response.headers["location"])
        assert page.status_code == 200
        assert "Delivery failed. The event remains pending and can be retried." in page.text
        assert event.status == "pending"
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_delivery_worker_claims_one_eligible_event_without_sending() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        event = session.scalar(select(NotificationOutbox))
        claim_time = datetime(2026, 10, 1, tzinfo=UTC)

        claimed = claim_next_eligible_outbox_event(session, now=claim_time)
        second_claim = claim_next_eligible_outbox_event(session, now=claim_time)

        assert claimed is event
        assert claimed.claimed_at == claim_time
        assert claimed.attempt_count == 1
        assert second_claim is None
        assert event.status == "pending"
        assert outbox_idempotency_key(event) == f"synthetic-outbox-{event.id}"

        event.claimed_at = claim_time - timedelta(minutes=6)
        reclaimed = claim_next_eligible_outbox_event(session, now=claim_time)

        assert reclaimed is event
        assert reclaimed.attempt_count == 2
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_delivery_result_handlers_preserve_retry_and_rejection_state() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        event = session.scalar(select(NotificationOutbox))
        claim_time = datetime(2026, 10, 1, tzinfo=UTC)
        claim_next_eligible_outbox_event(session, now=claim_time)

        record_retryable_delivery_failure(event, "n8n rejected the event with HTTP 404")
        session.flush()

        assert event.status == "pending"
        assert event.claimed_at is None
        assert event.last_error == "n8n rejected the event with HTTP 404"

        record_delivery_success(event, {"automation_status": "processed", "dispatcher_message": "Prepared locally."})
        session.flush()

        assert event.status == "recorded"
        assert event.last_error is None
        assert event.payload["dispatcher_message"] == "Prepared locally."

        record_permanent_delivery_rejection(event, "synthetic-only validation failed")
        session.flush()

        assert event.status == "failed"
        assert event.last_error == "synthetic-only validation failed"
        assert event.payload["n8n_rejection_reason"] == "synthetic-only validation failed"
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_staff_can_requeue_a_failed_owner_reporting_event() -> None:
    client, session = create_test_client()
    try:
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        event = session.scalar(select(NotificationOutbox))
        event.status = "failed"
        event.last_error = "Synthetic delivery failure"
        session.commit()

        response = client.post(f"/staff/automation/events/{event.id}/requeue", follow_redirects=False)
        session.refresh(event)

        assert response.status_code == 303
        assert event.status == "pending"
        assert event.last_error is None
        assert event.next_attempt_at is None
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_automatic_delivery_defaults_off_and_respects_retry_schedule(monkeypatch) -> None:
    client, session = create_test_client()
    try:
        monkeypatch.delenv("AIRCON_AUTOMATIC_DELIVERY_ENABLED", raising=False)
        assert automatic_delivery_enabled() is False
        assert "Automatic delivery is disabled" in client.get("/staff/automation").text

        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        event = session.scalar(select(NotificationOutbox))
        claim_time = datetime(2026, 10, 1, tzinfo=UTC)
        event.next_attempt_at = next_retry_time(attempt_count=1, now=claim_time)

        assert claim_next_eligible_outbox_event(session, now=claim_time) is None
        assert claim_next_eligible_outbox_event(session, now=claim_time, ignore_retry_schedule=True) is event
        assert next_retry_time(attempt_count=99, now=claim_time) == claim_time + timedelta(minutes=30)
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_due_delivery_worker_check_is_no_send_while_disabled(monkeypatch) -> None:
    client, session = create_test_client()
    try:
        monkeypatch.delenv("AIRCON_AUTOMATIC_DELIVERY_ENABLED", raising=False)
        client.post("/book", data=valid_form_data())
        booking = session.scalar(select(BookingRequest))
        client.post(f"/staff/requests/{booking.id}/review", data={"decision": "approve"})
        team = session.scalar(select(ServiceTeam).where(ServiceTeam.name == "Team A"))
        client.post(
            "/staff/dispatch/assign",
            data={
                "booking_request_id": booking.id,
                "service_team_id": team.id,
                "appointment_date": str(date.today() + timedelta(days=1)),
                "slot_key": "09:00",
            },
        )
        event = session.scalar(select(NotificationOutbox))

        worker_state, due_events = run_due_delivery_worker_check(session)
        response = client.post("/staff/automation/worker-check", follow_redirects=False)

        assert worker_state == "disabled"
        assert due_events == 1
        assert due_outbox_event_count(session) == 1
        assert event.status == "pending"
        assert event.attempt_count == 0
        assert response.headers["location"] == "/staff/automation?worker=disabled&due=1"
    finally:
        session.close()
        app.dependency_overrides.clear()
