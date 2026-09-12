from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ForecastSnapshot(Base):
    """
    Stage 3: Demand Forecasting Model
    Persists historical forecasts for accuracy monitoring and tracking.
    """
    __tablename__ = "forecast_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, default=date.today)
    model_name = Column(String(50), nullable=False)  # Moving Average, Exp Smoothing, Linear Trend
    horizon_days = Column(Integer, nullable=False)
    total_forecasted_demand = Column(Float, nullable=False)
    daily_forecasted_mean = Column(Float, nullable=False)
    daily_predictions = Column(JSON, nullable=True)  # List of daily predictions [10.2, 11.5, ...]
    
    # Error metrics
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=get_utc_now)

    item = relationship("Item", back_populates="forecasts")


class ReorderRecommendation(Base):
    """
    Stage 4: Reorder Recommendation Model
    Actionable replenishment decisions based on Stock + Consumption + Forecasting.
    """
    __tablename__ = "reorder_recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_at = Column(DateTime, default=get_utc_now, index=True)
    
    current_stock = Column(Integer, nullable=False)
    avg_daily_demand = Column(Float, nullable=False)
    demand_std_dev = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    
    lead_time_demand = Column(Float, nullable=False)
    safety_stock = Column(Integer, nullable=False)
    reorder_point = Column(Integer, nullable=False)
    economic_order_quantity = Column(Integer, nullable=False)
    recommended_order_quantity = Column(Integer, nullable=False)
    
    # Risk & Planning Metrics
    urgency_status = Column(String(30), nullable=False)  # CRITICAL, REORDER_NOW, REORDER_SOON, HEALTHY, OVERSTOCK
    days_until_stockout = Column(Float, nullable=True)
    estimated_reorder_cost = Column(Float, nullable=False)
    
    rationale = Column(String(500), nullable=True)

    item = relationship("Item", back_populates="recommendations")
