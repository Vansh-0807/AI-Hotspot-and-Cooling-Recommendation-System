from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.root_cause_service import RootCauseService

router = APIRouter(prefix="/analysis", tags=["analysis"])
root_cause_service = RootCauseService()


@router.get("/{cell_id}")
def get_analysis(cell_id: str, db: Session = Depends(get_db)):
    try:
        return root_cause_service.analyze(db, cell_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
