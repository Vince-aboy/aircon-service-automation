"""Input validation before any booking request can reach the database."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


PreferredWindow = Literal["09:00-12:00", "13:00-16:00"]
CoverageArea = Literal["Urban Deca Homes, Tondo"]
AirconType = Literal[
    "Window Type",
    "Split Type Wall Mounted",
    "Split Type Floor Mounted",
    "Split Type Ceiling Mounted",
    "Multi-Split Type Free Match",
    "Ceiling Cassette",
    "Ceiling Concealed Ducted Type",
    "Chilled Water Type",
    "Big Ducted Type",
    "VRF/VRV System",
]


class BookingRequestInput(BaseModel):
    """Validated customer request for the local Urban Deca Homes prototype."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=120)
    mobile: str = Field(max_length=24)
    email: Optional[str] = Field(default=None, max_length=254)
    address_line: str = Field(min_length=5, max_length=255)
    barangay: str = Field(min_length=2, max_length=100)
    city: str = Field(max_length=100)
    coverage_area: CoverageArea
    aircon_type: AirconType = "Window Type"
    service_type_id: int = Field(gt=0)
    preferred_date: date
    preferred_window: PreferredWindow
    unit_count: int = Field(ge=1, le=10)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("mobile")
    @classmethod
    def normalize_philippine_mobile(cls, value: str) -> str:
        normalized = value.replace(" ", "").replace("-", "")
        if normalized.startswith("+63"):
            normalized = "0" + normalized[3:]
        if not re.fullmatch(r"09\d{9}", normalized):
            raise ValueError("mobile must be a valid Philippine mobile number")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        normalized = value.lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("email must be valid when supplied")
        return normalized

    @field_validator("city")
    @classmethod
    def restrict_to_manila(cls, value: str) -> str:
        if value.casefold() != "manila":
            raise ValueError("the prototype currently serves Manila only")
        return "Manila"

    @field_validator("preferred_date")
    @classmethod
    def require_future_preferred_date(cls, value: date) -> date:
        if value <= date.today():
            raise ValueError("preferred_date must be in the future")
        return value
