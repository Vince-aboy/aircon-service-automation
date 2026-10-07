"""Deterministic parsing for the first schedule-intake workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal
import re


LOCATION_PATTERN = re.compile(r"\b(?:b|bldg|building)\s*(\d+)\s*,?\s*(?:unit\s*)?(\d+)\b", re.IGNORECASE)
DASH_LOCATION_PATTERN = re.compile(r"^\s*(?:b(?:ldg)?\s*)?(\d{1,2})\s*[-/]\s*(\d{1,5})\b", re.IGNORECASE)
TIME_PATTERN = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"^₱?\s*\d+(?:\.\d{2})?$")
SERVICE_PATTERN = re.compile(r"cleaning|drainpan|check\s*up|checkup|greasetrap|back\s*job", re.IGNORECASE)
WEEKDAY_PREFIX_PATTERN = re.compile(r"^(?:mon|monday|tue|tuesday|wed|wednesday|thu|thursday|fri|friday|sat|saturday|sun|sunday)\s+", re.IGNORECASE)


@dataclass
class ParsedScheduleItem:
    source_line: str
    building_number: int
    unit_number: str
    raw_service_text: str | None = None
    scheduled_time: time | None = None
    price: Decimal | None = None

    @property
    def review_status(self) -> str:
        # Team and customer are intentionally empty at intake time. A row
        # cannot be ready until staff completes those review fields.
        return "needs_review"


def normalize_service(value: str) -> str | None:
    """Map common informal service wording to a clean review label."""
    cleaned = WEEKDAY_PREFIX_PATTERN.sub("", value.strip())
    lowered = cleaned.lower()
    if re.search(r"kuha(?:in)?\s+(?:ng\s+)?ac|pull\s*-?\s*out|collection", lowered):
        return "AC pull-out / collection"
    if re.search(r"\bpvc\b", lowered):
        return "PVC work"
    if "replace" in lowered and re.search(r"a?ac|aircon|ac", lowered):
        return "AC replacement"
    if "drainpan" in lowered or "drainpab" in lowered:
        return "Drainpan check / repair" if "check" in lowered else "Drainpan leak"
    if "check" in lowered and ("back job" in lowered or "backjob" in lowered):
        return "Check-up / back job"
    if "check" in lowered and ("ac" in lowered or "aircon" in lowered):
        return "AC check-up"
    if "greasetrap" in lowered and "cleaning" in lowered:
        return "Greasetrap + AC cleaning"
    if "greasetrap" in lowered:
        return "Greasetrap"
    if re.search(r"clean\w*", lowered):
        return "AC cleaning"
    return None


def parse_clock(value: str) -> time | None:
    match = TIME_PATTERN.match(value.strip())
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or "00")
    meridiem = (match.group(3) or "").lower()
    # Informal daytime schedules often omit AM/PM. Treat 1:00–6:59 as PM;
    # the row remains a draft for staff review before confirmation.
    if not meridiem and 1 <= hour <= 6:
        meridiem = "pm"
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def parse_raw_schedule(raw_message: str) -> list[ParsedScheduleItem]:
    lines = [line.strip() for line in raw_message.splitlines() if line.strip()]
    parsed: list[ParsedScheduleItem] = []
    current: ParsedScheduleItem | None = None

    for line in lines:
        location = LOCATION_PATTERN.search(line) or DASH_LOCATION_PATTERN.search(line)
        clock = parse_clock(line)
        price = line.replace("₱", "").strip() if PRICE_PATTERN.match(line) else None
        service_line = normalize_service(line)

        if location:
            if current:
                parsed.append(current)
            current = ParsedScheduleItem(
                source_line=line,
                building_number=int(location.group(1)),
                unit_number=location.group(2),
            )
            inline_service = normalize_service(line)
            if inline_service:
                current.raw_service_text = inline_service
        elif current and clock:
            current.scheduled_time = clock
            current.source_line += f"\n{line}"
        elif current and price is not None:
            current.price = Decimal(price)
            current.source_line += f"\n{line}"
        elif current and service_line:
            normalized_service = normalize_service(line)
            current.raw_service_text = (
                f"{current.raw_service_text} + {normalized_service}"
                if current.raw_service_text
                else normalized_service
            )
            current.source_line += f"\n{line}"
        elif current:
            # Keep every unrecognised instruction for staff review. It remains
            # available with the draft even when it is not a structured field.
            current.source_line += f"\n{line}"

    if current:
        parsed.append(current)
    return parsed
