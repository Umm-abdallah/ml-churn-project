"""Tests unitaires du modèle et des données (sans passer par l'API)."""
import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
FEATURES = ["age", "anciennete", "revenu",
            "nb_reclamations", "montant_mensuel", "retards_paiement"]


@pytest.fixture(scope="module")
def model():
    return joblib.load(ROOT / "models" / "model.pkl")


@pytest.fixture(scope="module")
def metadata():
    return json.loads((ROOT / "models" / "metadata.json").read_text(encoding="utf-8"))


def test_dataset_schema():
    df = pd.read_csv(ROOT / "data" / "raw" / "churn.csv")
    assert list(df.columns) == FEATURES + ["churn"]
    assert len(df) == 2000
    assert df.isnull().sum().sum() == 0
    assert set(df["churn"].unique()) == {0, 1}


def test_metadata_features(metadata):
    assert metadata["features"] == FEATURES
    assert metadata["model_version"]


def test_model_predicts_proba(model):
    X = pd.DataFrame([[35, 5, 450000, 2, 25000, 2]], columns=FEATURES)
    proba = model.predict_proba(X)[0]
    assert len(proba) == 2
    assert abs(sum(proba) - 1) < 1e-6


def test_model_quality_gate(metadata):
    # Seuil minimal : un modèle qui ne bat pas le hasard ne doit pas être déployé
    assert metadata["metrics"]["roc_auc"] >= 0.60


def test_long_tenure_reduces_churn_risk(model):
    # Test métier : une forte ancienneté doit faire baisser le risque
    new = pd.DataFrame([[35, 3, 450000, 2, 25000, 2]], columns=FEATURES)
    old = pd.DataFrame([[35, 110, 450000, 2, 25000, 2]], columns=FEATURES)
    assert model.predict_proba(old)[0][1] < model.predict_proba(new)[0][1]
