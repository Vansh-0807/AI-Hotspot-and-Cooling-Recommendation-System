"""Bootstrap live grid from OpenWeather + OSM — no synthetic seed data."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import GridCell
from app.services.location_service import LocationService

logger = logging.getLogger(__name__)


def keys_configured() -> bool:
    settings = get_settings()
    return bool(settings.openweather_api_key.strip())


def raipur_cell_count(db: Session) -> int:
    settings = get_settings()
    return db.query(GridCell).filter(GridCell.city == settings.target_city).count()


def ensure_raipur_live_data(db: Session, force: bool = False) -> dict:
    """
    Load Raipur exclusively from live APIs. Clears legacy/demo rows on full refresh.
    """
    settings = get_settings()
    city = settings.target_city

    if not keys_configured():
        logger.warning(
            "OPENWEATHER_API_KEY is missing in .env — live data cannot be loaded. Will use synthetic data."
        )

    existing = raipur_cell_count(db)
    if existing > 0 and not force:
        logger.info("Raipur grid already loaded (%d cells)", existing)
        return {"refreshed": False, "cells": existing, "city": city}

    logger.info("Fetching live urban heat data for %s…", city)
    db.query(GridCell).delete()
    db.commit()

    service = LocationService()
    result = service.analyze_city(db, city=city, force_refresh=True)
    return {
        "refreshed": True,
        "cells": result["cells_created"],
        "city": city,
        "formatted_address": result["formatted_address"],
        "base_temperature_c": result["base_temperature_c"],
    }
