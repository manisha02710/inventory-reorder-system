def test_forecast_auto_model(client, sample_item_with_history):
    payload = {
        "horizon_days": 14,
        "model_type": "auto"
    }
    res = client.post(f"/api/v1/forecast/items/{sample_item_with_history.id}", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["horizon_days"] == 14
    assert data["model_name"] in ["moving_average", "weighted_moving_average", "exponential_smoothing", "linear_trend"]
    assert len(data["daily_predictions"]) == 14
    assert data["daily_forecasted_mean"] > 0
    assert data["metrics"]["mae"] >= 0


def test_forecast_specific_models(client, sample_item_with_history):
    models = ["moving_average", "exponential_smoothing", "linear_trend"]
    for m in models:
        payload = {
            "horizon_days": 7,
            "model_type": m
        }
        res = client.post(f"/api/v1/forecast/items/{sample_item_with_history.id}", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["model_name"] == m
        assert len(data["daily_predictions"]) == 7


def test_forecast_models_endpoint(client):
    res = client.get("/api/v1/forecast/models")
    assert res.status_code == 200
    assert "models" in res.json()
    assert len(res.json()["models"]) >= 4
