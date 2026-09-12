from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.recommendation import ReorderRecommendation
from app.schemas.recommendation import (
    ReorderCalculationParameters, ReorderRecommendationResponse
)
from app.services.reorder_service import ReorderService

router = APIRouter()


@router.post("/items/{item_id}", response_model=ReorderRecommendationResponse, summary="Compute reorder recommendation for an item")
def calculate_item_recommendation(
    item_id: int,
    params: Optional[ReorderCalculationParameters] = None,
    persist: bool = True,
    db: Session = Depends(get_db)
):
    """
    Evaluates Stage 1 (Stock), Stage 2 (Consumption), and Stage 3 (Forecast)
    to compute:
    - Lead Time Demand (LTD)
    - Dynamic Safety Stock (SS) based on cycle service level (Z)
    - Reorder Point (ROP)
    - Economic Order Quantity (EOQ)
    - Reorder Urgency (CRITICAL, REORDER_NOW, REORDER_SOON, HEALTHY, OVERSTOCK)
    - Days to stockout
    - Recommended order quantity and total purchase cost
    """
    try:
        return ReorderService.calculate_recommendation(db, item_id, params=params, persist=persist)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/items/{item_id}/history", summary="Get recommendation history for an item")
def get_recommendation_history(item_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Retrieve historical recommendation runs for an item."""
    return (
        db.query(ReorderRecommendation)
        .filter(ReorderRecommendation.item_id == item_id)
        .order_by(ReorderRecommendation.generated_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/critical", response_model=List[ReorderRecommendationResponse], summary="List all critical reorder items")
def get_critical_recommendations(db: Session = Depends(get_db)):
    """Retrieves all inventory items currently flagged with CRITICAL or REORDER_NOW urgency."""
    summary = ReorderService.run_pipeline(db)
    return [
        r for r in summary.recommendations 
        if r.urgency_status in ["CRITICAL", "REORDER_NOW"]
    ]


from pydantic import BaseModel, Field
import uuid

class PurchaseOrderItem(BaseModel):
    item_id: int
    quantity: int = Field(..., gt=0)

class CreatePurchaseOrderRequest(BaseModel):
    po_number: Optional[str] = None
    items: List[PurchaseOrderItem]
    supplier_notes: Optional[str] = None
    fulfill_immediately: bool = False


@router.post("/create-po", summary="Generate and optionally fulfill Purchase Order")
def create_purchase_order(req: CreatePurchaseOrderRequest, db: Session = Depends(get_db)):
    """
    Generates a formal purchase order for recommended items and can instantly
    simulate replenishment restock into the warehouse inventory.
    """
    from app.services.stock_service import StockService
    from app.schemas.stock import StockAdjustmentCreate
    from app.models.stock import Item

    po_id = req.po_number or f"PO-{uuid.uuid4().hex[:8].upper()}"
    line_items = []
    total_cost = 0.0

    for item_req in req.items:
        db_item = db.query(Item).filter(Item.id == item_req.item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"Item with id {item_req.item_id} not found")

        item_cost = round(item_req.quantity * db_item.unit_cost, 2)
        total_cost += item_cost

        # If fulfillment is requested, immediately increment stock
        if req.fulfill_immediately:
            StockService.adjust_stock(
                db, 
                db_item.id, 
                StockAdjustmentCreate(
                    quantity_change=item_req.quantity,
                    reason="restock",
                    notes=f"PO {po_id} Replenishment"
                )
            )

        line_items.append({
            "item_id": db_item.id,
            "sku": db_item.sku,
            "name": db_item.name,
            "quantity": item_req.quantity,
            "unit_cost": db_item.unit_cost,
            "total_line_cost": item_cost,
            "lead_time_days": db_item.lead_time_days,
            "new_stock_level": db_item.current_stock
        })

    return {
        "po_number": po_id,
        "status": "FULFILLED" if req.fulfill_immediately else "ISSUED",
        "supplier_notes": req.supplier_notes,
        "total_order_cost": round(total_cost, 2),
        "line_items_count": len(line_items),
        "items": line_items,
        "message": f"Purchase Order {po_id} created successfully" + (" and restocked to warehouse." if req.fulfill_immediately else ".")
    }
    import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@router.get("/export/csv", summary="Export Reorder Report to CSV")
def export_recommendations_csv(db: Session = Depends(get_db)):
    """Downloads the Stage 4 recommendations as a CSV file."""
    summary = ReorderService.run_pipeline(db)
    
    output = StringIO()
    writer = csv.writer(output)
    # Headers matching your INR currency focus
    writer.writerow(["SKU", "Item Name", "Current Stock", "Urgency", "ROP", "Safety Stock", "Rec Order Qty", "Unit Cost (INR)", "Total Investment (INR)"])
    
    for r in summary.recommendations:
        writer.writerow([
            r.sku, r.item_name, r.current_stock, r.urgency_status, 
            r.reorder_point, r.safety_stock, r.recommended_order_quantity, 
            r.unit_cost, r.estimated_reorder_cost
        ])
    
    output.seek(0)
    return StreamingResponse(
        output, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=reorder_report.csv"}
    )
