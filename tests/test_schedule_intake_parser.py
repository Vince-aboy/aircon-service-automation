from datetime import time

from app.booking.schedule_intake import parse_raw_schedule
from app.main import REPEAT_LOCATION_WARNING, important_staff_note


def test_parser_handles_common_team_message_typos_and_preserves_original_lines() -> None:
    items = parse_raw_schedule(
        """B13 1234
Replace aac
Ac cleaning
Checj drainpan by
Lagyn alambre

13-673 po
Pvc
Hintayin tawag ko

B10 354
Drainpab leak
8:30 am

B12 unit 247
Ac cleanint

sa bldg 9 1146 po
Kuhain ac na binebenta

B12 536 check up ac"""
    )

    assert [(item.building_number, item.unit_number) for item in items] == [
        (13, "1234"),
        (13, "673"),
        (10, "354"),
        (12, "247"),
        (9, "1146"),
        (12, "536"),
    ]
    assert items[0].raw_service_text == "Replace aac\nAc cleaning\nChecj drainpan by\nLagyn alambre"
    assert "Lagyn alambre" in items[0].source_line
    assert items[1].raw_service_text == "Pvc\nHintayin tawag ko"
    assert "Hintayin tawag ko" in items[1].source_line
    assert items[2].raw_service_text == "Drainpab leak"
    assert items[2].scheduled_time == time(8, 30)
    assert items[3].raw_service_text == "Ac cleanint"
    assert items[4].raw_service_text == "Kuhain ac na binebenta"
    assert items[5].raw_service_text == "check up ac"


def test_parser_does_not_treat_phone_number_as_price() -> None:
    items = parse_raw_schedule(
        "B13 1242\nVincent Aboy\n09505581886\nAc cleaning-Late Additional"
    )

    assert len(items) == 1
    assert items[0].customer_name == "Vincent Aboy"
    assert items[0].customer_phone == "09505581886"
    assert items[0].price is None
    assert "09505581886" in items[0].source_line
    assert "Ac cleaning-Late Additional" in items[0].raw_service_text


def test_important_staff_note_removes_old_routine_reminders() -> None:
    old_note = (
        "Auto-assigned Team A · same-building rule · "
        "Replace Client_B3_U244 with real name · Add time · "
        f"{REPEAT_LOCATION_WARNING}"
    )

    assert important_staff_note(old_note) == ""
    assert important_staff_note(f"Call first · {REPEAT_LOCATION_WARNING}") == "Call first"
