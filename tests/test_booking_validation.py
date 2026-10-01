from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.booking.validation import BookingRequestInput


def valid_payload() -> dict[str, object]:
    return {
        "full_name": "  Sample Customer  ",
        "mobile": "+63 917-123-4567",
        "email": "SAMPLE@EXAMPLE.TEST",
        "address_line": "123 Fictional Street",
        "barangay": "Sample Barangay",
        "city": "manila",
        "coverage_area": "Urban Deca Homes, Tondo",
        "aircon_type": "Window Type",
        "service_type_id": 1,
        "preferred_date": date.today() + timedelta(days=1),
        "preferred_window": "09:00-12:00",
        "unit_count": 2,
        "notes": "Synthetic test request only.",
    }


def test_valid_booking_input_is_normalized() -> None:
    request = BookingRequestInput.model_validate(valid_payload())

    assert request.full_name == "Sample Customer"
    assert request.mobile == "09171234567"
    assert request.email == "sample@example.test"
    assert request.city == "Manila"
    assert request.coverage_area == "Urban Deca Homes, Tondo"
    assert request.aircon_type == "Window Type"


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("mobile", "08171234567", "valid Philippine mobile number"),
        ("city", "Quezon City", "Manila only"),
        ("coverage_area", "Another Area", "Urban Deca Homes, Tondo"),
        ("aircon_type", "Portable Type", "Window Type"),
        ("preferred_date", date.today(), "must be in the future"),
        ("preferred_window", "16:00-19:00", "09:00-12:00"),
        ("unit_count", 0, "greater than or equal to 1"),
    ],
)
def test_invalid_booking_input_is_rejected(field: str, value: object, expected_message: str) -> None:
    payload = valid_payload()
    payload[field] = value

    with pytest.raises(ValidationError, match=expected_message):
        BookingRequestInput.model_validate(payload)


def test_unknown_fields_are_rejected() -> None:
    payload = valid_payload()
    payload["admin_override"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        BookingRequestInput.model_validate(payload)
