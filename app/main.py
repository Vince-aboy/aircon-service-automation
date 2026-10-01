"""Local FastAPI application for controlled booking requests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from datetime import date, datetime, time, timedelta
import os
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.booking.service import APPOINTMENT_STATUS_TRANSITIONS, DISPATCH_SLOTS, MANILA_TIMEZONE, automatic_delivery_enabled, complete_appointment_shortcut, create_pending_booking, process_pending_simulated_events, push_one_pending_event_to_n8n, review_booking_request, run_due_delivery_worker_check, schedule_approved_booking, update_appointment_status
from app.booking.validation import BookingRequestInput
from app.database.models import Address, Appointment, AppointmentStatusHistory, BookingRequest, BookingRequestStatusHistory, Customer, NotificationOutbox, ServiceTeam, ServiceType
from app.database.session import create_database_engine


app = FastAPI(
    title="Aircon Service Automation",
    version="0.1.0",
    description="Local portfolio prototype. It does not send real notifications or accept real customer data.",
)
APP_DIRECTORY = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIRECTORY / "templates"))
app.mount("/static", StaticFiles(directory=str(APP_DIRECTORY / "static")), name="static")
PUBLIC_BASE_PATH = os.getenv("AIRCON_PUBLIC_BASE_PATH", "").strip().rstrip("/")


def app_path(path: str) -> str:
    """Prefix browser-facing paths when deployed below a reverse-proxy route."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{PUBLIC_BASE_PATH}{normalized_path}"


templates.env.globals["app_path"] = app_path


class BookingReceipt(BaseModel):
    reference_code: str
    status: str
    message: str


def get_session() -> Generator[Session, None, None]:
    """Open a per-request database session using terminal/runtime-only credentials."""
    engine = create_database_engine()
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def active_service_types(session: Session) -> list[ServiceType]:
    return list(
        session.scalars(
            select(ServiceType).where(ServiceType.active.is_(True)).order_by(ServiceType.name)
        ).all()
    )


def pending_staff_requests(session: Session) -> list[tuple[BookingRequest, Customer, Address, ServiceType]]:
    """Return pending requests for the local staff-review queue only."""
    return list(
        session.execute(
            select(BookingRequest, Customer, Address, ServiceType)
            .join(Customer, BookingRequest.customer_id == Customer.id)
            .join(Address, BookingRequest.address_id == Address.id)
            .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
            .where(BookingRequest.status == "pending_review")
            .order_by(BookingRequest.created_at.asc(), BookingRequest.id.asc())
        ).all()
    )


def active_service_teams(session: Session) -> list[ServiceTeam]:
    return list(session.scalars(select(ServiceTeam).where(ServiceTeam.active.is_(True)).order_by(ServiceTeam.name)).all())


def approved_unscheduled_requests(session: Session) -> list[tuple[BookingRequest, Customer, Address, ServiceType]]:
    return list(
        session.execute(
            select(BookingRequest, Customer, Address, ServiceType)
            .join(Customer, BookingRequest.customer_id == Customer.id)
            .join(Address, BookingRequest.address_id == Address.id)
            .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
            .outerjoin(Appointment, Appointment.booking_request_id == BookingRequest.id)
            .where(BookingRequest.status == "approved_for_scheduling", Appointment.id.is_(None))
            .order_by(BookingRequest.preferred_date.asc(), BookingRequest.id.asc())
        ).all()
    )


def dispatch_appointments(session: Session, selected_date: date) -> dict[tuple[int, str], tuple[Appointment, BookingRequest, Customer, ServiceType]]:
    start_of_day = datetime.combine(selected_date, time.min, tzinfo=MANILA_TIMEZONE)
    end_of_day = datetime.combine(selected_date + timedelta(days=1), time.min, tzinfo=MANILA_TIMEZONE)
    rows = session.execute(
        select(Appointment, BookingRequest, Customer, ServiceType)
        .join(BookingRequest, Appointment.booking_request_id == BookingRequest.id)
        .join(Customer, BookingRequest.customer_id == Customer.id)
        .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
        .where(Appointment.scheduled_start >= start_of_day, Appointment.scheduled_start < end_of_day)
    ).all()
    return {
        (appointment.service_team_id, appointment.scheduled_start.astimezone(MANILA_TIMEZONE).strftime("%H:%M")): row
        for row in rows
        for appointment in (row[0],)
    }


