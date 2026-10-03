"""Controlled persistence for validated booking requests."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.booking.validation import BookingRequestInput
from app.core.project_info import is_live_mode
from app.database.models import (
    Address,
    Appointment,
    AppointmentStatusHistory,
    BookingRequest,
    BookingRequestStatusHistory,
    Customer,
    NotificationOutbox,
    ServiceTeam,
    ServiceType,
    TeamMembership,
    Technician,
)


MANILA_TIMEZONE = ZoneInfo("Asia/Manila")
DISPATCH_SLOTS: dict[str, tuple[str, time, time]] = {
    "09:00": ("09:00-11:00", time(9, 0), time(11, 0)),
    "11:30": ("11:30-13:30", time(11, 30), time(13, 30)),
    "14:00": ("14:00-16:00", time(14, 0), time(16, 0)),
}

APPOINTMENT_STATUS_TRANSITIONS: dict[str, dict[str, str]] = {
    "confirmed": {
        "en_route": "Team marked en route in the local dispatcher board; no customer message sent.",
        "cancelled": "Appointment cancelled in the local dispatcher board; no customer message sent.",
    },
    "en_route": {
        "in_progress": "Team marked on site and work in progress in the local dispatcher board; no customer message sent.",
        "cancelled": "Appointment cancelled in the local dispatcher board; no customer message sent.",
    },
    "in_progress": {
        "completed": "Work marked completed in the local dispatcher board; no customer message sent.",
        "cancelled": "Appointment cancelled in the local dispatcher board; no customer message sent.",
    },
}
OUTBOX_CLAIM_LEASE = timedelta(minutes=5)
AUTOMATIC_DELIVERY_ENVIRONMENT_VARIABLE = "AIRCON_AUTOMATIC_DELIVERY_ENABLED"


def automatic_delivery_enabled() -> bool:
    """Return whether a future automatic delivery worker is explicitly enabled."""
    return os.getenv(AUTOMATIC_DELIVERY_ENVIRONMENT_VARIABLE, "").strip().lower() == "true"


def next_retry_time(*, attempt_count: int, now: datetime | None = None) -> datetime:
    """Calculate a bounded retry delay for a future automatic worker."""
    retry_base = now or datetime.now(UTC)
    delay_minutes = min(2 ** max(attempt_count - 1, 0), 30)
    return retry_base + timedelta(minutes=delay_minutes)


def due_outbox_event_count(session: Session, *, now: datetime | None = None) -> int:
    """Count unclaimed pending events that a future worker may consider."""
    check_time = now or datetime.now(UTC)
    stale_claim_before = check_time - OUTBOX_CLAIM_LEASE
    return session.scalar(
        select(func.count())
        .select_from(NotificationOutbox)
        .where(
            NotificationOutbox.status == "pending",
            or_(
                NotificationOutbox.next_attempt_at.is_(None),
                NotificationOutbox.next_attempt_at <= check_time,
            ),
            or_(
                NotificationOutbox.claimed_at.is_(None),
                NotificationOutbox.claimed_at <= stale_claim_before,
            ),
        )
    ) or 0


def run_due_delivery_worker_check(session: Session, *, now: datetime | None = None) -> tuple[str, int]:
    """Safely inspect the future delivery queue without sending an event.

    This remains a no-send worker check even if the feature flag is enabled.
    A real background sender requires the separate security and publishing gate.
    """
    due_events = due_outbox_event_count(session, now=now)
    if not automatic_delivery_enabled():
        return "disabled", due_events
    return "approval_required", due_events


def generate_reference_code() -> str:
    """Generate a customer-safe reference without exposing an internal ID."""
    return f"AC-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"


def masked_mobile(mobile: str) -> str:
    """Keep automation evidence useful without displaying a full phone number."""
    return f"{mobile[:4]}****{mobile[-3:]}" if len(mobile) >= 7 else "masked"


def owner_phone(mobile: str) -> str:
    """Return the owner-reporting phone according to the explicit runtime mode."""
    return mobile if is_live_mode() else masked_mobile(mobile)


def display_address(address: Address) -> str:
    """Build a readable address without repeating a barangay in the coverage label."""
    coverage_area = address.coverage_area or ""
    barangay_prefix = f"{address.barangay},"
    if address.barangay and coverage_area.casefold().startswith(barangay_prefix.casefold()):
        coverage_area = coverage_area[len(barangay_prefix):].strip()
    return ", ".join(value for value in (address.address_line, address.barangay, address.city, coverage_area) if value)


def record_simulated_event(
    session: Session,
    *,
    booking: BookingRequest,
    customer: Customer,
    event_type: str,
    note: str,
) -> NotificationOutbox:
    """Place a local-only event in the outbox for later n8n simulation."""
    event = NotificationOutbox(
        booking_request_id=booking.id,
        event_type=event_type,
        # The local outbox remains simulation-only in every mode.  Live mode
        # means owner reporting through the payload/n8n workflow; it must not
        # turn this local record into a customer-delivery channel.
        channel="simulated",
        recipient_masked=masked_mobile(customer.mobile),
        status="pending",
        payload={
            "mode": "live_owner_reporting" if is_live_mode() else "synthetic_only",
            "booking_reference": booking.reference_code,
            "note": note,
        },
    )
    session.add(event)
    session.flush()
    return event


def process_pending_simulated_events(session: Session) -> int:
    """Record pending outbox events as locally processed; never deliver a message."""
    events = list(session.scalars(select(NotificationOutbox).where(NotificationOutbox.status == "pending")).all())
    for event in events:
        event.status = "recorded"
    session.flush()
    return len(events)


def outbox_idempotency_key(event: NotificationOutbox) -> str:
    """Return the stable future-delivery identity for one local outbox event."""
    if event.id is None:
        raise ValueError("the outbox event must be saved before it receives an idempotency key")
    prefix = "outbox" if is_live_mode() else "synthetic-outbox"
    return f"{prefix}-{event.id}"


def claim_next_eligible_outbox_event(
    session: Session,
    *,
    now: datetime | None = None,
    ignore_retry_schedule: bool = False,
) -> NotificationOutbox | None:
    """Reserve one retry-eligible event for a future delivery worker.

    The lease prevents another worker from selecting the event for five minutes.
    This function is local-only; it does not contact n8n or send any message.
    """
    claimed_at = now or datetime.now(UTC)
    stale_claim_before = claimed_at - OUTBOX_CLAIM_LEASE
    conditions = [
        NotificationOutbox.status == "pending",
        or_(
            NotificationOutbox.claimed_at.is_(None),
            NotificationOutbox.claimed_at <= stale_claim_before,
        ),
    ]
    if not ignore_retry_schedule:
        conditions.append(
            or_(
                NotificationOutbox.next_attempt_at.is_(None),
                NotificationOutbox.next_attempt_at <= claimed_at,
            )
        )
    event = session.scalar(
        select(NotificationOutbox)
        .where(*conditions)
        .order_by(NotificationOutbox.created_at.asc(), NotificationOutbox.id.asc())
        .with_for_update(skip_locked=True)
    )
    if event is None:
        return None

    event.claimed_at = claimed_at
    event.attempt_count = (event.attempt_count or 0) + 1
    session.flush()
    return event


def record_delivery_success(event: NotificationOutbox, result: dict[str, object]) -> None:
    """Record a successful owner-reporting delivery and release its claim."""
    event.status = "recorded"
    event.claimed_at = None
    event.last_error = None
    event.next_attempt_at = None
    if result.get("dispatcher_message"):
        event.payload = {
            **event.payload,
            "dispatcher_message": result["dispatcher_message"],
        }


def record_retryable_delivery_failure(
    event: NotificationOutbox,
    error_message: str,
    *,
    next_attempt_at: datetime | None = None,
) -> None:
    """Keep an event pending after a temporary delivery failure."""
    event.status = "pending"
    event.claimed_at = None
    event.last_error = error_message
    event.next_attempt_at = next_attempt_at


def record_permanent_delivery_rejection(event: NotificationOutbox, rejection_reason: str) -> None:
    """Stop retries after n8n explicitly rejects an event."""
    event.status = "failed"
    event.claimed_at = None
    event.last_error = rejection_reason
    event.next_attempt_at = None
    event.payload = {
        **event.payload,
        "n8n_rejection_reason": rejection_reason,
    }


def n8n_event_payload(session: Session, event: NotificationOutbox) -> dict[str, object]:
    """Convert one outbox row and its booking records into the owner-reporting payload."""
    booking = session.get(BookingRequest, event.booking_request_id)
    if booking is None:
        raise ValueError("the outbox booking request does not exist")
    customer = session.get(Customer, booking.customer_id)
    address = session.get(Address, booking.address_id)
    service_type = session.get(ServiceType, booking.service_type_id)
    appointment = session.scalar(
        select(Appointment).where(Appointment.booking_request_id == booking.id)
    )
    team = session.get(ServiceTeam, appointment.service_team_id) if appointment else None
    technician = session.get(Technician, appointment.technician_id) if appointment else None
    if customer is None or address is None or service_type is None:
        raise ValueError("the outbox booking records are incomplete")

    local_scheduled_start = appointment.scheduled_start.astimezone(MANILA_TIMEZONE) if appointment else None
    local_scheduled_end = appointment.scheduled_end.astimezone(MANILA_TIMEZONE) if appointment else None
    scheduled_start = local_scheduled_start.isoformat() if local_scheduled_start else None
    scheduled_end = local_scheduled_end.isoformat() if local_scheduled_end else None
    live_mode = is_live_mode()
    occurred_at = event.created_at or datetime.now(UTC)
    local_occurred_at = occurred_at.astimezone(MANILA_TIMEZONE)
    address_display = display_address(address)
    return {
        "event_id": f"outbox-{event.id}" if live_mode else f"synthetic-outbox-{event.id}",
        "idempotency_key": outbox_idempotency_key(event),
        "event_type": event.event_type,
        # Keep the legacy outbox status while consumers migrate to the nested
        # delivery object.
        "status": event.status,
        "occurred_at": occurred_at.isoformat(),
        "occurred_at_display": f"{local_occurred_at:%b} {local_occurred_at.day}, {local_occurred_at:%Y}, {local_occurred_at:%I:%M %p}".replace(" 0", " ", 1),
        "booking_reference": booking.reference_code,
        "booking_status": booking.status,
        "appointment_status": appointment.status if appointment else None,
        "synthetic_only": not live_mode,
        "operation_mode": "live_owner_reporting" if live_mode else "synthetic_only",
        "client": {
            "name": customer.full_name,
            "phone": owner_phone(customer.mobile),
            "phone_masked": masked_mobile(customer.mobile),
            "email": customer.email,
        },
        "service": {
            "name": service_type.name,
            "aircon_type": booking.aircon_type,
            "unit_count": booking.unit_count,
        },
        "location": {
            "address_line": address.address_line,
            "display": address_display,
            "barangay": address.barangay,
            "city": address.city,
            "coverage_area": address.coverage_area,
        },
        "schedule": {
            "preferred_date": booking.preferred_date.isoformat(),
            "scheduled_date": local_scheduled_start.date().isoformat() if local_scheduled_start else None,
            "preferred_window": booking.preferred_window,
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
            "time_window": f"{local_scheduled_start:%H:%M}-{local_scheduled_end:%H:%M}" if local_scheduled_start and local_scheduled_end else None,
            "team": team.name if team else None,
            "technician": technician.display_name if technician else None,
        },
        "delivery": {
            "outbox_status": event.status,
            "attempt_count": event.attempt_count,
            "last_error": event.last_error,
            "next_attempt_at": event.next_attempt_at.isoformat() if event.next_attempt_at else None,
        },
    }


def push_one_pending_event_to_n8n(
    session: Session,
    *,
    ignore_retry_schedule: bool = True,
) -> NotificationOutbox:
    """Send one claimed owner-reporting event to the configured n8n webhook."""
    webhook_url = os.getenv("AIRCON_N8N_WEBHOOK_URL")
    webhook_key = os.getenv("AIRCON_N8N_WEBHOOK_KEY")
    if not webhook_url or not webhook_key:
        raise ValueError("n8n delivery is disabled; set AIRCON_N8N_WEBHOOK_URL and AIRCON_N8N_WEBHOOK_KEY for this terminal session")
    if not webhook_url.startswith("https://"):
        raise ValueError("the n8n webhook URL must use HTTPS")

    event = claim_next_eligible_outbox_event(session, ignore_retry_schedule=ignore_retry_schedule)
    if event is None:
        raise ValueError("no pending automation event is available")

    request = Request(
        webhook_url,
        data=json.dumps(n8n_event_payload(session, event)).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Aircon-Webhook-Key": webhook_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                record_retryable_delivery_failure(
                    event,
                    f"n8n returned HTTP {response.status}",
                    next_attempt_at=next_retry_time(attempt_count=event.attempt_count),
                )
                session.flush()
                return event
            try:
                result = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                record_retryable_delivery_failure(
                    event,
                    "n8n returned an invalid JSON response",
                    next_attempt_at=next_retry_time(attempt_count=event.attempt_count),
                )
                session.flush()
                return event
    except HTTPError as error:
        record_retryable_delivery_failure(
            event,
            f"n8n rejected the event with HTTP {error.code}",
            next_attempt_at=next_retry_time(attempt_count=event.attempt_count),
        )
        session.flush()
        return event
    except (URLError, TimeoutError) as error:
        record_retryable_delivery_failure(
            event,
            "the n8n webhook could not be reached",
            next_attempt_at=next_retry_time(attempt_count=event.attempt_count),
        )
        session.flush()
        return event

    if not isinstance(result, dict):
        record_retryable_delivery_failure(
            event,
            "n8n returned an unexpected response shape",
            next_attempt_at=next_retry_time(attempt_count=event.attempt_count),
        )
        session.flush()
        return event
    automation_status = result.get("automation_status")
    if automation_status == "processed":
        record_delivery_success(event, result)
    elif automation_status == "rejected":
        record_permanent_delivery_rejection(event, str(result.get("rejection_reason", "n8n rejected the event")))
    else:
        record_retryable_delivery_failure(
            event,
            "n8n returned an unexpected automation status",
            next_attempt_at=next_retry_time(attempt_count=event.attempt_count),
        )
    session.flush()
    return event


def run_automatic_delivery_worker(session: Session) -> NotificationOutbox | None:
    """Deliver one due event when automatic delivery is explicitly enabled."""
    if not automatic_delivery_enabled():
        return None
    if due_outbox_event_count(session) == 0:
        return None
    return push_one_pending_event_to_n8n(session, ignore_retry_schedule=False)


def create_pending_booking(
    session: Session,
    booking_input: BookingRequestInput,
    *,
    reference_code: str | None = None,
) -> BookingRequest:
    """Create the records for a validated request without committing the session.

    The caller owns the transaction. This makes the operation testable and lets
    the web layer decide when a successful request is committed.
    """
    service_type = session.scalar(
        select(ServiceType).where(
            ServiceType.id == booking_input.service_type_id,
            ServiceType.active.is_(True),
        )
    )
    if service_type is None:
        raise ValueError("the selected service type is unavailable")

    customer = session.scalar(select(Customer).where(Customer.mobile == booking_input.mobile))
    if customer is None:
        customer = Customer(
            full_name=booking_input.full_name,
            mobile=booking_input.mobile,
            email=booking_input.email,
        )
        session.add(customer)
        session.flush()

    existing_booking = session.scalar(
        select(BookingRequest)
        .join(Address, BookingRequest.address_id == Address.id)
        .where(
            BookingRequest.customer_id == customer.id,
            BookingRequest.service_type_id == service_type.id,
            BookingRequest.aircon_type == booking_input.aircon_type,
            BookingRequest.preferred_date == booking_input.preferred_date,
            BookingRequest.preferred_window == booking_input.preferred_window,
            BookingRequest.status != "cancelled",
            Address.address_line == booking_input.address_line,
            Address.barangay == booking_input.barangay,
            Address.city == booking_input.city,
            Address.coverage_area == booking_input.coverage_area,
        )
        .order_by(BookingRequest.id.desc())
    )
    if existing_booking is not None:
        return existing_booking

    address = Address(
        customer_id=customer.id,
        address_line=booking_input.address_line,
        barangay=booking_input.barangay,
        city=booking_input.city,
        coverage_area=booking_input.coverage_area,
        service_area_valid=True,
    )
    session.add(address)
    session.flush()

    booking = BookingRequest(
        reference_code=reference_code or generate_reference_code(),
        customer_id=customer.id,
        address_id=address.id,
        service_type_id=service_type.id,
        aircon_type=booking_input.aircon_type,
        preferred_date=booking_input.preferred_date,
        preferred_window=booking_input.preferred_window,
        unit_count=booking_input.unit_count,
        notes=booking_input.notes,
        status="pending_review",
    )
    session.add(booking)
    session.flush()
    return booking


def review_booking_request(session: Session, booking_request_id: int, decision: str) -> BookingRequest:
    """Record one local-staff review decision without creating an appointment."""
    booking = session.get(BookingRequest, booking_request_id)
    if booking is None:
        raise ValueError("the booking request does not exist")
    if booking.status != "pending_review":
        raise ValueError("only pending requests can be reviewed")

    transitions = {
        "approve": ("approved_for_scheduling", "Approved in local staff queue; no appointment created."),
        "decline": ("cancelled", "Declined in local staff queue; no appointment created."),
    }
    if decision not in transitions:
        raise ValueError("the review decision is invalid")

    next_status, note = transitions[decision]
    previous_status = booking.status
    booking.status = next_status
    session.add(
        BookingRequestStatusHistory(
            booking_request_id=booking.id,
            from_status=previous_status,
            to_status=next_status,
            actor_type="local_staff",
            note=note,
        )
    )
    session.flush()
    return booking


def schedule_approved_booking(
    session: Session,
    *,
    booking_request_id: int,
    service_team_id: int,
    appointment_date: date,
    slot_key: str,
) -> Appointment:
    """Assign an approved request to one fixed team/time block without sending messages."""
    booking = session.get(BookingRequest, booking_request_id)
    if booking is None:
        raise ValueError("the booking request does not exist")
    if booking.status != "approved_for_scheduling":
        raise ValueError("only approved requests can be scheduled")
    if appointment_date < datetime.now(MANILA_TIMEZONE).date():
        raise ValueError("appointments cannot be scheduled in the past")
    if appointment_date != booking.preferred_date:
        raise ValueError(f"choose the customer's preferred date: {booking.preferred_date}")

    team = session.get(ServiceTeam, service_team_id)
    if team is None or not team.active:
        raise ValueError("the selected service team is unavailable")
    if slot_key not in DISPATCH_SLOTS:
        raise ValueError("the selected time block is invalid")

    lead_membership = session.scalar(
        select(TeamMembership).where(
            TeamMembership.service_team_id == team.id,
            TeamMembership.is_lead.is_(True),
        )
    )
    if lead_membership is None:
        raise ValueError("the selected service team has no lead technician")

    _, start_time, end_time = DISPATCH_SLOTS[slot_key]
    scheduled_start = datetime.combine(appointment_date, start_time, tzinfo=MANILA_TIMEZONE)
    scheduled_end = datetime.combine(appointment_date, end_time, tzinfo=MANILA_TIMEZONE)
    existing = session.scalar(
        select(Appointment).where(
            Appointment.service_team_id == team.id,
            Appointment.scheduled_start == scheduled_start,
        )
    )
    if existing is not None:
        raise ValueError("that team time block is already assigned")

    appointment = Appointment(
        booking_request_id=booking.id,
        service_team_id=team.id,
        technician_id=lead_membership.technician_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status="confirmed",
    )
    previous_status = booking.status
    booking.status = "scheduled"
    session.add(appointment)
    session.flush()
    session.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=None,
            to_status="confirmed",
            actor_type="local_staff",
            note="Scheduled in the local dispatcher board; no customer message sent.",
        )
    )
    session.add(
        BookingRequestStatusHistory(
            booking_request_id=booking.id,
            from_status=previous_status,
            to_status="scheduled",
            actor_type="local_staff",
            note=f"Assigned to {team.name} for {DISPATCH_SLOTS[slot_key][0]}; no message sent.",
        )
    )
    customer = session.get(Customer, booking.customer_id)
    if customer is None:
        raise ValueError("the booking customer does not exist")
    record_simulated_event(
        session,
        booking=booking,
        customer=customer,
        event_type="appointment_scheduled",
        note=f"Appointment scheduled for {DISPATCH_SLOTS[slot_key][0]}; simulated only.",
    )
    session.flush()
    return appointment


def reschedule_appointment(
    session: Session,
    *,
    appointment_id: int,
    appointment_date: date,
    slot_key: str,
    service_team_id: int | None = None,
) -> Appointment:
    """Move a confirmed appointment while preserving its audit trail."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise ValueError("the scheduled appointment does not exist")
    if appointment.status != "confirmed":
        raise ValueError("only confirmed appointments can be rescheduled")
    if appointment_date < datetime.now(MANILA_TIMEZONE).date():
        raise ValueError("appointments cannot be rescheduled into the past")
    if slot_key not in DISPATCH_SLOTS:
        raise ValueError("the selected time block is invalid")

    target_team_id = service_team_id or appointment.service_team_id
    target_team = session.get(ServiceTeam, target_team_id)
    if target_team is None or not target_team.active:
        raise ValueError("the selected service team is not active")
    target_lead = session.scalar(
        select(Technician)
        .join(TeamMembership, TeamMembership.technician_id == Technician.id)
        .where(
            TeamMembership.service_team_id == target_team.id,
            TeamMembership.is_lead.is_(True),
            Technician.active.is_(True),
        )
    )
    if target_lead is None:
        raise ValueError("the selected service team does not have an active team lead")

    _, start_time, end_time = DISPATCH_SLOTS[slot_key]
    scheduled_start = datetime.combine(appointment_date, start_time, tzinfo=MANILA_TIMEZONE)
    scheduled_end = datetime.combine(appointment_date, end_time, tzinfo=MANILA_TIMEZONE)
    existing = session.scalar(
        select(Appointment).where(
            Appointment.service_team_id == target_team.id,
            Appointment.scheduled_start == scheduled_start,
            Appointment.id != appointment.id,
        )
    )
    if existing is not None:
        raise ValueError("that team time block is already assigned")

    previous_team = session.get(ServiceTeam, appointment.service_team_id)
    previous_team_name = previous_team.name if previous_team else f"team {appointment.service_team_id}"
    previous_start = appointment.scheduled_start.astimezone(MANILA_TIMEZONE)
    previous_end = appointment.scheduled_end.astimezone(MANILA_TIMEZONE)
    appointment.scheduled_start = scheduled_start
    appointment.scheduled_end = scheduled_end
    appointment.service_team_id = target_team.id
    appointment.technician_id = target_lead.id
    session.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status="confirmed",
            to_status="confirmed",
            actor_type="local_staff",
            note=(
                f"Rescheduled from {previous_team_name}, {previous_start:%Y-%m-%d %H:%M}-{previous_end:%H:%M} "
                f"to {target_team.name}, {scheduled_start:%Y-%m-%d %H:%M}-{scheduled_end:%H:%M}; "
                "no customer message sent."
            ),
        )
    )
    booking = session.get(BookingRequest, appointment.booking_request_id)
    customer = session.get(Customer, booking.customer_id) if booking else None
    if booking is None or customer is None:
        raise ValueError("the appointment booking records are incomplete")
    record_simulated_event(
        session,
        booking=booking,
        customer=customer,
        event_type="appointment_rescheduled",
        note="Appointment rescheduled in the local dispatcher board; no customer message sent.",
    )
    session.flush()
    return appointment


