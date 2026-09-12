import io
import csv
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.stock import Item, StockAdjustment
from app.schemas.stock import ItemCreate, ItemUpdate, StockAdjustmentCreate, StockOverviewItem


class StockService:
    @staticmethod
    def get_item(db: Session, item_id: int) -> Optional[Item]:
        return db.query(Item).filter(Item.id == item_id).first()

    @staticmethod
    def get_item_by_sku(db: Session, sku: str) -> Optional[Item]:
        return db.query(Item).filter(Item.sku == sku).first()

    @staticmethod
    def list_items(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Item]:
        query = db.query(Item)
        if category:
            query = query.filter(Item.category == category)
        if search:
            query = query.filter((Item.sku.ilike(f"%{search}%")) | (Item.name.ilike(f"%{search}%")))
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create_item(db: Session, item_in: ItemCreate) -> Item:
        db_item = Item(**item_in.model_dump())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def update_item(db: Session, db_item: Item, item_in: ItemUpdate) -> Item:
        update_data = item_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_item, field, value)
        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def delete_item(db: Session, db_item: Item) -> None:
        db.delete(db_item)
        db.commit()

    @staticmethod
    def adjust_stock(db: Session, item_id: int, adj_in: StockAdjustmentCreate) -> Tuple[Item, StockAdjustment]:
        item = StockService.get_item(db, item_id)
        if not item:
            raise ValueError(f"Item with id {item_id} not found")
        
        new_stock = item.current_stock + adj_in.quantity_change
        if new_stock < 0:
            raise ValueError(f"Cannot reduce stock below zero. Current stock: {item.current_stock}, requested change: {adj_in.quantity_change}")
        
        item.current_stock = new_stock
        adjustment = StockAdjustment(
            item_id=item_id,
            quantity_change=adj_in.quantity_change,
            reason=adj_in.reason,
            notes=adj_in.notes
        )
        db.add(adjustment)
        db.commit()
        db.refresh(item)
        db.refresh(adjustment)
        return item, adjustment

    @staticmethod
    def get_stock_overview(db: Session) -> List[StockOverviewItem]:
        items = db.query(Item).all()
        result = []
        for item in items:
            value = round(item.current_stock * item.unit_cost, 2)
            if item.current_stock <= item.min_stock_level:
                status = "Critical"
            elif item.current_stock <= (item.min_stock_level * 1.5):
                status = "Low"
            elif item.current_stock > item.max_stock_level:
                status = "Overstocked"
            else:
                status = "Normal"
            
            result.append(StockOverviewItem(
                id=item.id,
                sku=item.sku,
                name=item.name,
                category=item.category,
                current_stock=item.current_stock,
                lead_time_days=item.lead_time_days,
                unit_cost=item.unit_cost,
                total_inventory_value=value,
                status=status
            ))
        return result

    @staticmethod
    def import_items_from_csv(db: Session, csv_content: str) -> Tuple[int, List[str]]:
        reader = csv.DictReader(io.StringIO(csv_content))
        created_count = 0
        errors = []

        for row_idx, row in enumerate(reader, start=1):
            try:
                sku = row.get("sku") or row.get("SKU") or row.get("item_id")
                name = row.get("name") or row.get("Product") or row.get("item_name")
                if not sku or not name:
                    errors.append(f"Row {row_idx}: Missing required fields 'sku' or 'name'")
                    continue

                existing = StockService.get_item_by_sku(db, sku.strip())
                if existing:
                    # Update stock if provided
                    if "current_stock" in row or "Quantity" in row:
                        val = int(row.get("current_stock") or row.get("Quantity", 0))
                        existing.current_stock = val
                    db.commit()
                    continue

                item = Item(
                    sku=sku.strip(),
                    name=name.strip(),
                    category=row.get("category", "General").strip(),
                    current_stock=int(row.get("current_stock") or row.get("Quantity", 0)),
                    min_stock_level=int(row.get("min_stock_level", 10)),
                    max_stock_level=int(row.get("max_stock_level", 500)),
                    lead_time_days=int(row.get("lead_time_days", 7)),
                    unit_cost=float(row.get("unit_cost") or row.get("Cost", 10.0)),
                    ordering_cost=float(row.get("ordering_cost", 50.0)),
                    holding_cost_rate=float(row.get("holding_cost_rate", 0.20))
                )
                db.add(item)
                db.commit()
                created_count += 1
            except Exception as e:
                db.rollback()
                errors.append(f"Row {row_idx}: {str(e)}")

        return created_count, errors
