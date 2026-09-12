import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Inventory Reorder Prediction System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
    
    # Inventory planning defaults
    DEFAULT_SERVICE_LEVEL_Z: float = 1.65  # 95% cycle service level
    DEFAULT_ANNUAL_HOLDING_RATE: float = 0.20  # 20% annual holding cost rate
    DEFAULT_ORDER_COST: float = 50.0  # Fixed cost per order ($)
    WORKING_DAYS_PER_YEAR: int = 365
    
    # Model defaults
    DEFAULT_FORECAST_HORIZON_DAYS: int = 30
    DEFAULT_MOVING_AVERAGE_WINDOW: int = 7

    # Auth settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours


settings = Settings()
