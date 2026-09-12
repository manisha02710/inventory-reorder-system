import random
from datetime import date, timedelta
from app.database import SessionLocal, engine, Base
from app.models.stock import Item, StockAdjustment
from app.models.consumption import ConsumptionTransaction
from app.services.reorder_service import ReorderService

def seed_database():
    print("Creating database tables if not present...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_count = db.query(Item).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} items. Skipping seed.")
            return

        print("Seeding inventory items across categories...")
        items_data = [
            {
                "sku": "ELEC-101",
                "name": "Noise-Cancelling Bluetooth Headphones",
                "category": "Electronics",
                "current_stock": 18,       # Critical low!
                "min_stock_level": 25,
                "max_stock_level": 300,
                "lead_time_days": 10,
                "unit_cost": 2499.0,
                "ordering_cost": 350.0,
                "holding_cost_rate": 0.20,
                "base_daily_demand": 8,
                "demand_variance": 3,
                "trend": 0.05
            },
            {
                "sku": "ELEC-102",
                "name": "65W GaN Fast Charger USB-C",
                "category": "Electronics",
                "current_stock": 42,       # Reorder now!
                "min_stock_level": 30,
                "max_stock_level": 400,
                "lead_time_days": 6,
                "unit_cost": 699.0,
                "ordering_cost": 150.0,
                "holding_cost_rate": 0.15,
                "base_daily_demand": 14,
                "demand_variance": 4,
                "trend": 0.0
            },
            {
                "sku": "OFFC-201",
                "name": "Ergonomic Lumbar Support Office Chair",
                "category": "Office",
                "current_stock": 110,      # Healthy
                "min_stock_level": 20,
                "max_stock_level": 250,
                "lead_time_days": 14,
                "unit_cost": 7999.0,
                "ordering_cost": 800.0,
                "holding_cost_rate": 0.25,
                "base_daily_demand": 4,
                "demand_variance": 2,
                "trend": 0.0
            },
            {
                "sku": "OFFC-202",
                "name": "Wireless Multi-Device Mouse",
                "category": "Office",
                "current_stock": 25,       # Reorder soon
                "min_stock_level": 20,
                "max_stock_level": 350,
                "lead_time_days": 7,
                "unit_cost": 999.0,
                "ordering_cost": 200.0,
                "holding_cost_rate": 0.18,
                "base_daily_demand": 9,
                "demand_variance": 3,
                "trend": 0.08
            },
            {
                "sku": "GROC-301",
                "name": "Single-Origin Dark Roast Coffee Beans 1kg",
                "category": "Groceries",
                "current_stock": 95,       # Healthy
                "min_stock_level": 30,
                "max_stock_level": 400,
                "lead_time_days": 4,
                "unit_cost": 850.0,
                "ordering_cost": 150.0,
                "holding_cost_rate": 0.20,
                "base_daily_demand": 12,
                "demand_variance": 5,
                "trend": 0.0
            },
            {
                "sku": "GROC-302",
                "name": "Ceremonial Uji Matcha Green Tea 100g",
                "category": "Groceries",
                "current_stock": 380,      # Overstocked!
                "min_stock_level": 15,
                "max_stock_level": 150,
                "lead_time_days": 8,
                "unit_cost": 1450.0,
                "ordering_cost": 250.0,
                "holding_cost_rate": 0.22,
                "base_daily_demand": 3,
                "demand_variance": 1,
                "trend": -0.01
            }
        ]

        created_items = []
        for item_info in items_data:
            item = Item(
                sku=item_info["sku"],
                name=item_info["name"],
                category=item_info["category"],
                current_stock=item_info["current_stock"],
                min_stock_level=item_info["min_stock_level"],
                max_stock_level=item_info["max_stock_level"],
                lead_time_days=item_info["lead_time_days"],
                unit_cost=item_info["unit_cost"],
                ordering_cost=item_info["ordering_cost"],
                holding_cost_rate=item_info["holding_cost_rate"]
            )
            db.add(item)
            db.flush()
            created_items.append((item, item_info))

        print("Generating 75 days of historical consumption transactions...")
        today = date.today()
        channels = ["Retail Store", "E-Commerce Web", "Mobile App", "B2B Wholesale"]
        
        random.seed(42)  # Deterministic seed for reproducible testing
        
        for item, info in created_items:
            base = info["base_daily_demand"]
            var = info["demand_variance"]
            trend = info["trend"]
            
            for days_ago in range(75, 0, -1):
                t_date = today - timedelta(days=days_ago)
                
                # Introduce slight weekend spike and trend
                day_of_week = t_date.weekday()
                weekend_factor = 1.3 if day_of_week in [4, 5] else 1.0
                trend_factor = 1.0 + (trend * (75 - days_ago))
                
                # Daily demand with normal noise
                noise = random.randint(-var, var)
                daily_total = max(1, int(round((base + noise) * weekend_factor * trend_factor)))
                
                # Split daily demand into 1-3 transactions
                num_transactions = random.randint(1, 3)
                portions = [random.randint(1, 5) for _ in range(num_transactions)]
                portion_sum = sum(portions)
                
                for p in portions:
                    t_qty = max(1, int(round(daily_total * (p / portion_sum))))
                    trans = ConsumptionTransaction(
                        item_id=item.id,
                        transaction_date=t_date,
                        quantity=t_qty,
                        channel=random.choice(channels),
                        unit_price=round(item.unit_cost * 1.45, 2)
                    )
                    db.add(trans)

        db.commit()
        print("Database seeded successfully with items and consumption records!")

        # Run initial recommendation calculation
        print("Running initial recommendation pipeline...")
        summary = ReorderService.run_pipeline(db)
        print(f"Pipeline executed: {summary.total_items_analyzed} items analyzed, {summary.critical_items_count} critical, {summary.reorder_now_count} reorder now.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
