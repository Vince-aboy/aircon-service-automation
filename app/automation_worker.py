"""One-shot background delivery worker for the synthetic n8n bridge."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.booking.service import run_automatic_delivery_worker
from app.database.session import create_database_engine


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    engine = create_database_engine()
    session = Session(engine)
    try:
        event = run_automatic_delivery_worker(session)
        session.commit()
        if event is None:
            logger.info("Automatic delivery disabled or no due event found")
        else:
            logger.info("Processed outbox event id=%s status=%s attempts=%s", event.id, event.status, event.attempt_count)
        return 0
    except Exception:
        session.rollback()
        logger.exception("Automatic delivery worker failed")
        return 1
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
