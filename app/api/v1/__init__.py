from fastapi import APIRouter
from app.api.v1.stock import router as stock_router
from app.api.v1.consumption import router as consumption_router
from app.api.v1.forecast import router as forecast_router
from app.api.v1.recommendation import router as recommendation_router
from app.api.v1.pipeline import router as pipeline_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(stock_router, prefix="/stock", tags=["Stage 1: Stock Data"])
api_v1_router.include_router(consumption_router, prefix="/consumption", tags=["Stage 2: Consumption Data"])
api_v1_router.include_router(forecast_router, prefix="/forecast", tags=["Stage 3: Forecasting"])
api_v1_router.include_router(recommendation_router, prefix="/recommendations", tags=["Stage 4: Reorder Recommendations"])
api_v1_router.include_router(pipeline_router, prefix="/pipeline", tags=["Pipeline & Batch Execution"])
