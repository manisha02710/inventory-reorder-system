import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.v1 import api_v1_router
from app.models.stock import Item
from data.seed_data import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite schema
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed database if empty
    db = SessionLocal()
    try:
        if db.query(Item).count() == 0:
            print("Database is empty. Populating sample retail/warehouse data...")
            seed_database()
    finally:
        db.close()
        
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, "templates")
static_dir = os.path.join(base_dir, "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Mount API v1 routes
app.include_router(api_v1_router)


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"], include_in_schema=False)
async def serve_dashboard(request: Request):
    """Interactive visual dashboard for all 4 stages of inventory reordering."""
    return templates.TemplateResponse(request=request, name="index.html", context={"app_name": settings.APP_NAME})


@app.get("/health", tags=["Health"], summary="System health check")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "stages": [
            "1. Stock Data",
            "2. Consumption Data",
            "3. Forecasting",
            "4. Reorder Recommendation"
        ]
    }