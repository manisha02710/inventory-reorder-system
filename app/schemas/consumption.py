from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class ConsumptionCreate(BaseModel):
    transaction_date: date = Field(..., examples=["2026-03-01"])
    quantity: int = Field(..., gt=0, examples=[12])
    channel: str = Field(default="Direct Sales", examples=["E-Commerce"])
    unit_price: Optional[float] = Field(default=None, examples=[59.99])
    notes: Optional[str] = Field(default=None)


class BulkConsumptionItem(BaseModel):
    sku: str = Field(..., examples=["ELEC-1001"])
    transaction_date: date = Field(..., examples=["2026-03-01"])
    quantity: int = Field(..., gt=0, examples=[15])
    channel: Optional[str] = "Direct Sales"
    unit_price: Optional[float] = None
    notes: Optional[str] = None


class ConsumptionResponse(BaseModel):
    id: int
    item_id: int
    transaction_date: date
    quantity: int
    channel: str
    unit_price: Optional[float]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyConsumptionPoint(BaseModel):
    date: str
    quantity: int


class ConsumptionMetrics(BaseModel):
    item_id: int
    sku: str
    item_name: str
    total_records: int
    days_analyzed: int
    total_quantity_consumed: int
    average_daily_demand: float
    demand_standard_deviation: float
    coefficient_of_variation: float  # volatility indicator
    min_daily_demand: int
    max_daily_demand: int
    recent_history: List[DailyConsumptionPoint]
