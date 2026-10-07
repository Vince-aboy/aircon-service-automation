from datetime import time

from app.booking.schedule_intake import parse_raw_schedule


def test_parser_handles_common_team_message_typos_and_preserves_original_lines() -> None:
    items = parse_raw_schedule(
        """B13 1234
Replace aac
Ac cleaning
Check drainpan by
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
    assert items[0].raw_service_text == "AC replacement + AC cleaning + Drainpan check / repair"
    assert "Lagyn alambre" in items[0].source_line
    assert items[1].raw_service_text == "PVC work"
    assert "Hintayin tawag ko" in items[1].source_line
    assert items[2].raw_service_text == "Drainpan leak"
    assert items[2].scheduled_time == time(8, 30)
    assert items[3].raw_service_text == "AC cleaning"
    assert items[4].raw_service_text == "AC pull-out / collection"
    assert items[5].raw_service_text == "AC check-up"
