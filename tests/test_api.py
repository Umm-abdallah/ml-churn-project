"""Tests de l'API (tests d'intégration : HTTP -> FastAPI -> modèle)."""
import pytest


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"
    assert response.json()["model_loaded"] is True


def test_model_info(client):
    response = client.get("/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["model"]
    assert data["version"]
    assert len(data["features"]) == 6


def test_prediction(client, payload):
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    assert "model_version" in data
    assert data["prediction"] in {"CHURN", "NO_CHURN"}
    assert 0.0 <= data["probability"] <= 1.0
    assert response.headers["X-Request-ID"] == data["request_id"]


def test_prediction_is_deterministic(client, payload):
    first = client.post("/predict", json=payload).json()
    second = client.post("/predict", json=payload).json()
    assert first["prediction"] == second["prediction"]
    assert first["probability"] == second["probability"]


def test_prediction_consistent_with_threshold(client, payload):
    data = client.post("/predict", json=payload).json()
    expected = "CHURN" if data["probability"] >= 0.5 else "NO_CHURN"
    assert data["prediction"] == expected


@pytest.mark.parametrize("field,value", [
    ("age", -5),
    ("anciennete", -1),
    ("nb_reclamations", "beaucoup"),
    ("montant_mensuel", -100),
])
def test_prediction_invalid_values(client, payload, field, value):
    payload[field] = value
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_prediction_missing_field(client, payload):
    payload.pop("revenu")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_metrics_exposed(client, payload):
    client.post("/predict", json=payload)
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body
    assert "churn_predictions_total" in body
    assert "churn_prediction_duration_seconds" in body


def test_ui_served(client):
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "predict-btn" in response.text
