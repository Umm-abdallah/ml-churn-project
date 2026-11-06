"""API FastAPI de prédiction du churn.

Corrections par rapport à l'énoncé :
* le chemin du modèle ne dépend plus du dossier courant (MODEL_PATH configurable) ;
* nom et version du modèle lus dans models/metadata.json au lieu d'être écrits en dur ;
* les données sont envoyées au modèle sous forme de DataFrame avec les noms de
  colonnes d'entraînement (sinon scikit learn émet un avertissement et un
  changement d'ordre des champs fausserait silencieusement les prédictions) ;
* validation des entrées (valeurs négatives ou absurdes refusées en 422) ;
* print remplacé par des logs JSON structurés (qui, quand, quoi, quel modèle,
  quel résultat, combien de temps, quelle erreur) envoyés vers la console et un
  fichier lu par Logstash ;
* gestion des erreurs : log ERROR + réponse 500 propre ;
* métriques métier Prometheus en plus des métriques HTTP ;
* /health vérifie réellement que le modèle est chargé ;
* interface web servie sur /ui (testée par Selenium).
"""
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "models" / "model.pkl"))
METADATA_PATH = Path(os.getenv("METADATA_PATH", MODEL_PATH.parent / "metadata.json"))
LOG_FILE = os.getenv("LOG_FILE", str(ROOT / "logs" / "api.log"))
FRONTEND_DIR = ROOT / "frontend"
APP_VERSION = "1.0.0"

DEFAULT_FEATURES = [
    "age", "anciennete", "revenu",
    "nb_reclamations", "montant_mensuel", "retards_paiement",
]


# ---------------------------------------------------------------- logging JSON
class JsonFormatter(logging.Formatter):
    """Une ligne JSON par événement : directement exploitable par Logstash."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "@timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "ml-churn-api",
        }
        payload.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("ml_churn_api")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    logger.handlers.clear()
    logger.propagate = False
    formatter = JsonFormatter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if LOG_FILE:
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


logger = setup_logging()


def log(level: int, message: str, **fields) -> None:
    logger.log(level, message, extra={"extra_fields": fields})


# ------------------------------------------------------------ métriques métier
PREDICTIONS = Counter(
    "churn_predictions_total", "Nombre de prédictions", ["result", "model_version"]
)
PREDICTION_ERRORS = Counter(
    "churn_prediction_errors_total", "Nombre d'erreurs de prédiction", ["model_version"]
)
PREDICTION_LATENCY = Histogram(
    "churn_prediction_duration_seconds",
    "Durée d'inférence du modèle",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)
PREDICTION_PROBABILITY = Histogram(
    "churn_prediction_probability",
    "Distribution des probabilités de churn (détection de dérive)",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)
MODEL_LOADED = Gauge("churn_model_loaded", "1 si le modèle est chargé")


# --------------------------------------------------------------- état du modèle
class ModelStore:
    model = None
    metadata: dict = {}


store = ModelStore()


def load_model() -> None:
    store.model = joblib.load(MODEL_PATH)
    if METADATA_PATH.exists():
        store.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    else:
        store.metadata = {"model_display_name": type(store.model).__name__,
                          "model_version": "unknown", "features": DEFAULT_FEATURES}
    MODEL_LOADED.set(1)
    log(logging.INFO, "Model loaded",
        event_type="model_loaded",
        model_name=store.metadata.get("model_display_name"),
        model_version=store.metadata.get("model_version"),
        model_path=str(MODEL_PATH))


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        load_model()
    except Exception:
        MODEL_LOADED.set(0)
        logger.exception("Model loading failed", extra={"extra_fields": {
            "event_type": "model_load_error", "model_path": str(MODEL_PATH)}})
        raise
    yield


app = FastAPI(
    title="Churn Prediction API",
    version=APP_VERSION,
    description="Prédiction du churn des clients d'un opérateur télécom",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Ajoute un identifiant de requête (réponse et logs) : répond à « qui ? »."""
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# --------------------------------------------------------------------- schémas
class ClientData(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "age": 35, "anciennete": 5, "revenu": 450000,
        "nb_reclamations": 2, "montant_mensuel": 25000, "retards_paiement": 2,
    }})

    age: int = Field(..., ge=18, le=100, description="Âge du client")
    anciennete: int = Field(..., ge=0, le=600, description="Ancienneté en mois")
    revenu: float = Field(..., ge=0, description="Revenu mensuel")
    nb_reclamations: int = Field(..., ge=0, le=100)
    montant_mensuel: float = Field(..., ge=0, description="Facture mensuelle")
    retards_paiement: int = Field(..., ge=0, le=100)


class PredictionResponse(BaseModel):
    prediction: str
    probability: float
    model_version: str
    duration_ms: float
    request_id: str


# -------------------------------------------------------------------- routes
@app.get("/")
def root():
    return {"application": "Churn Prediction API", "version": APP_VERSION,
            "status": "running", "docs": "/docs", "ui": "/ui/"}


@app.get("/health")
def health():
    """Liveness + readiness : UP seulement si le modèle est chargé."""
    if store.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "UP", "model_loaded": True,
            "model_version": store.metadata.get("model_version")}


@app.get("/model/info")
def model_info():
    md = store.metadata
    return {
        "model": md.get("model_display_name"),
        "version": md.get("model_version"),
        "trained_at": md.get("trained_at"),
        "features": md.get("features"),
        "metrics": md.get("metrics"),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(data: ClientData, request: Request):
    start = time.perf_counter()
    request_id = request.state.request_id
    version = str(store.metadata.get("model_version", "unknown"))
    client_ip = request.client.host if request.client else None
    features = store.metadata.get("features", DEFAULT_FEATURES)

    try:
        values = pd.DataFrame([data.model_dump()])[features]
        prediction = int(store.model.predict(values)[0])
        probability = float(store.model.predict_proba(values)[0][1])
    except Exception as exc:
        duration = time.perf_counter() - start
        PREDICTION_ERRORS.labels(model_version=version).inc()
        logger.exception("Prediction error", extra={"extra_fields": {
            "event_type": "prediction_error", "request_id": request_id,
            "client_ip": client_ip, "model_version": version,
            "response_time_ms": round(duration * 1000, 2),
            "error": f"{type(exc).__name__}: {exc}"}})
        raise HTTPException(status_code=500, detail="Prediction error") from exc

    duration = time.perf_counter() - start
    label = "CHURN" if prediction == 1 else "NO_CHURN"

    PREDICTIONS.labels(result=label, model_version=version).inc()
    PREDICTION_LATENCY.observe(duration)
    PREDICTION_PROBABILITY.observe(probability)

    log(logging.INFO, "Prediction request",
        event_type="prediction", request_id=request_id, client_ip=client_ip,
        model_name=store.metadata.get("model_display_name"), model_version=version,
        prediction=label, probability=round(probability, 4),
        response_time_ms=round(duration * 1000, 2), input=data.model_dump())

    return PredictionResponse(
        prediction=label,
        probability=round(probability, 4),
        model_version=version,
        duration_ms=round(duration * 1000, 2),
        request_id=request_id,
    )


# ------------------------------------------------------- interface web + metrics
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")


Instrumentator(
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, include_in_schema=False)
