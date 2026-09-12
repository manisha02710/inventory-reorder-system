from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ReorderCalculationParameters(BaseModel):
    service_level: Optional[float] = Field(default=0.95, gt=0.50, lt=1.0, description="Service level target (e.g. 0.95 = 95%)")
    lead_time_days_override: Optional[int] = Field(default=None, ge=1)
    ordering_cost_override: Optional[float] = Field(default=None, ge=0)
    holding_cost_rate_override: Optional[float] = Field(default=None, ge=0, le=1.0)


class ReorderRecommendationResponse(BaseModel):
    id: Optional[int] = None
    item_id: int
    sku: str
    item_name: str
    category: str
    
    # Stock Status
    current_stock: int
    min_stock_level: int
    max_stock_level: int
    unit_cost: float
    
    # Stage 2 & 3 Demand Context
    avg_daily_demand: float
    demand_std_dev: float
    forecast_daily_mean: float
    forecast_model_used: str
    lead_time_days: int
    
    # Stage 4 Scientific Calculations
    lead_time_demand: float
    safety_stock: int
    reorder_point: int
    economic_order_quantity: int
    recommended_order_quantity: int
    
    # Decisions & Alerts
    urgency_status: str  # CRITICAL, REORDER_NOW, REORDER_SOON, HEALTHY, OVERSTOCK
    urgency_color: str   # red, orange, yellow, green, purple
    days_until_stockout: Optional[float]
    estimated_reorder_cost: float
    rationale: str
    
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PipelineSummary(BaseModel):
    total_items_analyzed: int
    critical_items_count: int
    reorder_now_count: int
    reorder_soon_count: int
    healthy_count: int
    overstock_count: int
    total_estimated_reorder_investment: float
    recommendations: List[ReorderRecommendationResponse]
