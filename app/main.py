"""Local FastAPI application for controlled booking requests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from datetime import date, datetime, time, timedelta
import os
import re
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.booking.schedule_intake import parse_raw_schedule
from app.booking.service import APPOINTMENT_STATUS_TRANSITIONS, DISPATCH_SLOTS, MANILA_TIMEZONE, automatic_delivery_enabled, complete_appointment_shortcut, create_pending_booking, display_address, process_pending_simulated_events, push_one_pending_event_to_n8n, record_operational_job_event, reschedule_appointment, review_booking_request, run_due_delivery_worker_check, schedule_approved_booking, update_appointment_status
from app.booking.validation import BookingRequestInput
from app.database.models import Address, Appointment, AppointmentStatusHistory, BookingRequest, BookingRequestStatusHistory, Customer, NotificationOutbox, OperationalJob, ScheduleIntake, ScheduleIntakeItem, ServiceTeam, ServiceType, TeamMembership, Technician
from app.database.session import create_database_engine
from app.core.project_info import is_live_mode


app = FastAPI(
    title="Aircon Service Automation",
    version="0.1.0",
    description="Controlled air-conditioning service booking and owner operations application.",
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
templates.env.globals["is_live_mode"] = is_live_mode
templates.env.globals["address_display"] = display_address
templates.env.globals["operation_mode_label"] = lambda: "Live owner operations" if is_live_mode() else "Local prototype · synthetic data only"
templates.env.globals["staff_operator_name"] = lambda: (
    os.getenv("AIRCON_STAFF_DISPLAY_NAME", "").strip()
    or os.getenv("AIRCON_STAFF_USERNAME", "Operator").strip()
    or "Operator"
)
templates.env.globals["manila_now"] = lambda: datetime.now(MANILA_TIMEZONE)
templates.env.globals["to_manila"] = lambda value: value.astimezone(MANILA_TIMEZONE)

REPEAT_LOCATION_WARNING = "Possible repeat location; confirm separate job"


def important_staff_note(value: str) -> str:
    """Keep staff-entered alerts, while removing former routine system reminders."""
    note = value.strip()
    for pattern in (
        r"Auto-assigned.*?same-building rule",
        r"Replace\s+Client_.*?\s+with real name",
        r"Add team",
        r"Add customer name",
        r"Add time",
        re.escape(REPEAT_LOCATION_WARNING),
    ):
        note = re.sub(pattern, "", note, flags=re.IGNORECASE)
    return re.sub(r"(?:\s*[·]\s*){2,}", " · ", note).strip(" ·")


def automation_health(session: Session) -> dict[str, object]:
    """Return owner-facing delivery health from the local outbox evidence."""
    pending = session.scalar(
        select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == "pending")
    ) or 0
    retrying = session.scalar(
        select(func.count()).select_from(NotificationOutbox).where(
            NotificationOutbox.status == "pending",
            or_(NotificationOutbox.last_error.is_not(None), NotificationOutbox.next_attempt_at.is_not(None)),
        )
    ) or 0
    failed = session.scalar(
        select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == "failed")
    ) or 0
    last_recorded = session.scalar(
        select(NotificationOutbox)
        .where(NotificationOutbox.status == "recorded")
        .order_by(NotificationOutbox.id.desc())
        .limit(1)
    )
    last_sync_display = "No recorded sync yet"
    if last_recorded is not None:
        recorded_at = last_recorded.payload.get("recorded_at")
        if recorded_at:
            recorded_datetime = datetime.fromisoformat(str(recorded_at))
        else:
            recorded_datetime = last_recorded.created_at
        if recorded_datetime.tzinfo is None:
            recorded_datetime = recorded_datetime.replace(tzinfo=MANILA_TIMEZONE)
        last_sync_display = recorded_datetime.astimezone(MANILA_TIMEZONE).strftime("%b %d, %Y · %I:%M %p PHT")
    return {
        "pending": pending,
        "retrying": retrying,
        "failed": failed,
        "last_sync_display": last_sync_display,
        "state": "Needs attention" if failed or retrying else "Operational",
    }


def staff_auth_enabled() -> bool:
    """Keep staff authentication enabled unless the VPS explicitly disables it."""
    return os.getenv("AIRCON_STAFF_AUTH_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _staff_credentials_valid(request: Request) -> bool:
    """Validate environment-backed staff Basic Auth without storing credentials in code."""
    import secrets

    expected_user = os.getenv("AIRCON_STAFF_USERNAME", "").strip()
    expected_password = os.getenv("AIRCON_STAFF_PASSWORD", "")
    if not expected_user or not expected_password:
        return False
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("basic "):
        return False
    import base64
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error):
        return False
    return secrets.compare_digest(username, expected_user) and secrets.compare_digest(password, expected_password)


@app.middleware("http")
async def protect_staff_routes(request: Request, call_next: Any) -> Any:
    """Require Basic Auth for owner/staff pages when live mode is enabled."""
    staff_paths = ("/staff", "/staff/")
    prefixed_staff_path = f"{PUBLIC_BASE_PATH}/staff" if PUBLIC_BASE_PATH else ""
    is_staff_path = request.url.path == "/staff" or request.url.path.startswith(staff_paths[1]) or (
        prefixed_staff_path and (request.url.path == prefixed_staff_path or request.url.path.startswith(f"{prefixed_staff_path}/"))
    )
    if is_live_mode() and staff_auth_enabled() and is_staff_path:
        if not _staff_credentials_valid(request):
            return JSONResponse(
                {"detail": "Staff authentication is required."},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic realm=Balik-Lamig staff"},
            )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def friendly_http_error(request: Request, error: HTTPException) -> HTMLResponse | JSONResponse:
    """Render staff workflow errors as usable admin pages instead of raw JSON."""
    if "/staff" in request.url.path:
        return templates.TemplateResponse(
            request,
            "admin_error.html",
            {"status_code": error.status_code, "detail": error.detail},
            status_code=error.status_code,
            headers=error.headers,
        )
    return JSONResponse({"detail": error.detail}, status_code=error.status_code, headers=error.headers)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page(request: Request) -> HTMLResponse:
    """Render the public Balik-Lamig landing page."""
    return templates.TemplateResponse(request=request, name="landing.html")


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


def pending_staff_requests(
    session: Session,
    *,
    search: str = "",
    preferred_date: date | None = None,
) -> list[tuple[BookingRequest, Customer, Address, ServiceType]]:
    """Return pending requests for the local staff-review queue only."""
    statement = (
        select(BookingRequest, Customer, Address, ServiceType)
            .join(Customer, BookingRequest.customer_id == Customer.id)
            .join(Address, BookingRequest.address_id == Address.id)
            .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
            .where(BookingRequest.status == "pending_review")
            .order_by(BookingRequest.created_at.asc(), BookingRequest.id.asc())
    )
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        statement = statement.where(
            or_(
                BookingRequest.reference_code.ilike(pattern),
                Customer.full_name.ilike(pattern),
                Customer.mobile.ilike(pattern),
                Customer.email.ilike(pattern),
                Address.address_line.ilike(pattern),
            )
        )
    if preferred_date is not None:
        statement = statement.where(BookingRequest.preferred_date == preferred_date)
    return list(session.execute(statement).all())


def waitlisted_staff_requests(
    session: Session,
    *,
    search: str = "",
    preferred_date: date | None = None,
) -> list[tuple[BookingRequest, Customer, Address, ServiceType]]:
    """Return waitlisted requests for staff capacity management."""
    statement = (
        select(BookingRequest, Customer, Address, ServiceType)
        .join(Customer, BookingRequest.customer_id == Customer.id)
        .join(Address, BookingRequest.address_id == Address.id)
        .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
        .where(BookingRequest.status == "waitlisted")
        .order_by(BookingRequest.created_at.asc(), BookingRequest.id.asc())
    )
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        statement = statement.where(
            or_(
                BookingRequest.reference_code.ilike(pattern),
                Customer.full_name.ilike(pattern),
                Customer.mobile.ilike(pattern),
                Customer.email.ilike(pattern),
                Address.address_line.ilike(pattern),
            )
        )
    if preferred_date is not None:
        statement = statement.where(BookingRequest.preferred_date == preferred_date)
    return list(session.execute(statement).all())


def active_service_teams(session: Session) -> list[ServiceTeam]:
    return list(session.scalars(select(ServiceTeam).where(ServiceTeam.active.is_(True)).order_by(ServiceTeam.name)).all())


def booking_date_availability(session: Session, selected_date: date) -> dict[str, int | bool]:
    """Return the remaining active team slots for a preferred service date."""
    start_of_day = datetime.combine(selected_date, time.min, tzinfo=MANILA_TIMEZONE)
    end_of_day = datetime.combine(selected_date + timedelta(days=1), time.min, tzinfo=MANILA_TIMEZONE)
    team_count = session.scalar(
        select(func.count()).select_from(ServiceTeam).where(ServiceTeam.active.is_(True))
    ) or 0
    booked_count = session.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.scheduled_start >= start_of_day,
            Appointment.scheduled_start < end_of_day,
            Appointment.status != "cancelled",
        )
    ) or 0
    capacity = team_count * len(DISPATCH_SLOTS)
    remaining = max(capacity - booked_count, 0)
    return {
        "capacity": capacity,
        "booked": booked_count,
        "remaining": remaining,
        "fully_booked": capacity == 0 or remaining == 0,
    }


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


def dispatch_appointments(session: Session, selected_date: date) -> dict[tuple[int, str], tuple[Appointment, BookingRequest, Customer, ServiceType, Address]]:
    start_of_day = datetime.combine(selected_date, time.min, tzinfo=MANILA_TIMEZONE)
    end_of_day = datetime.combine(selected_date + timedelta(days=1), time.min, tzinfo=MANILA_TIMEZONE)
    rows = session.execute(
        select(Appointment, BookingRequest, Customer, ServiceType, Address)
        .join(BookingRequest, Appointment.booking_request_id == BookingRequest.id)
        .join(Customer, BookingRequest.customer_id == Customer.id)
        .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
        .join(Address, BookingRequest.address_id == Address.id)
        .where(
            Appointment.scheduled_start >= start_of_day,
            Appointment.scheduled_start < end_of_day,
            Appointment.status != "cancelled",
        )
    ).all()
    return {
        (appointment.service_team_id, appointment.scheduled_start.astimezone(MANILA_TIMEZONE).strftime("%H:%M")): row
        for row in rows
        for appointment in (row[0],)
    }


def team_timeline_jobs(session: Session, selected_date: date) -> dict[int, list[dict[str, Any]]]:
    """Return every scheduled job for the selected day grouped by team and time."""
    timeline: dict[int, list[dict[str, Any]]] = {}
    shared_rows = session.execute(
        select(OperationalJob, ServiceTeam)
        .join(ServiceTeam, OperationalJob.service_team_id == ServiceTeam.id)
        .where(
            OperationalJob.scheduled_date == selected_date,
            OperationalJob.service_team_id.is_not(None),
            OperationalJob.status != "cancelled",
        )
        .order_by(OperationalJob.service_team_id, OperationalJob.scheduled_time, OperationalJob.id)
    ).all()
    linked_booking_ids: set[int] = set()
    for job, team in shared_rows:
        if job.booking_request_id is not None:
            linked_booking_ids.add(job.booking_request_id)
        timeline.setdefault(team.id, []).append(
            {
                "time": job.scheduled_time,
                "time_label": job.scheduled_time.strftime("%I:%M %p") if job.scheduled_time else "Time missing",
                "service_label": job.service_label,
                "customer_label": job.customer_label,
                "address_label": job.address_label,
                "status": job.status.replace("_", " "),
                "is_provisional": job.customer_is_provisional,
                "source_label": "Team intake" if job.source == "team_intake" else "Customer booking",
                "detail_url": app_path(f"/staff/appointments/{job.appointment_id}") if job.appointment_id else None,
            }
        )

    start_of_day = datetime.combine(selected_date, time.min, tzinfo=MANILA_TIMEZONE)
    end_of_day = datetime.combine(selected_date + timedelta(days=1), time.min, tzinfo=MANILA_TIMEZONE)
    appointment_rows = session.execute(
        select(Appointment, BookingRequest, Customer, Address, ServiceTeam, ServiceType)
        .join(BookingRequest, Appointment.booking_request_id == BookingRequest.id)
        .join(Customer, BookingRequest.customer_id == Customer.id)
        .join(Address, BookingRequest.address_id == Address.id)
        .join(ServiceTeam, Appointment.service_team_id == ServiceTeam.id)
        .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
        .where(
            Appointment.scheduled_start >= start_of_day,
            Appointment.scheduled_start < end_of_day,
            Appointment.status != "cancelled",
        )
        .order_by(Appointment.service_team_id, Appointment.scheduled_start)
    ).all()
    for appointment, booking, customer, address, team, service_type in appointment_rows:
        if booking.id in linked_booking_ids:
            continue
        local_start = appointment.scheduled_start.astimezone(MANILA_TIMEZONE)
        timeline.setdefault(team.id, []).append(
            {
                "time": local_start.time(),
                "time_label": local_start.strftime("%I:%M %p"),
                "service_label": service_type.name,
                "customer_label": customer.full_name,
                "address_label": display_address(address),
                "status": appointment.status.replace("_", " "),
                "is_provisional": False,
                "source_label": "Customer booking",
                "detail_url": app_path(f"/staff/appointments/{appointment.id}"),
            }
        )
    for jobs in timeline.values():
        jobs.sort(key=lambda job: (job["time"] is None, job["time"] or time.max))
    return timeline


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
            "availability_endpoint": app_path("/book/availability"),
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
    return {"status": "ok", "mode": "live" if is_live_mode() else "local_prototype"}


@app.get("/book", response_class=HTMLResponse)
def booking_form(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Render the local synthetic-data booking form."""
    return render_booking_form(request, session)


