from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ItemBase(BaseModel):
    sku: str = Field(..., examples=["ELEC-1001"], description="Unique SKU code")
    name: str = Field(..., examples=["Wireless Noise Cancelling Headphones"])
    category: str = Field(default="General", examples=["Electronics"])
    current_stock: int = Field(default=0, ge=0, examples=[45])
    min_stock_level: int = Field(default=10, ge=0, examples=[15])
    max_stock_level: int = Field(default=500, ge=1, examples=[200])
    safety_stock_override: Optional[int] = Field(default=None, ge=0, examples=[20])
    lead_time_days: int = Field(default=7, ge=1, examples=[5], description="Lead time in calendar days")
    unit_cost: float = Field(default=10.0, gt=0, examples=[49.99])
    ordering_cost: float = Field(default=50.0, ge=0, examples=[40.0], description="Fixed order placement cost (S in EOQ)")
    holding_cost_rate: float = Field(default=0.20, ge=0, le=1.0, examples=[0.20], description="Annual holding cost fraction")


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    current_stock: Optional[int] = Field(default=None, ge=0)
    min_stock_level: Optional[int] = Field(default=None, ge=0)
    max_stock_level: Optional[int] = Field(default=None, ge=1)
    safety_stock_override: Optional[int] = Field(default=None, ge=0)
    lead_time_days: Optional[int] = Field(default=None, ge=1)
    unit_cost: Optional[float] = Field(default=None, gt=0)
    ordering_cost: Optional[float] = Field(default=None, ge=0)
    holding_cost_rate: Optional[float] = Field(default=None, ge=0, le=1.0)


class StockAdjustmentCreate(BaseModel):
    quantity_change: int = Field(..., examples=[50], description="Positive for addition/restock, negative for deduction")
    reason: str = Field(default="restock", examples=["restock"])
    notes: Optional[str] = Field(default=None, examples=["Received shipment PO-9912"])


class StockAdjustmentResponse(BaseModel):
    id: int
    item_id: int
    quantity_change: int
    reason: str
    notes: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockOverviewItem(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    current_stock: int
    lead_time_days: int
    unit_cost: float
    total_inventory_value: float
    status: str  # Critical, Low, Normal, Overstocked

    model_config = ConfigDict(from_attributes=True)
