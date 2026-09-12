from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.stock import (
    ItemCreate, ItemUpdate, ItemResponse, StockAdjustmentCreate, StockAdjustmentResponse, StockOverviewItem
)
from app.services.stock_service import StockService

router = APIRouter()


@router.get("/items", response_model=List[ItemResponse], summary="List inventory items")
def get_items(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve items from the inventory master with optional category and search filters."""
    return StockService.list_items(db, skip=skip, limit=limit, category=category, search=search)


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, summary="Create an inventory item")
def create_item(item_in: ItemCreate, db: Session = Depends(get_db)):
    """Add a new item to the inventory master."""
    existing = StockService.get_item_by_sku(db, item_in.sku)
    if existing:
        raise HTTPException(status_code=400, detail=f"Item with SKU '{item_in.sku}' already exists.")
    return StockService.create_item(db, item_in)


@router.get("/items/{item_id}", response_model=ItemResponse, summary="Get item details")
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get item by its database ID."""
    item = StockService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found.")
    return item


@router.put("/items/{item_id}", response_model=ItemResponse, summary="Update an item")
def update_item(item_id: int, item_in: ItemUpdate, db: Session = Depends(get_db)):
    """Update stock parameters, min/max limits, costs, or lead times for an item."""
    item = StockService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found.")
    return StockService.update_item(db, item, item_in)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an item")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Remove an item from inventory."""
    item = StockService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found.")
    StockService.delete_item(db, item)
    return None


@router.post("/items/{item_id}/adjust", response_model=StockAdjustmentResponse, summary="Record stock adjustment")
def adjust_stock(item_id: int, adj_in: StockAdjustmentCreate, db: Session = Depends(get_db)):
    """Manually adjust stock quantity (positive for shipment received, negative for loss/damage)."""
    try:
        _, adjustment = StockService.adjust_stock(db, item_id, adj_in)
        return adjustment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/overview", response_model=List[StockOverviewItem], summary="Get inventory stock health overview")
def get_stock_overview(db: Session = Depends(get_db)):
    """Returns a quick summary of stock health, inventory values, and critical items."""
    return StockService.get_stock_overview(db)


@router.post("/upload-csv", summary="Bulk import inventory items from CSV")
async def upload_items_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a CSV file containing inventory items (sku, name, current_stock, unit_cost, lead_time_days)."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")
    
    content = (await file.read()).decode("utf-8")
    count, errors = StockService.import_items_from_csv(db, content)
    return {
        "message": f"Successfully processed items CSV. {count} new items created.",
        "created_count": count,
        "errors": errors
    }


@router.get("/template-csv", summary="Download sample CSV template for inventory items")
def download_stock_template():
    """Download ready-to-use CSV template for importing inventory items."""
    csv_data = "sku,name,category,current_stock,min_stock_level,max_stock_level,lead_time_days,unit_cost,ordering_cost\n" \
               "TECH-101,Noise-Cancelling Headphones,Electronics,25,15,200,7,2499.00,350.00\n" \
               "TECH-102,USB-C Fast Cable 2m,Electronics,120,40,500,5,299.00,100.00\n" \
               "OFFC-301,Ergonomic Desk Mat,Office,45,20,150,10,650.00,150.00\n"
    from fastapi.responses import Response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_items_template.csv"}
    )
