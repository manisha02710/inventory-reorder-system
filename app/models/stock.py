from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Item(Base):
    """
    Stage 1: Stock Data Model
    Represents an inventory item/SKU with current stock and replenishment attributes.
    """
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="General", index=True)
    
    # Inventory levels
    current_stock = Column(Integer, default=0, nullable=False)
    min_stock_level = Column(Integer, default=0, nullable=False)
    max_stock_level = Column(Integer, default=1000, nullable=False)
    safety_stock_override = Column(Integer, nullable=True)  # Manual override if set
    
    # Replenishment parameters
    lead_time_days = Column(Integer, default=7, nullable=False)
    unit_cost = Column(Float, default=10.0, nullable=False)
    ordering_cost = Column(Float, default=50.0, nullable=False)  # Fixed S in EOQ
    holding_cost_rate = Column(Float, default=0.20, nullable=False)  # Annual % of unit cost
    
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    adjustments = relationship("StockAdjustment", back_populates="item", cascade="all, delete-orphan")
    consumption_records = relationship("ConsumptionTransaction", back_populates="item", cascade="all, delete-orphan")
    recommendations = relationship("ReorderRecommendation", back_populates="item", cascade="all, delete-orphan")
    forecasts = relationship("ForecastSnapshot", back_populates="item", cascade="all, delete-orphan")


class StockAdjustment(Base):
    """
    Audit log of manual or automated inventory changes (restocks, loss, audits).
    """
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity_change = Column(Integer, nullable=False)  # positive for restock, negative for deduction
    reason = Column(String(100), default="audit")  # restock, audit, damaged, return
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=get_utc_now)

    item = relationship("Item", back_populates="adjustments")
