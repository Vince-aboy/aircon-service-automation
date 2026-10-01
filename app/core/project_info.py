"""Stable metadata used by the local prototype."""

PROJECT_NAME = "Aircon Service Automation"
PROJECT_MODE = "local_prototype"


def is_production_ready() -> bool:
    """The learning prototype must never present itself as production-ready."""
    return False
