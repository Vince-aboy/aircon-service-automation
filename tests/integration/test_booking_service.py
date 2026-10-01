"""Controlled booking writes verified against local PostgreSQL and rolled back."""

from __future__ import annotations

from datetime import date, timedelta
import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.booking.service import create_pending_booking
from app.booking.validation import BookingRequestInput
from app.database.models import Address, BookingRequest, Customer
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


def valid_booking_input(service_type_id: int = 1) -> BookingRequestInput:
    return BookingRequestInput.model_validate(
        {
            "full_name": "Synthetic Customer",
            "mobile": "09171234567",
            "email": "synthetic.customer@example.test",
            "address_line": "123 Fictional Street",
            "barangay": "Sample Barangay",
            "city": "Manila",
            "coverage_area": "Urban Deca Homes, Tondo",
            "service_type_id": service_type_id,
            "preferred_date": date.today() + timedelta(days=1),
            "preferred_window": "09:00-12:00",
            "unit_count": 2,
            "notes": "Integration test only; rolled back.",
        }
    )


def table_count(session: Session, model: type[Customer] | type[Address] | type[BookingRequest]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_valid_booking_creates_pending_review_records(database_session: Session) -> None:
    before_counts = tuple(table_count(database_session, model) for model in (Customer, Address, BookingRequest))

    booking = create_pending_booking(
        database_session,
        valid_booking_input(),
        reference_code="AC-TEST-VALID-001",
    )

    after_counts = tuple(table_count(database_session, model) for model in (Customer, Address, BookingRequest))
    assert booking.status == "pending_review"
    assert booking.reference_code == "AC-TEST-VALID-001"
    assert after_counts == tuple(count + 1 for count in before_counts)


def test_unavailable_service_type_creates_no_partial_records(database_session: Session) -> None:
    before_counts = tuple(table_count(database_session, model) for model in (Customer, Address, BookingRequest))

    with pytest.raises(ValueError, match="service type is unavailable"):
        create_pending_booking(database_session, valid_booking_input(service_type_id=9999))

    after_counts = tuple(table_count(database_session, model) for model in (Customer, Address, BookingRequest))
    assert after_counts == before_counts