def update_appointment_status(
    session: Session,
    appointment_id: int,
    next_status: str,
    *,
    staff_note: str | None = None,
) -> Appointment:
    """Advance or cancel a scheduled job through the local staff workflow only."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise ValueError("the scheduled appointment does not exist")

    allowed_transitions = APPOINTMENT_STATUS_TRANSITIONS.get(appointment.status, {})
    if next_status not in allowed_transitions:
        raise ValueError(f"the appointment cannot move from {appointment.status} to {next_status}")
    cleaned_note = (staff_note or "").strip()
    if next_status == "cancelled" and not cleaned_note:
        raise ValueError("a cancellation reason is required")

    previous_status = appointment.status
    appointment.status = next_status
    session.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=previous_status,
            to_status=next_status,
            actor_type="local_staff",
            note=(
                f"{allowed_transitions[next_status]} Staff note: {cleaned_note}"
                if cleaned_note
                else allowed_transitions[next_status]
            ),
        )
    )
    booking = session.get(BookingRequest, appointment.booking_request_id)
    if booking is None:
        raise ValueError("the appointment booking request does not exist")
    customer = session.get(Customer, booking.customer_id)
    if customer is None:
        raise ValueError("the appointment customer does not exist")
    record_simulated_event(
        session,
        booking=booking,
        customer=customer,
        event_type=f"appointment_{next_status}",
        note=f"Appointment changed from {previous_status} to {next_status}; simulated only.",
    )
    session.flush()
    return appointment


def complete_appointment_shortcut(session: Session, appointment_id: int) -> Appointment:
    """Complete a confirmed job in one staff action while preserving every transition."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise ValueError("the scheduled appointment does not exist")
    if appointment.status != "confirmed":
        raise ValueError("the complete-job shortcut is available only from confirmed")

    for next_status in ("en_route", "in_progress", "completed"):
        appointment = update_appointment_status(session, appointment_id, next_status)
    return appointment
