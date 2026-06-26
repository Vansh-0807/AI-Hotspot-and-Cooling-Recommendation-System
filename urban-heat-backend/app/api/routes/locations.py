from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.models import GridCell
from app.models.schemas import DashboardResponse, LocationAnalyzeResponse
from app.services.location_service import LocationService
from app.services.priority_service import PriorityService

router = APIRouter(prefix="/locations", tags=["locations"])
location_service = LocationService()
priority_service = PriorityService()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db), city: str = Query(None, description="City name to fetch data for")):
    """Dynamic dashboard — live OpenWeather + OSM for any Indian city."""
    settings = get_settings()
    target_city = city if city else settings.target_city
    
    try:
        result = location_service.analyze_city(db, city=target_city, force_refresh=True)
        priority = priority_service.rank(db, target_city, top_n=8)
        return DashboardResponse(
            city=result["city"],
            formatted_address=result["formatted_address"],
            data_source=result["data_source"],
            base_temperature_c=result["base_temperature_c"],
            ml_hotspot_count=result["ml_hotspot_count"],
            ml_model=result["ml_model"],
            hotspots=result["hotspots"],
            priority=priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dashboard load failed: {exc}") from exc


@router.post("/refresh", response_model=LocationAnalyzeResponse)
def refresh_data(db: Session = Depends(get_db), city: str = Query(None, description="City name to refresh")):
    """Force refresh city from live APIs."""
    settings = get_settings()
    target_city = city if city else settings.target_city
    try:
        db.query(GridCell).filter(GridCell.city == target_city).delete()
        db.commit()
        result = location_service.analyze_city(db, city=target_city, force_refresh=True)
        return LocationAnalyzeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}") from exc
