def test_reorder_recommendation_calculation(client, sample_item_with_history):
    # With current_stock = 20, lead time = 5 days, avg demand ~10/day:
    # Lead time demand ~ 50. Current stock (20) will breach ROP!
    res = client.post(
        f"/api/v1/recommendations/items/{sample_item_with_history.id}",
        json={"service_level": 0.95}
    )
    assert res.status_code == 200
    rec = res.json()
    assert rec["item_id"] == sample_item_with_history.id
    assert rec["lead_time_demand"] > 0
    assert rec["safety_stock"] > 0
    assert rec["reorder_point"] > rec["safety_stock"]
    assert rec["economic_order_quantity"] > 0
    assert rec["urgency_status"] in ["CRITICAL", "REORDER_NOW", "REORDER_SOON"]
    assert rec["recommended_order_quantity"] > 0
    assert rec["estimated_reorder_cost"] > 0


def test_full_pipeline_run(client, sample_item_with_history):
    res = client.post("/api/v1/pipeline/run", json={"service_level": 0.95})
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_items_analyzed"] >= 1
    assert len(summary["recommendations"]) >= 1
    assert "critical_items_count" in summary
    assert "total_estimated_reorder_investment" in summary


def test_health_check_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert len(data["stages"]) == 4


def test_create_purchase_order(client, sample_item):
    payload = {
        "items": [{"item_id": sample_item.id, "quantity": 50}],
        "fulfill_immediately": True,
        "supplier_notes": "Immediate replenishment test"
    }
    res = client.post("/api/v1/recommendations/create-po", json=payload)
    assert res.status_code == 200
    po = res.json()
    assert po["status"] == "FULFILLED"
    assert po["line_items_count"] == 1
    assert po["total_order_cost"] == 50 * sample_item.unit_cost

    # Verify stock updated
    res_stock = client.get(f"/api/v1/stock/items/{sample_item.id}")
    assert res_stock.json()["current_stock"] == 70  # 20 + 50


def test_download_csv_templates(client):
    res_stock = client.get("/api/v1/stock/template-csv")
    assert res_stock.status_code == 200
    assert "text/csv" in res_stock.headers["content-type"]
    assert "sku,name,category" in res_stock.text

    res_cons = client.get("/api/v1/consumption/template-csv")
    assert res_cons.status_code == 200
    assert "text/csv" in res_cons.headers["content-type"]
    assert "sku,date,quantity" in res_cons.text
