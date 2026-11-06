"""Tests E2E Selenium : navigateur -> interface web -> API -> modèle -> affichage.

Corrections par rapport à l'énoncé :
* le titre de Swagger UI est « Churn Prediction API - Swagger UI » : il ne contient
  pas « FastAPI », l'assertion de l'énoncé échoue donc toujours ;
* Chrome est lancé en mode headless (indispensable sur serveur, CI ou Docker) ;
* attente explicite (WebDriverWait) au lieu de supposer que la page est prête ;
* le serveur est démarré automatiquement s'il ne tourne pas déjà ;
* le scénario complet décrit dans l'énoncé (saisie, clic sur Prédire, résultat)
  est réellement testé sur l'interface /ui.

Lancement :  pytest -m e2e
Contre un serveur déjà lancé (Docker, VM) :  BASE_URL=http://SERVER_IP:8000 pytest -m e2e
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

webdriver = pytest.importorskip("selenium.webdriver")
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001")


def _is_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def server():
    if _is_up(BASE_URL):
        yield BASE_URL
        return
    port = BASE_URL.rsplit(":", 1)[-1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", port],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if _is_up(BASE_URL):
            break
        time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("Le serveur uvicorn n'a pas démarré")
    yield BASE_URL
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


def test_swagger_docs(server, driver):
    driver.get(f"{server}/docs")
    WebDriverWait(driver, 10).until(EC.title_contains("Swagger UI"))
    assert "Churn Prediction API" in driver.title


def _fill(driver, field, value):
    element = driver.find_element(By.ID, field)
    element.clear()
    element.send_keys(str(value))


def test_prediction_from_ui(server, driver):
    # 1. Ouverture de l'application
    driver.get(f"{server}/ui/")
    assert "churn" in driver.title.lower()

    # 2. Saisie des données client
    client = {"age": 35, "anciennete": 5, "revenu": 450000,
              "nb_reclamations": 2, "montant_mensuel": 25000, "retards_paiement": 2}
    for field, value in client.items():
        _fill(driver, field, value)

    # 3. Clic sur "Prédire"  (4. appel API fait par la page)
    driver.find_element(By.ID, "predict-btn").click()

    # 5. Affichage du résultat
    WebDriverWait(driver, 10).until(
        lambda d: d.find_element(By.ID, "prediction").text.strip() != ""
    )

    # 6. Vérification du résultat
    text = driver.find_element(By.ID, "prediction").text
    assert text.startswith("CHURN") or text.startswith("NO_CHURN")
    probability = driver.find_element(By.ID, "probability").text
    assert probability.endswith("%")
    assert 0 <= float(probability.replace("%", "").strip()) <= 100


def test_invalid_input_shows_error(server, driver):
    driver.get(f"{server}/ui/")
    # Contourne la validation HTML pour tester la validation côté API
    driver.execute_script("document.getElementById('client-form').noValidate = true;")
    _fill(driver, "age", -3)
    driver.find_element(By.ID, "predict-btn").click()
    WebDriverWait(driver, 10).until(
        lambda d: d.find_element(By.ID, "prediction").text == "Erreur"
    )
