import io
import csv
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple, Dict
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.stock import Item
from app.models.consumption import ConsumptionTransaction
from app.schemas.consumption import (
    ConsumptionCreate, BulkConsumptionItem, ConsumptionMetrics, DailyConsumptionPoint
)


class ConsumptionService:
    @staticmethod
    def add_consumption(db: Session, item_id: int, cons_in: ConsumptionCreate) -> ConsumptionTransaction:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(f"Item with id {item_id} not found")
        
        record = ConsumptionTransaction(
            item_id=item_id,
            transaction_date=cons_in.transaction_date,
            quantity=cons_in.quantity,
            channel=cons_in.channel,
            unit_price=cons_in.unit_price,
            notes=cons_in.notes
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def add_bulk_consumption(db: Session, records: List[BulkConsumptionItem]) -> Tuple[int, List[str]]:
        created_count = 0
        errors = []
        
        # Cache items by SKU
        sku_map = {item.sku: item.id for item in db.query(Item).all()}

        for idx, rec in enumerate(records):
            item_id = sku_map.get(rec.sku)
            if not item_id:
                errors.append(f"Record {idx}: SKU '{rec.sku}' does not exist.")
                continue
            
            trans = ConsumptionTransaction(
                item_id=item_id,
                transaction_date=rec.transaction_date,
                quantity=rec.quantity,
                channel=rec.channel or "Direct Sales",
                unit_price=rec.unit_price,
                notes=rec.notes
            )
            db.add(trans)
            created_count += 1
        
        db.commit()
        return created_count, errors

    @staticmethod
    def get_item_consumption_history(
        db: Session, 
        item_id: int, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> List[ConsumptionTransaction]:
        query = db.query(ConsumptionTransaction).filter(ConsumptionTransaction.item_id == item_id)
        if start_date:
            query = query.filter(ConsumptionTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(ConsumptionTransaction.transaction_date <= end_date)
        return query.order_by(ConsumptionTransaction.transaction_date.asc()).all()

    @staticmethod
    def get_daily_series(
        db: Session, 
        item_id: int, 
        days_back: int = 90
    ) -> pd.Series:
        """
        Retrieves a continuous daily time-series of consumption for the item,
        filling missing dates with 0 demand.
        """
        end_d = date.today()
        start_d = end_d - timedelta(days=days_back)
        
        records = (
            db.query(
                ConsumptionTransaction.transaction_date,
                func.sum(ConsumptionTransaction.quantity).label("daily_qty")
            )
            .filter(
                ConsumptionTransaction.item_id == item_id,
                ConsumptionTransaction.transaction_date >= start_d,
                ConsumptionTransaction.transaction_date <= end_d
            )
            .group_by(ConsumptionTransaction.transaction_date)
            .all()
        )

        # Generate full date range
        date_idx = pd.date_range(start=start_d, end=end_d, freq="D")
        daily_dict = {r[0]: int(r[1]) for r in records}
        
        # Build pandas series
        data = [daily_dict.get(d.date(), 0) for d in date_idx]
        series = pd.Series(data=data, index=date_idx, name="consumption")
        return series

    @staticmethod
    def get_consumption_metrics(db: Session, item_id: int, days_back: int = 90) -> ConsumptionMetrics:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(f"Item with id {item_id} not found")

        series = ConsumptionService.get_daily_series(db, item_id, days_back=days_back)
        
        total_records = db.query(ConsumptionTransaction).filter(ConsumptionTransaction.item_id == item_id).count()
        total_quantity = int(series.sum())
        mean_demand = float(series.mean()) if len(series) > 0 else 0.0
        std_demand = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        
        # Volatility index (Coefficient of Variation)
        cv = (std_demand / mean_demand) if mean_demand > 0 else 0.0
        
        # Format recent history points for charts (last 30 days)
        recent = series.tail(30)
        recent_history = [
            DailyConsumptionPoint(date=ts.strftime("%Y-%m-%d"), quantity=int(val))
            for ts, val in recent.items()
        ]

        return ConsumptionMetrics(
            item_id=item.id,
            sku=item.sku,
            item_name=item.name,
            total_records=total_records,
            days_analyzed=len(series),
            total_quantity_consumed=total_quantity,
            average_daily_demand=round(mean_demand, 2),
            demand_standard_deviation=round(std_demand, 2),
            coefficient_of_variation=round(cv, 3),
            min_daily_demand=int(series.min()) if len(series) > 0 else 0,
            max_daily_demand=int(series.max()) if len(series) > 0 else 0,
            recent_history=recent_history
        )

    @staticmethod
    def import_consumption_csv(db: Session, csv_content: str) -> Tuple[int, List[str]]:
        reader = csv.DictReader(io.StringIO(csv_content))
        bulk_items = []
        errors = []

        for row_idx, row in enumerate(reader, start=1):
            try:
                sku = row.get("sku") or row.get("SKU") or row.get("Product")
                date_str = row.get("date") or row.get("Date") or row.get("transaction_date")
                qty_str = row.get("quantity") or row.get("Quantity") or row.get("Sales")

                if not sku or not date_str or not qty_str:
                    errors.append(f"Row {row_idx}: Missing sku, date, or quantity")
                    continue

                # Parse date
                try:
                    t_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
                except ValueError:
                    t_date = datetime.strptime(date_str.strip(), "%m/%d/%Y").date()

                bulk_items.append(BulkConsumptionItem(
                    sku=sku.strip(),
                    transaction_date=t_date,
                    quantity=int(float(qty_str)),
                    channel=row.get("channel", row.get("Region", "Direct Sales")),
                    unit_price=float(row.get("unit_price")) if row.get("unit_price") else None,
                    notes=row.get("notes")
                ))
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

        created, bulk_errors = ConsumptionService.add_bulk_consumption(db, bulk_items)
        errors.extend(bulk_errors)
        return created, errors