@app.get("/book/availability")
def booking_availability(preferred_date: date, session: Session = Depends(get_session)) -> JSONResponse:
    return JSONResponse(booking_date_availability(session, preferred_date))


@app.get("/staff", response_class=HTMLResponse)
def staff_dashboard(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Render the owner/operator command center."""
    today = datetime.now(MANILA_TIMEZONE).date()
    start_of_day = datetime.combine(today, time.min, tzinfo=MANILA_TIMEZONE)
    end_of_day = datetime.combine(today + timedelta(days=1), time.min, tzinfo=MANILA_TIMEZONE)
    pending_intake_items = session.scalar(
        select(func.count())
        .select_from(ScheduleIntakeItem)
        .join(ScheduleIntake, ScheduleIntakeItem.schedule_intake_id == ScheduleIntake.id)
        .where(ScheduleIntake.status != "confirmed", ScheduleIntakeItem.review_status != "skipped")
    ) or 0
    metrics = {
        "pending_review": (session.scalar(
            select(func.count()).select_from(BookingRequest).where(BookingRequest.status == "pending_review")
        ) or 0) + pending_intake_items,
        "awaiting_assignment": session.scalar(
            select(func.count()).select_from(OperationalJob).where(
                OperationalJob.status == "approved_for_scheduling", OperationalJob.service_team_id.is_(None)
            )
        ) or 0,
        "today_appointments": session.scalar(
            select(func.count()).select_from(OperationalJob).where(
                OperationalJob.scheduled_date == today, OperationalJob.status != "cancelled"
            )
        ) or 0,
        "active_teams": session.scalar(
            select(func.count()).select_from(ServiceTeam).where(ServiceTeam.active.is_(True))
        ) or 0,
        "pending_automation": session.scalar(
            select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == "pending")
        ) or 0,
        "failed_automation": session.scalar(
            select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == "failed")
        ) or 0,
    }
    upcoming_jobs = list(
        session.scalars(
            select(OperationalJob)
            .where(OperationalJob.scheduled_date >= today, OperationalJob.status != "cancelled")
            .order_by(OperationalJob.scheduled_date.asc(), OperationalJob.scheduled_time.asc())
            .limit(6)
        )
    )
    team_names = {team.id: team.name for team in session.scalars(select(ServiceTeam))}
    job_status_counts = {
        job_status: session.scalar(
            select(func.count()).select_from(OperationalJob).where(OperationalJob.status == job_status)
        ) or 0
        for job_status in ("pending_review", "scheduled", "confirmed", "en_route", "in_progress", "completed", "cancelled")
    }
    reporting_health = automation_health(session)
    return templates.TemplateResponse(
        request,
        "staff_dashboard.html",
        {
            "metrics": metrics,
            "today": today,
            "upcoming_jobs": upcoming_jobs,
            "team_names": team_names,
            "job_status_counts": job_status_counts,
            "automatic_delivery_enabled": automatic_delivery_enabled(),
            "reporting_health": reporting_health,
        },
    )


@app.get("/staff/appointments", response_class=HTMLResponse)
def appointment_directory(
    request: Request,
    q: str = "",
    appointment_status: str = "",
    scheduled_date: date | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """List every shared operational job with operational filters."""
    statement = select(OperationalJob, ServiceTeam).outerjoin(
        ServiceTeam, OperationalJob.service_team_id == ServiceTeam.id
    )
    if q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                OperationalJob.customer_label.ilike(pattern),
                OperationalJob.address_label.ilike(pattern),
                OperationalJob.service_label.ilike(pattern),
                ServiceTeam.name.ilike(pattern),
            )
        )
    if appointment_status:
        statement = statement.where(OperationalJob.status == appointment_status)
    else:
        statement = statement.where(OperationalJob.status != "cancelled")
    if scheduled_date is not None:
        statement = statement.where(OperationalJob.scheduled_date == scheduled_date)
    statement = statement.order_by(ServiceTeam.name.asc(), OperationalJob.scheduled_date.asc(), OperationalJob.scheduled_time.asc())
    return templates.TemplateResponse(
        request,
        "appointment_directory.html",
        {
            "appointments": list(session.execute(statement).all()),
            "q": q,
            "appointment_status_filter": appointment_status,
            "scheduled_date_filter": scheduled_date,
        },
    )


@app.get("/staff/customers", response_class=HTMLResponse)
def customer_directory(request: Request, q: str = "", session: Session = Depends(get_session)) -> HTMLResponse:
    """List customers and their booking volume."""
    statement = select(Customer).order_by(Customer.full_name.asc())
    if q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(Customer.full_name.ilike(pattern), Customer.mobile.ilike(pattern), Customer.email.ilike(pattern))
        )
    customers = list(session.scalars(statement).all())
    booking_counts = {
        customer.id: session.scalar(
            select(func.count()).select_from(BookingRequest).where(BookingRequest.customer_id == customer.id)
        ) or 0
        for customer in customers
    }
    provisional_statement = select(OperationalJob).where(
        OperationalJob.customer_is_provisional.is_(True),
        OperationalJob.status != "cancelled",
    ).order_by(OperationalJob.scheduled_date.desc(), OperationalJob.id.desc())
    if q.strip():
        pattern = f"%{q.strip()}%"
        provisional_statement = provisional_statement.where(
            or_(
                OperationalJob.customer_label.ilike(pattern),
                OperationalJob.address_label.ilike(pattern),
                OperationalJob.service_label.ilike(pattern),
            )
        )
    provisional_jobs = list(session.scalars(provisional_statement).all())
    return templates.TemplateResponse(
        request,
        "customer_directory.html",
        {
            "customers": customers,
            "booking_counts": booking_counts,
            "provisional_jobs": provisional_jobs,
            "q": q,
        },
    )


@app.get("/staff/customers/{customer_id}", response_class=HTMLResponse)
def customer_details(customer_id: int, request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Show one customer's addresses and complete service history."""
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The customer does not exist.")
    addresses = list(session.scalars(select(Address).where(Address.customer_id == customer.id)).all())
    bookings = list(
        session.execute(
            select(BookingRequest, ServiceType, Appointment, ServiceTeam)
            .join(ServiceType, BookingRequest.service_type_id == ServiceType.id)
            .outerjoin(Appointment, Appointment.booking_request_id == BookingRequest.id)
            .outerjoin(ServiceTeam, Appointment.service_team_id == ServiceTeam.id)
            .where(BookingRequest.customer_id == customer.id)
            .order_by(BookingRequest.created_at.desc())
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "customer_details.html",
        {"customer": customer, "addresses": addresses, "bookings": bookings},
    )


@app.get("/staff/teams", response_class=HTMLResponse)
def team_directory(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Manage service teams and technician memberships."""
    teams = list(session.scalars(select(ServiceTeam).order_by(ServiceTeam.name)).all())
    technicians = list(session.scalars(select(Technician).order_by(Technician.display_name)).all())
    memberships = list(session.scalars(select(TeamMembership)).all())
    members_by_team: dict[int, list[tuple[TeamMembership, Technician]]] = {team.id: [] for team in teams}
    technicians_by_id = {technician.id: technician for technician in technicians}
    for membership in memberships:
        technician = technicians_by_id.get(membership.technician_id)
        if technician is not None:
            members_by_team.setdefault(membership.service_team_id, []).append((membership, technician))
    return templates.TemplateResponse(
        request,
        "team_directory.html",
        {"teams": teams, "technicians": technicians, "members_by_team": members_by_team},
    )


@app.post("/staff/technicians")
def create_technician(display_name: str = Form(), session: Session = Depends(get_session)) -> RedirectResponse:
    name = display_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Technician name is required.")
    try:
        session.add(Technician(display_name=name, active=True))
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A technician with that name already exists.") from error
    return RedirectResponse(url=app_path("/staff/teams"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/teams")
def create_service_team(name: str = Form(), session: Session = Depends(get_session)) -> RedirectResponse:
    team_name = name.strip()
    if not team_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Team name is required.")
    try:
        session.add(ServiceTeam(name=team_name, active=True))
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A service team with that name already exists.") from error
    return RedirectResponse(url=app_path("/staff/teams"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/teams/{team_id}/members")
def assign_team_member(
    team_id: int,
    technician_id: int = Form(),
    is_lead: bool = Form(default=False),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    team = session.get(ServiceTeam, team_id)
    technician = session.get(Technician, technician_id)
    if team is None or technician is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The selected team or technician does not exist.")
    if is_lead:
        for current_lead in session.scalars(
            select(TeamMembership).where(TeamMembership.service_team_id == team.id, TeamMembership.is_lead.is_(True))
        ):
            current_lead.is_lead = False
    membership = session.scalar(
        select(TeamMembership).where(
            TeamMembership.service_team_id == team.id,
            TeamMembership.technician_id == technician.id,
        )
    )
    if membership is None:
        membership = TeamMembership(service_team_id=team.id, technician_id=technician.id, is_lead=is_lead)
        session.add(membership)
    else:
        membership.is_lead = is_lead
    session.commit()
    return RedirectResponse(url=app_path("/staff/teams"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/teams/{team_id}/toggle")
def toggle_team(team_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    team = session.get(ServiceTeam, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The service team does not exist.")
    if team.active:
        future_work = session.scalar(
            select(func.count()).select_from(Appointment).where(
                Appointment.service_team_id == team.id,
                Appointment.status.not_in(("completed", "cancelled")),
                Appointment.scheduled_start >= datetime.now(MANILA_TIMEZONE),
            )
        ) or 0
        if future_work:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{team.name} still has {future_work} active or future appointment(s). Reassign or finish them first.",
            )
    team.active = not team.active
    session.commit()
    return RedirectResponse(url=app_path("/staff/teams"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/technicians/{technician_id}/toggle")
def toggle_technician(technician_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    technician = session.get(Technician, technician_id)
    if technician is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The technician does not exist.")
    if technician.active:
        future_work = session.scalar(
            select(func.count()).select_from(Appointment).where(
                Appointment.technician_id == technician.id,
                Appointment.status.not_in(("completed", "cancelled")),
                Appointment.scheduled_start >= datetime.now(MANILA_TIMEZONE),
            )
        ) or 0
        if future_work:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{technician.display_name} still has {future_work} active or future appointment(s). Reassign or finish them first.",
            )
    technician.active = not technician.active
    session.commit()
    return RedirectResponse(url=app_path("/staff/teams"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/teams/{team_id}/members/{membership_id}/remove")
def remove_team_member(
    team_id: int,
    membership_id: int,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    membership = session.get(TeamMembership, membership_id)
    if membership is None or membership.service_team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That team membership does not exist.")
    session.delete(membership)
    session.commit()
    return RedirectResponse(url=app_path("/staff/teams"), status_code=status.HTTP_303_SEE_OTHER)


@app.get("/staff/activity", response_class=HTMLResponse)
def activity_history(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Display the latest booking and appointment audit events."""
    events: list[dict[str, Any]] = []
    for history, booking in session.execute(
        select(BookingRequestStatusHistory, BookingRequest)
        .join(BookingRequest, BookingRequestStatusHistory.booking_request_id == BookingRequest.id)
        .order_by(BookingRequestStatusHistory.occurred_at.desc())
        .limit(75)
    ):
        events.append({"occurred_at": history.occurred_at, "reference": booking.reference_code, "kind": "Request", "from_status": history.from_status, "to_status": history.to_status, "note": history.note})
    for history, booking in session.execute(
        select(AppointmentStatusHistory, BookingRequest)
        .join(Appointment, AppointmentStatusHistory.appointment_id == Appointment.id)
        .join(BookingRequest, Appointment.booking_request_id == BookingRequest.id)
        .order_by(AppointmentStatusHistory.occurred_at.desc())
        .limit(75)
    ):
        events.append({"occurred_at": history.occurred_at, "reference": booking.reference_code, "kind": "Appointment", "from_status": history.from_status, "to_status": history.to_status, "note": history.note})
    events.sort(key=lambda event: event["occurred_at"], reverse=True)
    return templates.TemplateResponse(request, "activity_history.html", {"events": events[:100]})


@app.get("/staff/settings", response_class=HTMLResponse)
def staff_settings(request: Request) -> HTMLResponse:
    """Show deployment-safe operational settings without exposing secrets."""
    settings = {
        "operation_mode": "Live owner operations" if is_live_mode() else "Local prototype",
        "timezone": "Asia/Manila",
        "public_base_path": PUBLIC_BASE_PATH or "/",
        "automatic_delivery": automatic_delivery_enabled(),
        "webhook_configured": bool(os.getenv("AIRCON_N8N_WEBHOOK_URL") and os.getenv("AIRCON_N8N_WEBHOOK_KEY")),
        "staff_auth_configured": bool(os.getenv("AIRCON_STAFF_USERNAME") and os.getenv("AIRCON_STAFF_PASSWORD")),
        "staff_auth_enabled": staff_auth_enabled(),
    }
    return templates.TemplateResponse(request, "staff_settings.html", {"settings": settings})


@app.get("/staff/requests", response_class=HTMLResponse)
def staff_request_queue(
    request: Request,
    reviewed: str | None = None,
    q: str = "",
    preferred_date: date | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Render the loopback-only read-only queue for pending staff review."""
    return templates.TemplateResponse(
        request,
        "staff_requests.html",
        {
            "requests": pending_staff_requests(session, search=q, preferred_date=preferred_date),
            "waitlist_requests": waitlisted_staff_requests(session, search=q, preferred_date=preferred_date),
            "reviewed": reviewed,
            "q": q,
            "preferred_date_filter": preferred_date,
        },
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
    intake_published: str | None = None,
    demo: bool = False,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Render a small local two-team dispatcher board for one selected day."""
    approved_requests = approved_unscheduled_requests(session)
    board_date = selected_date or (approved_requests[0][0].preferred_date if approved_requests else date.today())
    # Once staff approves a request for scheduling, they may place it on any
    # selected date. The original preferred date remains visible on the card
    # as customer context, while the appointment date is chosen here.
    assignable_requests = approved_requests
    return templates.TemplateResponse(
        request,
        "dispatch_board.html",
        {
            "teams": active_service_teams(session),
            "approved_requests": approved_requests,
            "assignable_requests": assignable_requests,
            "timeline_jobs_by_team": team_timeline_jobs(session, board_date),
            "appointments": dispatch_appointments(session, board_date),
            "selected_date": board_date,
            "previous_date": board_date - timedelta(days=1),
            "next_date": board_date + timedelta(days=1),
            "today": datetime.now(MANILA_TIMEZONE).date(),
            "slots": [(key, label) for key, (label, _, _) in DISPATCH_SLOTS.items()],
            "scheduled": scheduled,
            "job_updated": job_updated,
            "intake_published": intake_published,
            "demo_preview": demo,
        },
    )


@app.get("/staff/schedule-intake", response_class=HTMLResponse)
def schedule_intake(request: Request, intake_id: int | None = None, show_skipped: bool = False, session: Session = Depends(get_session)) -> HTMLResponse:
    """Render the front-end-only raw schedule intake workspace."""
    intake = session.get(ScheduleIntake, intake_id) if intake_id else None
    recent_intakes = list(
        session.scalars(
            select(ScheduleIntake).order_by(desc(ScheduleIntake.id)).limit(10)
        )
    )
    intake_items = []
    all_intake_items = []
    if intake:
        all_intake_items = list(
            session.scalars(
                select(ScheduleIntakeItem)
                .where(ScheduleIntakeItem.schedule_intake_id == intake.id)
                .order_by(ScheduleIntakeItem.id)
            )
        )
        all_intake_items.sort(
            key=lambda item: (
                item.building_number if item.building_number is not None else 10**9,
                int(item.unit_number) if item.unit_number and item.unit_number.isdigit() else 10**9,
                item.id,
            )
        )
    skipped_count = sum(item.review_status == "skipped" for item in all_intake_items)
    intake_items = all_intake_items if show_skipped else [item for item in all_intake_items if item.review_status != "skipped"]
    return templates.TemplateResponse(
        request,
        "schedule_intake.html",
        {
            "selected_date": intake.schedule_date if intake else datetime.now(MANILA_TIMEZONE).date(),
            "latest_intake": intake,
            "intake_items": intake_items,
            "recent_intakes": recent_intakes,
            "intake_teams": list(session.scalars(select(ServiceTeam).where(ServiceTeam.active.is_(True)).order_by(ServiceTeam.name))),
            "intake_team_names": {
                team.id: team.name
                for team in session.scalars(select(ServiceTeam).where(ServiceTeam.active.is_(True)))
            },
            "show_skipped": show_skipped,
            "skipped_count": skipped_count,
        },
    )


@app.post("/staff/schedule-intake", response_class=RedirectResponse)
def create_schedule_intake(
    schedule_date: date = Form(),
    raw_message: str = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Save a pasted staff message and its editable draft rows."""
    if not raw_message.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Paste a schedule message first.")

    parsed_items = parse_raw_schedule(raw_message)
    intake = ScheduleIntake(schedule_date=schedule_date, raw_message=raw_message.strip())
    session.add(intake)
    session.flush()
    active_teams = list(session.scalars(select(ServiceTeam).where(ServiceTeam.active.is_(True)).order_by(ServiceTeam.id)))
    building_groups: dict[int, list[int]] = {}
    for index, item in enumerate(parsed_items):
        building_groups.setdefault(item.building_number, []).append(index)
    team_workloads = {team.id: 0 for team in active_teams}
    provisional_team_by_item: dict[int, ServiceTeam] = {}
    tie_cursor = 0
    for building_number in sorted(building_groups):
        if not active_teams:
            break
        lowest_workload = min(team_workloads.values())
        candidates = [team for team in active_teams if team_workloads[team.id] == lowest_workload]
        assigned_team = candidates[tie_cursor % len(candidates)]
        tie_cursor += 1
        for item_index in building_groups[building_number]:
            provisional_team_by_item[item_index] = assigned_team
        team_workloads[assigned_team.id] += len(building_groups[building_number])
    location_counts: dict[tuple[int, str], int] = {}
    for item in parsed_items:
        key = (item.building_number, item.unit_number)
        location_counts[key] = location_counts.get(key, 0) + 1
    location_occurrences: dict[tuple[int, str], int] = {}
    for item_index, item in enumerate(parsed_items):
        assigned_team = provisional_team_by_item.get(item_index)
        location_key = (item.building_number, item.unit_number)
        location_occurrences[location_key] = location_occurrences.get(location_key, 0) + 1
        occurrence_suffix = (
            f"_{location_occurrences[location_key]}"
            if location_counts[location_key] > 1
            else ""
        )
        provisional_customer = f"Client_B{item.building_number}_U{item.unit_number}{occurrence_suffix}"
        notes = []
        if location_counts[(item.building_number, item.unit_number)] > 1:
            notes.append(REPEAT_LOCATION_WARNING)
        session.add(
            ScheduleIntakeItem(
                schedule_intake_id=intake.id,
                source_line=item.source_line,
                service_team_id=assigned_team.id if assigned_team else None,
                customer_name=item.customer_name or provisional_customer,
                customer_phone=item.customer_phone,
                customer_is_provisional=not bool(item.customer_name),
                building_number=item.building_number,
                unit_number=item.unit_number,
                raw_service_text=item.raw_service_text,
                scheduled_time=item.scheduled_time,
                price=item.price,
                review_status=item.review_status,
                review_note=" · ".join(notes) or None,
            )
        )
    intake.status = "ready" if parsed_items and all(item.review_status == "ready" for item in parsed_items) else "draft"
    session.commit()
    return RedirectResponse(url=app_path(f"/staff/schedule-intake?intake_id={intake.id}"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/schedule-intake/clear", response_class=RedirectResponse)
def clear_schedule_intakes(session: Session = Depends(get_session)) -> RedirectResponse:
    """Delete unapproved raw schedule drafts, including their draft rows."""
    session.execute(delete(ScheduleIntake).where(ScheduleIntake.status != "confirmed"))
    session.commit()
    return RedirectResponse(url=app_path("/staff/schedule-intake"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/schedule-intake/{intake_id}/approve", response_class=RedirectResponse)
def approve_schedule_intake(intake_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    """Publish reviewed intake rows to the team schedule as provisional jobs."""
    intake = session.get(ScheduleIntake, intake_id)
    if intake is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule intake not found.")
    active_items = list(
        session.scalars(
            select(ScheduleIntakeItem).where(
                ScheduleIntakeItem.schedule_intake_id == intake.id,
                ScheduleIntakeItem.review_status != "skipped",
            )
        )
    )
    if not active_items:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="There are no active rows to approve.")
    intake.status = "confirmed"
    for item in active_items:
        item.review_status = "confirmed"
        job = session.scalar(
            select(OperationalJob).where(OperationalJob.schedule_intake_item_id == item.id)
        )
        if job is None:
            job = OperationalJob(
                source="team_intake",
                schedule_intake_item_id=item.id,
                customer_id=item.customer_id,
                customer_label=item.customer_name or "Client missing",
                customer_phone=item.customer_phone,
                customer_is_provisional=item.customer_is_provisional,
                address_label=f"Building {item.building_number}, Unit {item.unit_number}",
                service_type_id=item.service_type_id,
                service_label=item.raw_service_text or "Service missing",
                service_team_id=item.service_team_id,
                scheduled_date=intake.schedule_date,
                scheduled_time=item.scheduled_time,
                price=item.price,
                status="scheduled",
            )
            session.add(job)
        session.flush()
        existing_event = session.scalar(
            select(NotificationOutbox).where(
                NotificationOutbox.operational_job_id == job.id,
                NotificationOutbox.event_type == "appointment_scheduled",
            )
        )
        if existing_event is None:
            record_operational_job_event(session, job=job)
    session.commit()
    return RedirectResponse(
        url=app_path(f"/staff/dispatch?selected_date={intake.schedule_date}&intake_published=1"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/staff/schedule-intake/items/{item_id}", response_class=RedirectResponse)
def update_schedule_intake_item(
    item_id: int,
    intake_id: int = Form(),
    service_team_id: int | None = Form(None),
    building_number: int | None = Form(None),
    unit_number: str = Form(""),
    customer_name: str = Form(""),
    customer_phone: str = Form(""),
    raw_service_text: str = Form(""),
    scheduled_time: time | None = Form(None),
    price: str = Form(""),
    review_note: str = Form(""),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Save edits to one draft row without creating operational records."""
    item = session.get(ScheduleIntakeItem, item_id)
    if item is None or item.schedule_intake_id != intake_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule draft row not found.")
    intake = session.get(ScheduleIntake, intake_id)
    if intake is not None and intake.status == "confirmed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Published intake rows cannot be edited here.")
    if building_number is not None and building_number <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Building number must be positive.")

    item.service_team_id = service_team_id
    item.building_number = building_number
    item.unit_number = unit_number.strip() or None
    submitted_customer_name = customer_name.strip()
    item.customer_is_provisional = bool(
        item.customer_is_provisional and submitted_customer_name == item.customer_name
    )
    item.customer_name = submitted_customer_name or None
    item.customer_phone = customer_phone.strip() or None
    item.raw_service_text = raw_service_text.strip() or None
    item.scheduled_time = scheduled_time
    item.price = None
    if price.strip():
        try:
            from decimal import Decimal
            item.price = Decimal(price.strip())
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Price must be a valid number.") from error
    matching_active_items = session.scalar(
        select(func.count())
        .select_from(ScheduleIntakeItem)
        .where(
            ScheduleIntakeItem.schedule_intake_id == intake_id,
            ScheduleIntakeItem.id != item.id,
            ScheduleIntakeItem.review_status != "skipped",
            ScheduleIntakeItem.building_number == item.building_number,
            ScheduleIntakeItem.unit_number == item.unit_number,
        )
    ) or 0
    has_repeat_warning = matching_active_items > 0
    notes = []
    staff_alert = important_staff_note(review_note)
    if staff_alert:
        notes.append(staff_alert)
    if has_repeat_warning:
        notes.append(REPEAT_LOCATION_WARNING)
    item.review_note = " · ".join(notes) or None
    item.review_status = "ready" if all((item.service_team_id, item.customer_name, item.building_number, item.unit_number, item.raw_service_text, item.scheduled_time)) and not item.customer_is_provisional and not has_repeat_warning else "needs_review"
    session.commit()
    return RedirectResponse(url=app_path(f"/staff/schedule-intake?intake_id={intake_id}"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/staff/schedule-intake/items/{item_id}/skip", response_class=RedirectResponse)
def skip_schedule_intake_item(
    item_id: int,
    intake_id: int = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Mark one draft row skipped while preserving the raw intake history."""
    item = session.get(ScheduleIntakeItem, item_id)
    if item is None or item.schedule_intake_id != intake_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule draft row not found.")
    intake = session.get(ScheduleIntake, intake_id)
    if intake is not None and intake.status == "confirmed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Published intake rows cannot be skipped here.")
    item.review_status = "skipped"
    item.review_note = "Skipped by staff" if not item.review_note else f"Skipped by staff · {item.review_note}"
    session.commit()
    return RedirectResponse(url=app_path(f"/staff/schedule-intake?intake_id={intake_id}"), status_code=status.HTTP_303_SEE_OTHER)


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
    staff_note: str = Form(default=""),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Record a local team-progress update without sending any message."""
    try:
        if next_status == "completed_now":
            appointment = complete_appointment_shortcut(session, appointment_id)
        else:
            appointment = update_appointment_status(session, appointment_id, next_status, staff_note=staff_note)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    selected_date = appointment.scheduled_start.astimezone(MANILA_TIMEZONE).date()
    return RedirectResponse(
        url=app_path(f"/staff/dispatch?selected_date={selected_date}&job_updated={appointment.status}"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/staff/appointments/{appointment_id}/notes")
def add_appointment_note(
    appointment_id: int,
    note: str = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    appointment = session.get(Appointment, appointment_id)
    cleaned_note = note.strip()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The scheduled appointment does not exist.")
    if not cleaned_note:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="An internal note is required.")
    session.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=appointment.status,
            to_status=appointment.status,
            actor_type="local_staff",
            note=f"Internal note: {cleaned_note}",
        )
    )
    session.commit()
    return RedirectResponse(
        url=app_path(f"/staff/appointments/{appointment.id}"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/staff/appointments/{appointment_id}/reschedule")
def reschedule_scheduled_job(
    appointment_id: int,
    appointment_date: date = Form(),
    slot_key: str = Form(),
    service_team_id: int = Form(),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Move a confirmed appointment to another open team time block."""
    try:
        appointment = reschedule_appointment(
            session,
            appointment_id=appointment_id,
            appointment_date=appointment_date,
            slot_key=slot_key,
            service_team_id=service_team_id,
        )
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    selected_date = appointment.scheduled_start.astimezone(MANILA_TIMEZONE).date()
    return RedirectResponse(
        url=app_path(f"/staff/dispatch?selected_date={selected_date}&scheduled=1"),
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
    event_status: str = "",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Show local-only automation events; no external workflow is connected."""
    event_statement = select(NotificationOutbox).order_by(NotificationOutbox.id.desc())
    if event_status:
        event_statement = event_statement.where(NotificationOutbox.status == event_status)
    events = list(session.scalars(event_statement.limit(200)).all())
    event_counts = {
        value: session.scalar(
            select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == value)
        ) or 0
        for value in ("pending", "recorded", "failed")
    }
    reporting_health = automation_health(session)
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
            "event_status_filter": event_status,
            "event_counts": event_counts,
            "automatic_delivery_enabled": automatic_delivery_enabled(),
            "reporting_health": reporting_health,
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
    """Run the local-only simulation action when prototype mode is enabled."""
    if is_live_mode():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local simulation is disabled in live owner-reporting mode.")
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
    """Send exactly one owner-reporting outbox event to the protected n8n webhook."""
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


@app.post("/staff/automation/events/{event_id}/requeue")
def requeue_automation_event(event_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    """Return a failed owner-reporting event to the automatic-delivery queue."""
    event = session.get(NotificationOutbox, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The automation event does not exist.")
    if event.status != "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed events can be requeued.")
    event.status = "pending"
    event.claimed_at = None
    event.next_attempt_at = None
    event.last_error = None
    session.commit()
    return RedirectResponse(url=app_path("/staff/automation?event_status=pending"), status_code=status.HTTP_303_SEE_OTHER)


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
    active_teams = list(session.scalars(select(ServiceTeam).where(ServiceTeam.active.is_(True)).order_by(ServiceTeam.name)).all())
    return {
        "appointment": appointment,
        "booking": booking,
        "customer": customer,
        "address": address,
        "address_display": display_address(address),
        "team": team,
        "active_teams": active_teams,
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
    submission_mode: str = Form(default="normal"),
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

    availability = booking_date_availability(session, booking_input.preferred_date)
    if submission_mode not in {"normal", "waitlist"}:
        submission_mode = "normal"
    if availability["fully_booked"] and submission_mode == "normal":
        return render_booking_form(
            request,
            session,
            values=values,
            errors={"preferred_date": "This date is fully booked. Choose another date or request the waitlist."},
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        booking = create_pending_booking(
            session,
            booking_input,
            initial_status="waitlisted" if submission_mode == "waitlist" else "pending_review",
        )
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
        {
            "reference_code": booking.reference_code,
            "status": booking.status,
            "waitlisted": booking.status == "waitlisted",
            "preferred_date": booking.preferred_date,
        },
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
