import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.v1 import api_v1_router
from app.api.v1.auth import router as auth_router
from app.models.stock import Item
from app.models.user import User
from app.auth import get_password_hash
from data.seed_data import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    Base.metadata.create_all(bind=engine)

    # Auto-seed sample catalog if database is fresh
    db = SessionLocal()
    try:
        if db.query(Item).count() == 0:
            print("Database is empty. Populating sample retail/warehouse data...")
            seed_database()
    except Exception as e:
        print("Lifespan initialization error:", e)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Inventory Reorder Prediction System (4 Stages)
    An automated stock replenishment decision support system powered by FastAPI:
    1. **Stage 1: Stock Data** - Current inventory, lead times, safety thresholds, and SKU catalogs.
    2. **Stage 2: Consumption Data** - Transaction outflows, daily demand volatility, and frequency analysis.
    3. **Stage 3: Demand Forecasting** - Time-series projections (Moving Average, Exponential Smoothing, Linear Trend) with automatic model validation.
    4. **Stage 4: Reorder Recommendations** - Scientific calculation of Dynamic Safety Stock, Reorder Point (ROP), Economic Order Quantity (EOQ), urgency status, and recommended purchase order volumes.
    """,
    lifespan=lifespan
)

# CORS middleware for open integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Templates
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, "templates")
static_dir = os.path.join(base_dir, "static")

if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


# Mount Routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(api_v1_router)


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"], include_in_schema=False)
async def serve_dashboard(request: Request, user=Depends(get_current_user_from_cookie)):
    """Interactive visual dashboard for all 4 stages of inventory reordering."""
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"app_name": settings.APP_NAME, "user": user}
    )


@app.get("/login", response_class=HTMLResponse, tags=["Auth"], include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


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
