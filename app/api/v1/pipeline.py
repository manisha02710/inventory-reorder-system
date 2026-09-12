from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.recommendation import (
    ReorderCalculationParameters, PipelineSummary
)
from app.services.reorder_service import ReorderService

router = APIRouter()


@router.post("/run", response_model=PipelineSummary, summary="Execute full 4-stage inventory reorder pipeline")
def run_reorder_pipeline(
    params: Optional[ReorderCalculationParameters] = None,
    db: Session = Depends(get_db)
):
    """
    Triggers the end-to-end 4-stage automated pipeline across all products in inventory:
    1. Reads latest stock levels and lead times (Stage 1).
    2. Analyzes consumption history and demand volatility (Stage 2).
    3. Runs time-series forecasting models (Stage 3).
    4. Computes ROP, EOQ, urgency risk, and purchase order quantities (Stage 4).
    """
    return ReorderService.run_pipeline(db, params=params)


@router.get("/summary", response_model=PipelineSummary, summary="Get latest pipeline overview and status")
def get_pipeline_summary(db: Session = Depends(get_db)):
    """Returns the most recent reorder recommendation overview across all inventory."""
    return ReorderService.run_pipeline(db)
