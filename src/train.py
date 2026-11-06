"""Entraînement et comparaison de trois modèles de classification du churn.

Corrections par rapport à l'énoncé :
* chemins robustes et création du dossier models/ ;
* la séparation des features et l'ordre des colonnes sont fixés (FEATURES) et
  enregistrés avec le modèle, pour que l'API envoie exactement les mêmes colonnes ;
* ajout du ROC AUC (métrique adaptée à un score de probabilité) et de zero_division ;
* le modèle retenu est choisi sur les résultats (F1 en validation croisée sur le
  jeu d'entraînement) au lieu d'être imposé sans justification. On peut forcer un
  modèle : MODEL_NAME=random_forest python src/train.py ;
* le Random Forest est régularisé (max_depth, min_samples_leaf), sans quoi il
  sur apprend fortement sur ce dataset bruité ;
* sauvegarde d'un fichier metadata.json (version, date, métriques, features) et
  d'une copie versionnée du modèle : c'est la base du versionnement MLOps.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw" / "churn.csv"
MODELS_DIR = ROOT / "models"

FEATURES = [
    "age",
    "anciennete",
    "revenu",
    "nb_reclamations",
    "montant_mensuel",
    "retards_paiement",
]
TARGET = "churn"
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")
RANDOM_STATE = 42

DISPLAY_NAMES = {
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
}


def build_models() -> dict:
    return {
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000)),
        ]),
        "decision_tree": DecisionTreeClassifier(
            max_depth=5, random_state=RANDOM_STATE
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=10,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


def evaluate(model, X_test, y_test) -> dict:
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    return {
        "accuracy": round(accuracy_score(y_test, predictions), 4),
        "precision": round(precision_score(y_test, predictions, zero_division=0), 4),
        "recall": round(recall_score(y_test, predictions, zero_division=0), 4),
        "f1": round(f1_score(y_test, predictions, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, probabilities), 4),
    }


def main() -> None:
    df = pd.read_csv(DATA)
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    models = build_models()
    results = {}

    for name, model in models.items():
        print(f"\nEntraînement : {name}")
        cv_f1 = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1")
        model.fit(X_train, y_train)
        metrics = evaluate(model, X_test, y_test)
        metrics["cv_f1_mean"] = round(float(cv_f1.mean()), 4)
        metrics["cv_f1_std"] = round(float(cv_f1.std()), 4)
        results[name] = metrics
        print(metrics)

    forced = os.getenv("MODEL_NAME")
    if forced:
        if forced not in models:
            raise SystemExit(f"MODEL_NAME inconnu : {forced}. Choix : {list(models)}")
        best_name = forced
    else:
        # Sélection sur la validation croisée (train) : le test reste un jeu neutre
        best_name = max(results, key=lambda n: results[n]["cv_f1_mean"])

    best_model = models[best_name]
    print(f"\nModèle retenu : {best_name}")
    print(classification_report(y_test, best_model.predict(X_test), digits=3))
    print("Matrice de confusion :")
    print(confusion_matrix(y_test, best_model.predict(X_test)))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODELS_DIR / "model.pkl")
    joblib.dump(best_model, MODELS_DIR / f"model_v{MODEL_VERSION}.pkl")

    metadata = {
        "model_name": best_name,
        "model_display_name": DISPLAY_NAMES[best_name],
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": FEATURES,
        "target": TARGET,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "churn_rate": round(float(y.mean()), 4),
        "sklearn_version": sklearn.__version__,
        "selection_metric": "cv_f1_mean" if not forced else "forced",
        "metrics": results[best_name],
        "all_results": results,
    }
    with open(MODELS_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nModèle sauvegardé dans models/model.pkl (version {MODEL_VERSION})")
    print("Métadonnées sauvegardées dans models/metadata.json")


if __name__ == "__main__":
    main()
