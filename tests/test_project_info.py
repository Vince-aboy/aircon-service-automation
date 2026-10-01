from app.core.project_info import PROJECT_MODE, PROJECT_NAME, is_production_ready


def test_project_identifies_as_local_prototype() -> None:
    assert PROJECT_NAME == "Aircon Service Automation"
    assert PROJECT_MODE == "local_prototype"
    assert is_production_ready() is False
