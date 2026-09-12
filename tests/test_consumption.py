from datetime import date


def test_log_consumption(client, sample_item):
    today = date.today().isoformat()
    payload = {
        "transaction_date": today,
        "quantity": 8,
        "channel": "Retail Store",
        "unit_price": 30.0,
        "notes": "Storefront sale"
    }
    res = client.post(f"/api/v1/consumption/items/{sample_item.id}", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["quantity"] == 8
    assert data["channel"] == "Retail Store"


def test_consumption_history_and_metrics(client, sample_item_with_history):
    # Verify history
    res_hist = client.get(f"/api/v1/consumption/items/{sample_item_with_history.id}/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) == 30

    # Verify statistical metrics
    res_metrics = client.get(f"/api/v1/consumption/items/{sample_item_with_history.id}/metrics?days_back=90")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()
    assert metrics["item_id"] == sample_item_with_history.id
    assert metrics["total_records"] == 30
    assert metrics["average_daily_demand"] > 0
    assert metrics["demand_standard_deviation"] >= 0
    assert len(metrics["recent_history"]) > 0


def test_bulk_consumption(client, sample_item):
    today = date.today().isoformat()
    bulk_data = [
        {"sku": sample_item.sku, "transaction_date": today, "quantity": 5, "channel": "Online"},
        {"sku": sample_item.sku, "transaction_date": today, "quantity": 12, "channel": "Retail"}
    ]
    res = client.post("/api/v1/consumption/bulk", json=bulk_data)
    assert res.status_code == 200
    assert res.json()["created_count"] == 2