def render_booking_form(
    request: Request,
    session: Session,
    *,
    values: dict[str, Any] | None = None,
    errors: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "booking_form.html",
        {
            "services": active_service_types(session),
            "values": values or {},
            "errors": errors or {},
        },
        status_code=status_code,
    )


def validation_error_messages(error: ValidationError) -> dict[str, str]:
    messages: dict[str, str] = {}
    for item in error.errors():
        location = item["loc"][-1]
        messages[str(location)] = item["msg"]
    return messages


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "mode": "local_prototype"}


@app.get("/book", response_class=HTMLResponse)
def booking_form(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Render the local synthetic-data booking form."""
    return render_booking_form(request, session)


@app.get("/staff/requests", response_class=HTMLResponse)
def staff_request_queue(
    request: Request,
    reviewed: str | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Render the loopback-only read-only queue for pending staff review."""
    return templates.TemplateResponse(
        request,
        "staff_requests.html",
        {"requests": pending_staff_requests(session), "reviewed": reviewed},
    )


@app.post("/staff/requests/{booking_request_id}/review")
def review_staff_request(
    booking_request_id: int,
    decision: str = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Save a staff review outcome without scheduling work or sending messages."""
    try:
        booking = review_booking_request(session, booking_request_id, decision)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The review decision could not be saved safely.") from error

    return RedirectResponse(url=app_path(f"/staff/requests?reviewed={booking.status}"), status_code=status.HTTP_303_SEE_OTHER)


@app.get("/staff/dispatch", response_class=HTMLResponse)
def dispatch_board(
    request: Request,
    selected_date: date | None = None,
    scheduled: str | None = None,
    job_updated: str | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Render a small local two-team dispatcher board for one selected day."""
    approved_requests = approved_unscheduled_requests(session)
    board_date = selected_date or (approved_requests[0][0].preferred_date if approved_requests else date.today())
    return templates.TemplateResponse(
        request,
        "dispatch_board.html",
        {
            "teams": active_service_teams(session),
            "approved_requests": approved_requests,
            "appointments": dispatch_appointments(session, board_date),
            "selected_date": board_date,
            "slots": [(key, label) for key, (label, _, _) in DISPATCH_SLOTS.items()],
            "scheduled": scheduled,
            "job_updated": job_updated,
        },
    )


@app.post("/staff/dispatch/assign")
def assign_dispatch_slot(
    booking_request_id: int = Form(),
    service_team_id: int = Form(),
    appointment_date: date = Form(),
    slot_key: str = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Assign one approved request to an open fixed team/time block."""
    try:
        appointment = schedule_approved_booking(
            session,
            booking_request_id=booking_request_id,
            service_team_id=service_team_id,
            appointment_date=appointment_date,
            slot_key=slot_key,
        )
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That time block was just assigned. Refresh the board and try another block.") from error

    return RedirectResponse(
        url=app_path(f"/staff/dispatch?selected_date={appointment.scheduled_start.astimezone(MANILA_TIMEZONE).date()}&scheduled=1"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/staff/appointments/{appointment_id}/status")
def update_scheduled_job_status(
    appointment_id: int,
    next_status: str = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Record a local team-progress update without sending any message."""
    try:
        if next_status == "completed_now":
            appointment = complete_appointment_shortcut(session, appointment_id)
        else:
            appointment = update_appointment_status(session, appointment_id, next_status)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    selected_date = appointment.scheduled_start.astimezone(MANILA_TIMEZONE).date()
    return RedirectResponse(
        url=app_path(f"/staff/dispatch?selected_date={selected_date}&job_updated={appointment.status}"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/staff/automation", response_class=HTMLResponse)
def automation_outbox(
    request: Request,
    processed: int | None = None,
    pushed: int | None = None,
    rejected: int | None = None,
    push_error: int | None = None,
    worker: str | None = None,
    due: int | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Show local-only automation events; no external workflow is connected."""
    events = list(session.scalars(select(NotificationOutbox).order_by(NotificationOutbox.id.desc())).all())
    return templates.TemplateResponse(
        request,
        "automation_outbox.html",
        {
            "events": events,
            "processed": processed,
            "pushed": pushed,
            "rejected": rejected,
            "push_error": push_error,
            "worker": worker,
            "due": due,
            "automatic_delivery_enabled": automatic_delivery_enabled(),
        },
    )


@app.get("/staff/documentation/phases", response_class=HTMLResponse)
def phase_roadmap(request: Request) -> HTMLResponse:
    """Show the completed synthetic-project roadmap in the local app."""
    phases = [
        {"number": 0, "title": "MVP plan", "summary": "Defined a bounded synthetic-only booking and dispatcher prototype.", "result": "Scope and safety rules set"},
        {"number": 1, "title": "Local foundation", "summary": "Created Python, Pytest, and local PostgreSQL foundations.", "result": "Testable local app"},
        {"number": 2, "title": "Booking database", "summary": "Added controlled relational records, constraints, and fictional seed data.", "result": "Safe data model"},
        {"number": 3, "title": "Request form", "summary": "Built the local service-request form and reference receipt.", "result": "Pending-review requests"},
        {"number": 4, "title": "Staff review and dispatch", "summary": "Added approval flow and fixed Team A / Team B time blocks.", "result": "Scheduled synthetic jobs"},
        {"number": 5, "title": "Job lifecycle", "summary": "Added en route, in progress, completed, cancellation, and audit history.", "result": "Traceable field workflow"},
        {"number": 6, "title": "Protected n8n workflow", "summary": "Created an unpublished, Header-Auth synthetic n8n webhook.", "result": "Safe test automation"},
        {"number": 7, "title": "App-to-n8n bridge", "summary": "Connected one local outbox event at a time to the n8n test webhook.", "result": "Recorded processing result"},
        {"number": 8, "title": "Completion notice", "summary": "Added the complete-job shortcut and local dispatcher notice display.", "result": "Operational completion context"},
        {"number": 9, "title": "Failure and retry proof", "summary": "Verified duplicate prevention, pending preservation, and controlled retry.", "result": "Reliable delivery evidence"},
    ]
    return templates.TemplateResponse(request, "phase_roadmap.html", {"phases": phases})


@app.post("/staff/automation/process")
def process_automation_outbox(session: Session = Depends(get_session)) -> RedirectResponse:
    """Run a local stand-in for a future n8n outbox workflow."""
    processed = process_pending_simulated_events(session)
    session.commit()
    return RedirectResponse(url=app_path(f"/staff/automation?processed={processed}"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/automation/worker-check")
def check_due_delivery_worker(session: Session = Depends(get_session)) -> RedirectResponse:
    """Show whether due events could run without starting an automatic sender."""
    worker, due = run_due_delivery_worker_check(session)
    return RedirectResponse(url=app_path(f"/staff/automation?worker={worker}&due={due}"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/automation/push")
def push_automation_event_to_n8n(session: Session = Depends(get_session)) -> RedirectResponse:
    """Send exactly one synthetic outbox event to the opt-in n8n test webhook."""
    try:
        event = push_one_pending_event_to_n8n(session)
        session.commit()
    except ValueError as error:
        session.rollback()
        return RedirectResponse(url=app_path("/staff/automation?push_error=1"), status_code=status.HTTP_303_SEE_OTHER)

    if event.status == "failed":
        return RedirectResponse(url=app_path(f"/staff/automation?rejected={event.id}"), status_code=status.HTTP_303_SEE_OTHER)
    if event.status == "pending":
        return RedirectResponse(url=app_path("/staff/automation?push_error=1"), status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=app_path(f"/staff/automation?pushed={event.id}"), status_code=status.HTTP_303_SEE_OTHER)


def appointment_detail_context(session: Session, appointment_id: int) -> dict[str, Any]:
    """Load read-only scheduled-job context for a full page or dispatcher modal."""
    row = session.execute(
        select(Appointment, BookingRequest, Customer, Address, ServiceTeam, ServiceType)
        .join(BookingRequest, Appointment.booking_request_id == BookingRequest.id)
        .join(Customer, BookingRequest.customer_id == Customer.id)
        .join(Address, BookingRequest.address_id == Address.id)
        .join(ServiceTeam, Appointment.service_team_id == ServiceTeam.id)
        .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
        .where(Appointment.id == appointment_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The scheduled appointment does not exist.")

    appointment, booking, customer, address, team, service_type = row
    booking_history = list(
        session.scalars(
            select(BookingRequestStatusHistory)
            .where(BookingRequestStatusHistory.booking_request_id == booking.id)
            .order_by(BookingRequestStatusHistory.occurred_at.asc(), BookingRequestStatusHistory.id.asc())
        ).all()
    )
    appointment_history = list(
        session.scalars(
            select(AppointmentStatusHistory)
            .where(AppointmentStatusHistory.appointment_id == appointment.id)
            .order_by(AppointmentStatusHistory.occurred_at.asc(), AppointmentStatusHistory.id.asc())
        ).all()
    )
    local_start = appointment.scheduled_start.astimezone(MANILA_TIMEZONE)
    local_end = appointment.scheduled_end.astimezone(MANILA_TIMEZONE)
    return {
        "appointment": appointment,
        "booking": booking,
        "customer": customer,
        "address": address,
        "team": team,
        "service_type": service_type,
        "booking_history": booking_history,
        "appointment_history": appointment_history,
        "available_status_updates": APPOINTMENT_STATUS_TRANSITIONS.get(appointment.status, {}),
        "scheduled_date": local_start.strftime("%B %d, %Y"),
        "scheduled_time": f"{local_start:%H:%M}-{local_end:%H:%M}",
    }


@app.get("/staff/appointments/{appointment_id}", response_class=HTMLResponse)
def appointment_details(appointment_id: int, request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Render a read-only local detail page as a non-JavaScript fallback."""
    return templates.TemplateResponse(request, "appointment_details.html", appointment_detail_context(session, appointment_id))


@app.get("/staff/appointments/{appointment_id}/fragment", response_class=HTMLResponse)
def appointment_details_fragment(appointment_id: int, request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Render a read-only scheduled-job fragment for the dispatcher-board modal."""
    return templates.TemplateResponse(request, "appointment_details_content.html", appointment_detail_context(session, appointment_id))


@app.post("/book", response_class=HTMLResponse, status_code=status.HTTP_201_CREATED)
def submit_booking_form(
    request: Request,
    full_name: str = Form(),
    mobile: str = Form(),
    email: str = Form(default=""),
    address_line: str = Form(),
    barangay: str = Form(),
    city: str = Form(),
    coverage_area: str = Form(),
    aircon_type: str = Form(default="Window Type"),
    service_type_id: str = Form(),
    preferred_date: str = Form(),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Validate and save a local form submission as pending staff review."""
    values = {
        "full_name": full_name,
        "mobile": mobile,
        "email": email,
        "address_line": address_line,
        "barangay": barangay,
        "city": city,
        "coverage_area": coverage_area,
        "aircon_type": aircon_type,
        "service_type_id": service_type_id,
        "preferred_date": preferred_date,
        "preferred_window": "09:00-12:00",
        "unit_count": "1",
        "notes": "",
    }
    try:
        booking_input = BookingRequestInput.model_validate(values)
    except ValidationError as error:
        return render_booking_form(
            request,
            session,
            values=values,
            errors=validation_error_messages(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    try:
        booking = create_pending_booking(session, booking_input)
        session.commit()
    except ValueError as error:
        session.rollback()
        return render_booking_form(
            request,
            session,
            values=values,
            errors={"service_type_id": str(error)},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The booking request could not be saved safely. Please review the request and try again.",
        ) from error

    return templates.TemplateResponse(
        request,
        "booking_received.html",
        {"reference_code": booking.reference_code, "status": booking.status},
        status_code=status.HTTP_201_CREATED,
    )


@app.post("/bookings", response_model=BookingReceipt, status_code=status.HTTP_201_CREATED)
def submit_booking(
    booking_input: BookingRequestInput,
    session: Session = Depends(get_session),
) -> BookingReceipt:
    """Create a review-required booking request from validated input."""
    try:
        booking = create_pending_booking(session, booking_input)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The booking request could not be saved safely. Please review the request and try again.",
        ) from error

    return BookingReceipt(
        reference_code=booking.reference_code,
        status=booking.status,
        message="Your request was received and is pending staff review.",
    )
