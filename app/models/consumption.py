from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ConsumptionTransaction(Base):
    """
    Stage 2: Consumption Data Model
    Tracks daily sales, internal usage, or issues from the warehouse.
    """
    __tablename__ = "consumption_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    channel = Column(String(50), default="Direct Sales")  # Retail, Online, Wholesale, B2B, Internal
    unit_price = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    item = relationship("Item", back_populates="consumption_records")
