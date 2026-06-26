from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.services.priority_service import PriorityService

router = APIRouter(prefix="/priority", tags=["priority"])
priority_service = PriorityService()


@router.get("")
def get_priority(
    city: str = Query(default=None, description="City name"),
    top_n: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    target_city = city if city else settings.target_city
    try:
        return priority_service.rank(db, target_city, top_n)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc