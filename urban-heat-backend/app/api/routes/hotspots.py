from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.services.hotspot_service import HotspotService

router = APIRouter(prefix="/hotspots", tags=["hotspots"])
hotspot_service = HotspotService()


@router.get("")
def get_hotspots(
    city: str = Query(default=None, description="City name"),
    query_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    target_city = city if city else settings.target_city
    target_date = query_date or date.today()
    try:
        return hotspot_service.get_hotspots(db, target_city, target_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc