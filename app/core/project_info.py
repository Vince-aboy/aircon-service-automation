"""Runtime metadata for the controlled booking application."""

import os

PROJECT_NAME = "Aircon Service Automation"
PROJECT_MODE = os.getenv("AIRCON_OPERATION_MODE", "local_prototype").strip().lower() or "local_prototype"


def is_live_mode() -> bool:
    """Return whether the application is explicitly configured for live owner operations."""
    return PROJECT_MODE == "live"


def is_production_ready() -> bool:
    """Return whether live operation was explicitly enabled at runtime."""
    return is_live_mode()
