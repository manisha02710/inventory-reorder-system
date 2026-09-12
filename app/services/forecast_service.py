from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from app.models.stock import Item
from app.models.recommendation import ForecastSnapshot
from app.schemas.forecast import (
    ForecastRequest, ForecastResult, ForecastDailyPoint, ForecastEvaluationMetrics
)
from app.services.consumption_service import ConsumptionService


class ForecastService:
    @staticmethod
    def moving_average_forecast(series: np.ndarray, horizon: int, window: int = 7) -> np.ndarray:
        """Simple Moving Average projection"""
        if len(series) == 0:
            return np.zeros(horizon)
        if len(series) < window:
            window = max(1, len(series))
        
        last_window_mean = float(np.mean(series[-window:]))
        # Constant projection at the window mean
        return np.full(horizon, max(0.0, last_window_mean))

    @staticmethod
    def weighted_moving_average_forecast(series: np.ndarray, horizon: int, window: int = 7) -> np.ndarray:
        """Linear Weighted Moving Average projection"""
        if len(series) == 0:
            return np.zeros(horizon)
        w_len = min(window, len(series))
        weights = np.arange(1, w_len + 1, dtype=float)
        weights /= weights.sum()
        w_val = float(np.sum(series[-w_len:] * weights))
        return np.full(horizon, max(0.0, w_val))

    @staticmethod
    def exponential_smoothing_forecast(series: np.ndarray, horizon: int, alpha: float = 0.3) -> np.ndarray:
        """Single Exponential Smoothing projection"""
        if len(series) == 0:
            return np.zeros(horizon)
        smoothed = series[0]
        for val in series[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed
        return np.full(horizon, max(0.0, float(smoothed)))

    @staticmethod
    def linear_trend_forecast(series: np.ndarray, horizon: int) -> np.ndarray:
        """Linear Trend (OLS) projection"""
        n = len(series)
        if n < 2:
            return np.full(horizon, float(series[0]) if n == 1 else 0.0)
        
        x = np.arange(n)
        # Calculate slope and intercept
        slope, intercept = np.polyfit(x, series, 1)
        
        future_x = np.arange(n, n + horizon)
        preds = slope * future_x + intercept
        return np.clip(preds, a_min=0.0, a_max=None)

    @staticmethod
    def evaluate_model_accuracy(actuals: np.ndarray, predictions: np.ndarray) -> Tuple[float, float, Optional[float]]:
        """Computes MAE, RMSE, and MAPE"""
        if len(actuals) == 0 or len(predictions) == 0:
            return 0.0, 0.0, None
        
        n = min(len(actuals), len(predictions))
        act = actuals[:n]
        pred = predictions[:n]
        
        errors = act - pred
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        
        # MAPE with division by zero protection
        non_zero_mask = act > 0
        if np.any(non_zero_mask):
            mape = float(np.mean(np.abs(errors[non_zero_mask] / act[non_zero_mask])) * 100)
        else:
            mape = None
            
        return round(mae, 3), round(rmse, 3), round(mape, 2) if mape is not None else None

    @classmethod
    def generate_forecast(
        cls, 
        db: Session, 
        item_id: int, 
        req: Optional[ForecastRequest] = None,
        save_snapshot: bool = True
    ) -> ForecastResult:
        if req is None:
            req = ForecastRequest()
            
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(f"Item with id {item_id} not found")

        horizon = req.horizon_days if req.horizon_days else item.lead_time_days
        horizon = max(1, horizon)
        
        # Get historical daily demand (up to 90 days)
        daily_series = ConsumptionService.get_daily_series(db, item_id, days_back=90)
        history_values = daily_series.to_numpy(dtype=float)
        
        if len(history_values) == 0 or np.all(history_values == 0):
            # No consumption history fallback
            fallback_mean = 1.0  # nominal baseline
            predictions = np.full(horizon, fallback_mean)
            model_used = "baseline_flat"
            mae, rmse, mape = 0.0, 0.0, 0.0
            comparison = {}
        else:
            # Model selection logic
            split_point = max(len(history_values) - 14, int(len(history_values) * 0.8))
            train = history_values[:split_point]
            test = history_values[split_point:]
            
            candidate_models = {
                "moving_average": lambda arr, h: cls.moving_average_forecast(arr, h, window=req.window_size or 7),
                "weighted_moving_average": lambda arr, h: cls.weighted_moving_average_forecast(arr, h, window=req.window_size or 7),
                "exponential_smoothing": lambda arr, h: cls.exponential_smoothing_forecast(arr, h, alpha=req.alpha or 0.3),
                "linear_trend": lambda arr, h: cls.linear_trend_forecast(arr, h),
            }
            
            comparison = {}
            if len(test) >= 3 and len(train) >= 7:
                for name, fn in candidate_models.items():
                    test_pred = fn(train, len(test))
                    c_mae, _, _ = cls.evaluate_model_accuracy(test, test_pred)
                    comparison[name] = c_mae
            else:
                comparison = {k: 1.0 for k in candidate_models.keys()}
            
            if req.model_type and req.model_type != "auto" and req.model_type in candidate_models:
                model_used = req.model_type
            else:
                # Auto select best model with lowest MAE
                model_used = min(comparison.items(), key=lambda x: x[1])[0]
            
            # Predict full horizon using all history
            predictions = candidate_models[model_used](history_values, horizon)
            
            # Estimate validation metrics
            test_preds = candidate_models[model_used](history_values[:-min(14, len(history_values))], min(14, len(history_values)))
            mae, rmse, mape = cls.evaluate_model_accuracy(history_values[-len(test_preds):], test_preds)

        # Standard error for prediction intervals
        noise_margin = max(1.0, rmse * 1.65 if rmse > 0 else float(np.std(history_values)) if len(history_values) > 1 else 1.0)
        
        # Build daily points
        today = date.today()
        daily_points = []
        for i in range(horizon):
            future_d = today + timedelta(days=i + 1)
            pred_val = float(predictions[i])
            daily_points.append(ForecastDailyPoint(
                date=future_d.strftime("%Y-%m-%d"),
                predicted_quantity=round(pred_val, 2),
                lower_bound=round(max(0.0, pred_val - noise_margin), 2),
                upper_bound=round(pred_val + noise_margin, 2)
            ))

        total_forecast = float(np.sum(predictions))
        daily_mean = float(np.mean(predictions))
        hist_mean = float(np.mean(history_values)) if len(history_values) > 0 else 0.0

        metrics = ForecastEvaluationMetrics(mae=mae, rmse=rmse, mape=mape)

        # Persist snapshot if enabled
        if save_snapshot:
            snapshot = ForecastSnapshot(
                item_id=item.id,
                forecast_date=today,
                model_name=model_used,
                horizon_days=horizon,
                total_forecasted_demand=round(total_forecast, 2),
                daily_forecasted_mean=round(daily_mean, 2),
                daily_predictions=[p.predicted_quantity for p in daily_points],
                mae=mae,
                rmse=rmse,
                mape=mape
            )
            db.add(snapshot)
            db.commit()

        # Extract recent historical points for frontend charting (last 21 days)
        recent_tail = daily_series.tail(21)
        historical_points = [
            {"date": ts.strftime("%Y-%m-%d"), "quantity": int(val)}
            for ts, val in recent_tail.items()
        ]

        return ForecastResult(
            item_id=item.id,
            sku=item.sku,
            item_name=item.name,
            model_name=model_used,
            horizon_days=horizon,
            total_forecasted_demand=round(total_forecast, 2),
            daily_forecasted_mean=round(daily_mean, 2),
            metrics=metrics,
            historical_daily_mean=round(hist_mean, 2),
            historical_points=historical_points,
            daily_predictions=daily_points,
            comparison_summary=comparison
        )
