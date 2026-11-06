import pytest
from fastapi.testclient import TestClient

from api.main import app

VALID_PAYLOAD = {
    "age": 35,
    "anciennete": 5,
    "revenu": 450000,
    "nb_reclamations": 2,
    "montant_mensuel": 25000,
    "retards_paiement": 2,
}


@pytest.fixture(scope="session")
def client():
    # Correction : le "with" déclenche le lifespan (chargement du modèle).
    with TestClient(app) as c:
        yield c


@pytest.fixture
def payload():
    return dict(VALID_PAYLOAD)
