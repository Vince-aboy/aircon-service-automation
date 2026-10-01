"""Database-level rules verified in transactions that are always rolled back."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import os

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Address, Appointment, BookingRequest, Customer, ServiceTeam, ServiceType, Technician
from app.database.session import create_database_engine


pytestmark = pytest.mark.integration


@pytest.fixture
def database_session() -> Session:
    if not os.getenv("AIRCON_DATABASE_URL"):
        pytest.skip("AIRCON_DATABASE_URL is not set; integration tests require local PostgreSQL access.")

    engine = create_database_engine()
    session = Session(engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def add_valid_booking_parents(session: Session) -> tuple[Customer, Address, ServiceType, Technician, ServiceTeam]:
    customer = Customer(full_name="Database Test Customer", mobile="09999999999")
    service_type = ServiceType(name="Database Test Service", duration_minutes=60, active=True)
    technician = Technician(display_name="Database Test Technician", active=True)
    service_team = ServiceTeam(name="Database Test Team", active=True)
    session.add_all((customer, service_type, technician, service_team))
    session.flush()

    address = Address(
        customer_id=customer.id,
        address_line="1 Test Street",
        barangay="Test Barangay",
        city="Manila",
        coverage_area="Urban Deca Homes, Tondo",
        service_area_valid=True,
    )
    session.add(address)
    session.flush()
    return customer, address, service_type, technician, service_team


def add_valid_booking(session: Session) -> tuple[BookingRequest, Technician, ServiceTeam]:
    customer, address, service_type, technician, service_team = add_valid_booking_parents(session)
    booking = BookingRequest(
        reference_code="TEST-ROLLBACK-001",
        customer_id=customer.id,
        address_id=address.id,
        service_type_id=service_type.id,
        preferred_date=date(2030, 1, 15),
        preferred_window="09:00-12:00",
        unit_count=1,
        status="scheduled",
    )
    session.add(booking)
    session.flush()
    return booking, technician, service_team


def test_database_rejects_non_positive_service_duration(database_session: Session) -> None:
    database_session.add(ServiceType(name="Invalid Duration Test", duration_minutes=0, active=True))

    with pytest.raises(IntegrityError):
        database_session.flush()


def test_database_rejects_non_positive_booking_unit_count(database_session: Session) -> None:
    customer, address, service_type, _, _ = add_valid_booking_parents(database_session)
    database_session.add(
        BookingRequest(
            reference_code="TEST-INVALID-UNITS",
            customer_id=customer.id,
            address_id=address.id,
            service_type_id=service_type.id,
            preferred_date=date(2030, 1, 15),
            preferred_window="09:00-12:00",
            unit_count=0,
            status="pending_review",
        )
    )

    with pytest.raises(IntegrityError):
        database_session.flush()


def test_database_rejects_appointment_with_invalid_time_range(database_session: Session) -> None:
    booking, technician, service_team = add_valid_booking(database_session)
    start = datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)
    database_session.add(
        Appointment(
            booking_request_id=booking.id,
            service_team_id=service_team.id,
            technician_id=technician.id,
            scheduled_start=start,
            scheduled_end=start - timedelta(minutes=30),
            status="confirmed",
        )
    )

    with pytest.raises(IntegrityError):
        database_session.flush()
