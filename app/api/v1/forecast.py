from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.recommendation import ForecastSnapshot
from app.schemas.forecast import (
    ForecastRequest, ForecastResult, ForecastSnapshotResponse
)
from app.services.forecast_service import ForecastService

router = APIRouter()


@router.post("/items/{item_id}", response_model=ForecastResult, summary="Generate demand forecast for an item")
def forecast_item_demand(
    item_id: int,
    request_params: Optional[ForecastRequest] = None,
    save_snapshot: bool = True,
    db: Session = Depends(get_db)
):
    """
    Generate future demand forecasts for an inventory item.
    Supports:
    - `auto`: runs walk-forward evaluation across all candidate models and picks the lowest MAE.
    - `moving_average`: simple moving window mean.
    - `weighted_moving_average`: linear weighted recent demand.
    - `exponential_smoothing`: single exponential smoothing.
    - `linear_trend`: ordinary least squares linear projection.
    """
    try:
        return ForecastService.generate_forecast(
            db, item_id, req=request_params, save_snapshot=save_snapshot
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/items/{item_id}/snapshots", response_model=List[ForecastSnapshotResponse], summary="Get past forecast snapshots")
def get_forecast_snapshots(item_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Retrieve historical forecast runs and tracked accuracy metrics."""
    return (
        db.query(ForecastSnapshot)
        .filter(ForecastSnapshot.item_id == item_id)
        .order_by(ForecastSnapshot.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/models", summary="List available forecasting models")
def list_available_models():
    """Information on supported forecasting algorithms and tuning parameters."""
    return {
        "models": [
            {
                "id": "auto",
                "name": "Auto Selection (Best Fit)",
                "description": "Cross-validates MAE across all models and automatically picks the most accurate model."
            },
            {
                "id": "moving_average",
                "name": "Simple Moving Average (SMA)",
                "parameters": {"window_size": "int (default: 7)"},
                "best_for": "Stable, non-seasonal products"
            },
            {
                "id": "weighted_moving_average",
                "name": "Weighted Moving Average (WMA)",
                "parameters": {"window_size": "int (default: 7)"},
                "best_for": "Fast-moving items where recent sales are most predictive"
            },
            {
                "id": "exponential_smoothing",
                "name": "Single Exponential Smoothing (SES)",
                "parameters": {"alpha": "float 0-1 (default: 0.3)"},
                "best_for": "Smooth trends without clear seasonality"
            },
            {
                "id": "linear_trend",
                "name": "Linear Trend Projection (OLS)",
                "parameters": {},
                "best_for": "Items with steady growth or steady declining demand"
            }
        ]
    }
