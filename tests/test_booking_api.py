from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models import BookingRequest, Customer, ServiceType
from app.main import app, get_session


def create_test_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(ServiceType(name="Aircon Cleaning", duration_minutes=90, active=True))
    session.commit()

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app), session


def valid_payload() -> dict[str, object]:
    return {
        "full_name": "Synthetic API Customer",
        "mobile": "09171234567",
        "email": "synthetic.api@example.test",
        "address_line": "123 Fictional Street",
        "barangay": "Sample Barangay",
        "city": "Manila",
        "coverage_area": "Urban Deca Homes, Tondo",
        "aircon_type": "Window Type",
        "service_type_id": 1,
        "preferred_date": str(date.today() + timedelta(days=1)),
        "preferred_window": "09:00-12:00",
        "unit_count": 2,
        "notes": "Automated API test only.",
    }


def test_health_check_identifies_local_prototype() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "local_prototype"}


def test_valid_booking_request_returns_pending_review_receipt() -> None:
    client, session = create_test_client()
    try:
        response = client.post("/bookings", json=valid_payload())

        assert response.status_code == 201
        assert response.json()["status"] == "pending_review"
        assert response.json()["reference_code"].startswith("AC-")
        assert session.scalar(select(func.count()).select_from(Customer)) == 1
        assert session.scalar(select(func.count()).select_from(BookingRequest)) == 1
    finally:
        session.close()
        app.dependency_overrides.clear()


def test_invalid_booking_request_returns_validation_error_without_records() -> None:
    client, session = create_test_client()
    try:
        payload = valid_payload()
        payload["city"] = "Quezon City"
        response = client.post("/bookings", json=payload)

        assert response.status_code == 422
        assert session.scalar(select(func.count()).select_from(Customer)) == 0
        assert session.scalar(select(func.count()).select_from(BookingRequest)) == 0
    finally:
        session.close()
        app.dependency_overrides.clear()
