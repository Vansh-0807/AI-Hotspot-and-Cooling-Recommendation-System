from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.schemas import RecommendationRequest
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendation_service = RecommendationService()


@router.post("")
def create_recommendations(request: RecommendationRequest, db: Session = Depends(get_db)):
    try:
        return recommendation_service.handle_request(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
