def test_create_and_get_item(client):
    payload = {
        "sku": "ITEM-CREATE-1",
        "name": "Mechanical Keyboard",
        "category": "Electronics",
        "current_stock": 50,
        "min_stock_level": 10,
        "max_stock_level": 250,
        "lead_time_days": 7,
        "unit_cost": 65.0,
        "ordering_cost": 40.0,
        "holding_cost_rate": 0.20
    }
    # Create item
    res = client.post("/api/v1/stock/items", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["sku"] == "ITEM-CREATE-1"
    item_id = data["id"]

    # Get item
    res_get = client.get(f"/api/v1/stock/items/{item_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Mechanical Keyboard"


def test_adjust_stock_level(client, sample_item):
    # Adjust stock: restock +30
    adj_payload = {
        "quantity_change": 30,
        "reason": "restock",
        "notes": "PO Received"
    }
    res = client.post(f"/api/v1/stock/items/{sample_item.id}/adjust", json=adj_payload)
    assert res.status_code == 200
    assert res.json()["quantity_change"] == 30

    # Verify updated stock
    res_item = client.get(f"/api/v1/stock/items/{sample_item.id}")
    assert res_item.json()["current_stock"] == 50  # 20 + 30


def test_adjust_stock_negative_below_zero_fails(client, sample_item):
    # Attempt to deduct more stock than available (current is 20)
    adj_payload = {
        "quantity_change": -50,
        "reason": "audit",
        "notes": "Invalid deduction"
    }
    res = client.post(f"/api/v1/stock/items/{sample_item.id}/adjust", json=adj_payload)
    assert res.status_code == 400
    assert "Cannot reduce stock below zero" in res.json()["detail"]


def test_stock_overview(client, sample_item):
    res = client.get("/api/v1/stock/overview")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(i["sku"] == sample_item.sku for i in items)
