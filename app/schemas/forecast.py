from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class ForecastRequest(BaseModel):
    horizon_days: Optional[int] = Field(default=None, ge=1, le=180, description="Forecast horizon. Defaults to item lead time if omitted.")
    model_type: Optional[str] = Field(default="auto", examples=["auto"], description="auto, moving_average, exponential_smoothing, linear_trend")
    window_size: Optional[int] = Field(default=7, ge=2, le=90, description="Window size for Moving Average")
    alpha: Optional[float] = Field(default=0.3, gt=0, lt=1, description="Smoothing parameter for Exponential Smoothing")


class ForecastDailyPoint(BaseModel):
    date: str
    predicted_quantity: float
    lower_bound: float
    upper_bound: float


class ForecastEvaluationMetrics(BaseModel):
    mae: float
    rmse: float
    mape: Optional[float] = None


from typing import Optional, List, Dict, Any

class ForecastResult(BaseModel):
    item_id: int
    sku: str
    item_name: str
    model_name: str
    horizon_days: int
    total_forecasted_demand: float
    daily_forecasted_mean: float
    metrics: ForecastEvaluationMetrics
    historical_daily_mean: float
    historical_points: Optional[List[Dict[str, Any]]] = None
    daily_predictions: List[ForecastDailyPoint]
    comparison_summary: Optional[Dict[str, float]] = None  # MAE of each tested model in auto mode


class ForecastSnapshotResponse(BaseModel):
    id: int
    item_id: int
    forecast_date: date
    model_name: str
    horizon_days: int
    total_forecasted_demand: float
    daily_forecasted_mean: float
    mae: Optional[float]
    rmse: Optional[float]
    mape: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
