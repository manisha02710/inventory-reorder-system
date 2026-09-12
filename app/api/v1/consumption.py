from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.consumption import (
    ConsumptionCreate, BulkConsumptionItem, ConsumptionResponse, ConsumptionMetrics
)
from app.services.consumption_service import ConsumptionService

router = APIRouter()


@router.post("/items/{item_id}", response_model=ConsumptionResponse, status_code=status.HTTP_201_CREATED, summary="Log a consumption/sales record")
def log_consumption(item_id: int, cons_in: ConsumptionCreate, db: Session = Depends(get_db)):
    """Log an individual sale or usage event for an inventory item."""
    try:
        return ConsumptionService.add_consumption(db, item_id, cons_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk", summary="Bulk log consumption transactions")
def bulk_log_consumption(records: List[BulkConsumptionItem], db: Session = Depends(get_db)):
    """Add multiple consumption records simultaneously across multiple SKUs."""
    created, errors = ConsumptionService.add_bulk_consumption(db, records)
    return {
        "message": f"Successfully logged {created} consumption records.",
        "created_count": created,
        "errors": errors
    }


@router.get("/items/{item_id}/history", response_model=List[ConsumptionResponse], summary="Get consumption history")
def get_consumption_history(
    item_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Retrieve raw chronological sales/usage logs for an item."""
    return ConsumptionService.get_item_consumption_history(db, item_id, start_date=start_date, end_date=end_date)


@router.get("/items/{item_id}/metrics", response_model=ConsumptionMetrics, summary="Get aggregate demand metrics")
def get_demand_metrics(
    item_id: int,
    days_back: int = 90,
    db: Session = Depends(get_db)
):
    """
    Computes statistical consumption metrics for an item over the designated time window:
    - Average Daily Demand
    - Standard Deviation of Daily Demand
    - Demand Volatility (Coefficient of Variation)
    - Min and Max Daily Outflows
    """
    try:
        return ConsumptionService.get_consumption_metrics(db, item_id, days_back=days_back)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/upload-csv", summary="Bulk import historical sales/consumption CSV")
async def upload_consumption_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a sales/consumption CSV file with columns: sku (or Product), date, quantity (or Sales)."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")
    
    content = (await file.read()).decode("utf-8")
    count, errors = ConsumptionService.import_consumption_csv(db, content)
    return {
        "message": f"Successfully imported {count} consumption records from CSV.",
        "created_count": count,
        "errors": errors
    }


@router.get("/template-csv", summary="Download sample CSV template for sales/consumption")
def download_consumption_template():
    """Download ready-to-use CSV template for importing consumption / sales history."""
    csv_data = "sku,date,quantity,channel,unit_price,notes\n" \
               "ELEC-101,2026-03-01,8,E-Commerce,2999.00,Standard sale\n" \
               "ELEC-101,2026-03-02,12,Retail Store,2999.00,Weekend promotion\n" \
               "ELEC-102,2026-03-01,25,Wholesale,799.00,Corporate order\n"
    from fastapi.responses import Response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_consumption_template.csv"}
    )
