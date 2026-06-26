from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.schemas import SimulateRequest
from app.services.simulator_service import SimulatorService

router = APIRouter(prefix="/simulate", tags=["simulator"])
simulator_service = SimulatorService()


@router.post("")
def run_simulation(request: SimulateRequest, db: Session = Depends(get_db)):
    try:
        return simulator_service.simulate(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
