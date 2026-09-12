import math
from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.config import settings
from app.models.stock import Item
from app.models.recommendation import ReorderRecommendation
from app.schemas.recommendation import (
    ReorderCalculationParameters, ReorderRecommendationResponse, PipelineSummary
)
from app.services.consumption_service import ConsumptionService
from app.services.forecast_service import ForecastService


class ReorderService:
    # Service level Z-score mapping
    Z_TABLE = {
        0.80: 0.84,
        0.85: 1.04,
        0.90: 1.28,
        0.95: 1.645,
        0.98: 2.055,
        0.99: 2.326,
    }

    @classmethod
    def get_z_score(cls, service_level: float) -> float:
        """Finds closest Z-score or computes normal quantile approximation"""
        # Exact lookup if match
        for sl, z in cls.Z_TABLE.items():
            if abs(sl - service_level) < 0.005:
                return z
        # Approximation formula for normal quantile
        # Abramowitz and Stegun approximation
        p = service_level
        if p >= 1.0:
            return 3.0
        if p <= 0.5:
            return 0.0
        t = math.sqrt(-2.0 * math.log(1.0 - p))
        c0 = 2.515517
        c1 = 0.802853
        c2 = 0.010328
        d1 = 1.432788
        d2 = 0.189269
        d3 = 0.001308
        z = t - ((c2 * t + c1) * t + c0) / (((d3 * t + d2) * t + d1) * t + 1.0)
        return round(z, 3)

    @classmethod
    def calculate_recommendation(
        cls,
        db: Session,
        item_id: int,
        params: Optional[ReorderCalculationParameters] = None,
        persist: bool = True
    ) -> ReorderRecommendationResponse:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(f"Item with id {item_id} not found")

        params = params or ReorderCalculationParameters()
        lead_time = params.lead_time_days_override or item.lead_time_days
        order_cost = params.ordering_cost_override if params.ordering_cost_override is not None else item.ordering_cost
        holding_rate = params.holding_cost_rate_override if params.holding_cost_rate_override is not None else item.holding_cost_rate
        service_level = params.service_level or settings.DEFAULT_SERVICE_LEVEL_Z

        # Stage 2: Historical metrics
        metrics = ConsumptionService.get_consumption_metrics(db, item_id, days_back=90)
        avg_daily = metrics.average_daily_demand
        std_dev = metrics.demand_standard_deviation

        # Stage 3: Forecast
        forecast = ForecastService.generate_forecast(db, item_id, save_snapshot=False)
        forecast_daily = forecast.daily_forecasted_mean

        # Use blended or forecast daily demand for future planning
        effective_daily_demand = max(forecast_daily, avg_daily, 0.5)

        # Stage 4: Formulas
        # 1. Lead Time Demand (LTD)
        ltd = effective_daily_demand * lead_time

        # 2. Safety Stock (SS)
        if item.safety_stock_override is not None:
            safety_stock = item.safety_stock_override
        else:
            z = cls.get_z_score(service_level)
            # SS = Z * sigma_d * sqrt(LeadTime)
            calc_ss = z * max(std_dev, 0.5) * math.sqrt(lead_time)
            # Ensure minimum safety stock covers at least 1-2 days
            safety_stock = int(math.ceil(max(calc_ss, item.min_stock_level, 1)))

        # 3. Reorder Point (ROP) = LTD + SS
        reorder_point = int(math.ceil(ltd + safety_stock))

        # 4. Economic Order Quantity (EOQ)
        # Annual demand D = effective_daily_demand * 365
        annual_demand = effective_daily_demand * settings.WORKING_DAYS_PER_YEAR
        holding_cost_per_unit = max(item.unit_cost * holding_rate, 0.10)
        
        # EOQ = sqrt((2 * D * S) / H)
        eoq_raw = math.sqrt((2.0 * annual_demand * order_cost) / holding_cost_per_unit)
        eoq = max(1, int(round(eoq_raw)))

        # 5. Current Stock & Days until stockout
        current_stock = item.current_stock
        days_until_stockout = round(current_stock / effective_daily_demand, 1) if effective_daily_demand > 0 else 999.0

        # 6. Urgency classification & Recommended quantity
        urgency_color_map = {
            "CRITICAL": "red",
            "REORDER_NOW": "orange",
            "REORDER_SOON": "yellow",
            "HEALTHY": "green",
            "OVERSTOCK": "purple"
        }

        if current_stock <= safety_stock:
            urgency = "CRITICAL"
            shortfall = reorder_point - current_stock
            rec_qty = max(eoq, shortfall + safety_stock)
            rationale = (
                f"CRITICAL: Current stock ({current_stock}) is below safety stock ({safety_stock}). "
                f"Stockout projected in {days_until_stockout} days vs lead time of {lead_time} days. "
                f"Immediate purchase order required."
            )
        elif current_stock <= reorder_point:
            urgency = "REORDER_NOW"
            shortfall = reorder_point - current_stock
            rec_qty = max(eoq, shortfall)
            rationale = (
                f"REORDER NOW: Stock ({current_stock}) has breached reorder point ({reorder_point}). "
                f"Expected lead-time demand is {round(ltd, 1)} units. Place replenishment order of {rec_qty} units."
            )
        elif current_stock <= int(reorder_point * 1.15):
            urgency = "REORDER_SOON"
            rec_qty = eoq
            rationale = (
                f"REORDER SOON: Stock ({current_stock}) is within 15% of reorder point ({reorder_point}). "
                f"Estimated supply remaining: {days_until_stockout} days."
            )
        elif current_stock > item.max_stock_level:
            urgency = "OVERSTOCK"
            rec_qty = 0
            excess = current_stock - item.max_stock_level
            rationale = (
                f"OVERSTOCK: Current stock ({current_stock}) exceeds maximum warehouse target ({item.max_stock_level}) "
                f"by {excess} units. Do not reorder; promote sales to reduce holding costs."
            )
        else:
            urgency = "HEALTHY"
            rec_qty = 0
            rationale = (
                f"HEALTHY: Stock level ({current_stock}) is comfortably above ROP ({reorder_point}). "
                f"Safe buffer of {days_until_stockout} days remaining."
            )

        # Cap recommended order quantity to not breach max stock if order arrives immediately
        if rec_qty > 0 and item.max_stock_level > 0:
            max_allowed = max(0, item.max_stock_level - current_stock)
            if max_allowed > 0:
                rec_qty = min(rec_qty, max(max_allowed, eoq))

        estimated_reorder_cost = round(rec_qty * item.unit_cost, 2)
        generated_at = datetime.now(timezone.utc)

        # Persist to database if requested
        db_rec = None
        if persist:
            db_rec = ReorderRecommendation(
                item_id=item.id,
                generated_at=generated_at,
                current_stock=current_stock,
                avg_daily_demand=round(avg_daily, 2),
                demand_std_dev=round(std_dev, 2),
                lead_time_days=lead_time,
                lead_time_demand=round(ltd, 2),
                safety_stock=safety_stock,
                reorder_point=reorder_point,
                economic_order_quantity=eoq,
                recommended_order_quantity=rec_qty,
                urgency_status=urgency,
                days_until_stockout=days_until_stockout,
                estimated_reorder_cost=estimated_reorder_cost,
                rationale=rationale
            )
            db.add(db_rec)
            db.commit()
            db.refresh(db_rec)

        return ReorderRecommendationResponse(
            id=db_rec.id if db_rec else None,
            item_id=item.id,
            sku=item.sku,
            item_name=item.name,
            category=item.category,
            current_stock=current_stock,
            min_stock_level=item.min_stock_level,
            max_stock_level=item.max_stock_level,
            unit_cost=item.unit_cost,
            avg_daily_demand=round(avg_daily, 2),
            demand_std_dev=round(std_dev, 2),
            forecast_daily_mean=round(forecast_daily, 2),
            forecast_model_used=forecast.model_name,
            lead_time_days=lead_time,
            lead_time_demand=round(ltd, 2),
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            economic_order_quantity=eoq,
            recommended_order_quantity=rec_qty,
            urgency_status=urgency,
            urgency_color=urgency_color_map[urgency],
            days_until_stockout=days_until_stockout,
            estimated_reorder_cost=estimated_reorder_cost,
            rationale=rationale,
            generated_at=generated_at
        )

    @classmethod
    def run_pipeline(cls, db: Session, params: Optional[ReorderCalculationParameters] = None) -> PipelineSummary:
        """Executes full 4-stage analysis for all inventory items"""
        items = db.query(Item).all()
        recommendations = []
        
        crit_count = 0
        now_count = 0
        soon_count = 0
        healthy_count = 0
        overstock_count = 0
        total_investment = 0.0

        for item in items:
            rec = cls.calculate_recommendation(db, item.id, params=params, persist=True)
            recommendations.append(rec)
            total_investment += rec.estimated_reorder_cost

            if rec.urgency_status == "CRITICAL":
                crit_count += 1
            elif rec.urgency_status == "REORDER_NOW":
                now_count += 1
            elif rec.urgency_status == "REORDER_SOON":
                soon_count += 1
            elif rec.urgency_status == "HEALTHY":
                healthy_count += 1
            elif rec.urgency_status == "OVERSTOCK":
                overstock_count += 1

        # Sort recommendations by urgency: CRITICAL first, then REORDER_NOW, REORDER_SOON, HEALTHY, OVERSTOCK
        order_rank = {"CRITICAL": 0, "REORDER_NOW": 1, "REORDER_SOON": 2, "HEALTHY": 3, "OVERSTOCK": 4}
        recommendations.sort(key=lambda x: order_rank.get(x.urgency_status, 99))

        return PipelineSummary(
            total_items_analyzed=len(items),
            critical_items_count=crit_count,
            reorder_now_count=now_count,
            reorder_soon_count=soon_count,
            healthy_count=healthy_count,
            overstock_count=overstock_count,
            total_estimated_reorder_investment=round(total_investment, 2),
            recommendations=recommendations
        )
