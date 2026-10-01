"""Database-engine construction with runtime-only credentials."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine


def create_database_engine() -> Engine:
    """Create an engine from a password-free database URL supplied at runtime."""
    database_url = os.getenv("AIRCON_DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "AIRCON_DATABASE_URL is required. Supply it only in the current terminal session."
        )
    return create_engine(database_url, pool_pre_ping=True)
