# Corrections apportées à l'énoncé

Ce document liste les erreurs et manques relevés dans l'énoncé du projet fil rouge, et la correction mise en œuvre dans ce dépôt. Chaque correction a été vérifiée par exécution (pipeline, tests, API) sauf mention contraire.

## Synthèse

| Gravité | Nombre | Effet si non corrigé |
|---|---|---|
| Bloquant | 9 | Le pipeline ne fonctionne pas (erreur, test toujours en échec, service injoignable) |
| Important | 12 | Fonctionne mais résultat faux, non reproductible ou non industriel |
| Amélioration | 8 | Bonnes pratiques MLOps attendues en soutenance |

## 1. Corrections bloquantes

| # | Partie | Problème dans l'énoncé | Correction |
|---|---|---|---|
| B1 | 11 | `from api.main import app` échoue avec `ModuleNotFoundError: No module named 'api'` : pytest ajoute le dossier `tests/` au chemin Python, pas la racine du projet. | `pytest.ini` avec `pythonpath = .`, fichiers `__init__.py` dans `api/`, `src/`, `tests/`. |
| B2 | 11 | Avec le chargement du modèle au démarrage, `TestClient(app)` sans `with` ne déclenche pas le démarrage de l'application. | Fixture `client` dans `tests/conftest.py` utilisant `with TestClient(app) as c`. |
| B3 | 16, 17 | `pip install selenium` est fait après `pip freeze`, donc absent de `requirements.txt`. En CI, pytest collecte `tests/test_selenium.py` et échoue (`ModuleNotFoundError`, pas de serveur, pas d'écran). | Tests E2E marqués `e2e`, exclus par défaut (`addopts = -m "not e2e"`), exécutés dans un job CI séparé avec Chrome headless. |
| B4 | 17 | `assert "FastAPI" in driver.title` échoue toujours : le titre réel de Swagger UI est « Churn Prediction API - Swagger UI ». | Attente explicite du titre et assertion sur « Churn Prediction API ». |
| B5 | 17 | `webdriver.Chrome()` sans option plante sur un serveur ou en CI (pas d'affichage). | Options `--headless=new`, `--no-sandbox`, `--disable-dev-shm-usage`. |
| B6 | 14, 26 | Python 3.11 dans l'image et la CI, alors que `pip freeze` est fait sur la machine de l'étudiant (Ubuntu 24.04 : Python 3.12). Les versions figées peuvent ne pas exister pour 3.11 : constaté ici, `numpy==2.5.3` n'est pas installable en 3.11 et le build échoue. | Python 3.12 partout (poste, image `python:3.12-slim`, CI) et `requirements.txt` écrit à la main avec des versions vérifiées. |
| B7 | 14, 26 | L'image copie `models/model.pkl` qui doit exister avant le build ; un modèle sérialisé avec une autre version de scikit learn peut ne pas se recharger. | Le Dockerfile génère les données et entraîne le modèle pendant le build, avec les versions de l'image. |
| B8 | 22 | `docker run grafana/grafana` lance Grafana hors du réseau compose : il ne peut pas joindre Prometheus, et Prometheus lui même n'est lancé nulle part alors que sa cible est `api:8000` (nom DNS valable uniquement dans compose). | Services `prometheus` et `grafana` ajoutés à `docker-compose.yml`, datasource et dashboard provisionnés automatiquement. |
| B9 | 20 | « Créer docker-compose.yml » écrase le fichier de la partie 15 (perte du service `api`), et aucune configuration ELK n'est fournie (ni services, ni pipeline Logstash, ni moyen d'acheminer les logs). | Un seul compose enrichi. L'API écrit des logs JSON dans un volume partagé, Logstash les lit (`docker/logstash/pipeline/ml-churn.conf`) et les indexe dans Elasticsearch, Kibana les affiche. Prérequis système documenté : `vm.max_map_count=262144`. |

## 2. Corrections importantes

| # | Partie | Problème | Correction |
|---|---|---|---|
| I1 | 9 | Résultat attendu `CHURN` avec probabilité 0,87. Avec la formule de génération, ce client (ancienneté 5 mois) a une probabilité théorique de churn de 0,60 environ : 0,87 est irréaliste. | Résultat réel documenté : `CHURN`, probabilité 0,599. |
| I2 | 6 | Le Random Forest est retenu sans regarder les résultats, alors que la question de soutenance demande de justifier ce choix. Les données étant générées par une formule logistique, la régression logistique est le modèle le mieux adapté. | Sélection automatique sur le F1 en validation croisée (5 plis, jeu d'entraînement uniquement). Résultat : régression logistique (F1 CV 0,523 contre 0,478 pour le Random Forest). Le choix peut être forcé : `MODEL_NAME=random_forest python src/train.py`. |
| I3 | 6 | Random Forest sans limite de profondeur : sur apprentissage sur un jeu bruité. | `max_depth=6`, `min_samples_leaf=10`. |
| I4 | 6 | Métriques limitées au seuil 0,5. | Ajout du ROC AUC, du rapport de classification et de la matrice de confusion. |
| I5 | 7 | L'API envoie une liste sans noms de colonnes : avertissement scikit learn et risque de prédictions fausses si l'ordre des champs change. | DataFrame construit avec la liste de features enregistrée à l'entraînement. Les tests transforment cet avertissement en erreur. |
| I6 | 7 | `joblib.load("models/model.pkl")` dépend du dossier courant. | Chemin calculé depuis le fichier, surchargeable par `MODEL_PATH`. |
| I7 | 7 | Nom et version du modèle écrits en dur (« Random Forest », « 1.0.0 »), donc faux dès qu'on change de modèle. | Lus dans `models/metadata.json` produit par l'entraînement. |
| I8 | 7 | Aucune validation métier des entrées (âge négatif accepté). | Contraintes Pydantic (`ge`, `le`) : réponse 422. |
| I9 | 5 | `plt.show()` bloque ou plante sans écran ; chemins `../data` dépendants du dossier courant ; deux graphiques superposés sans `plt.figure()`. | Backend `Agg` sans écran, chemins absolus, figures dans `reports/figures`. |
| I10 | 14 | Pas de `.dockerignore` : `COPY . .` embarque `.venv`, `.git`, les logs. | `.dockerignore`, copie sélective, utilisateur non root, `HEALTHCHECK`. |
| I11 | 16, 24 | La partie 24 annonce « Build Docker » dans la CI, mais le workflow ne le fait pas ; il ne régénère pas non plus le modèle. | Workflow en 3 jobs : tests, E2E, build Docker avec test de fumée et publication GHCR sur `main`. |
| I12 | 18 | Arborescence JMeter incorrecte (Listener enfant du Header Manager) ; pas d'en tête `Content-Type: application/json` mentionné, donc réponses 422 ; aucune assertion, donc les erreurs ne sont pas comptées. | Plan `jmeter/churn_load_test.jmx` corrigé, paramétrable (`-Jthreads=500`) et script des 3 tirs en mode non GUI. |

## 3. Améliorations

| # | Partie | Constat | Mise en œuvre |
|---|---|---|---|
| A1 | 19 | Les logs ne répondent pas aux questions « qui ? », « quel résultat ? », « combien de temps ? ». | Logs JSON : `request_id` (aussi renvoyé dans l'en tête `X-Request-ID`), `client_ip`, `model_name`, `model_version`, `prediction`, `probability`, `response_time_ms`, `input`, et trace complète en cas d'erreur. |
| A2 | 21, 22 | Les métriques HTTP ne permettent pas de compter les prédictions ni de suivre le modèle. | Métriques métier : `churn_predictions_total{result}`, `churn_prediction_errors_total`, `churn_prediction_duration_seconds`, `churn_prediction_probability`, `churn_model_loaded`. |
| A3 | 21 | Aucune alerte. | `monitoring/prometheus/alerts.yml` : API indisponible, taux d'erreur, latence p95, dérive du taux de CHURN prédit. |
| A4 | 7 | `/health` répond UP même sans modèle. | `/health` renvoie 503 si le modèle n'est pas chargé. |
| A5 | 17, 23 | Le dossier `frontend` est créé mais jamais rempli, alors que l'architecture et Selenium supposent une interface web. | Interface `frontend/index.html` servie sur `/ui/`, testée par Selenium (saisie, clic sur Prédire, vérification du résultat). |
| A6 | 6 | Pas de versionnement du modèle. | `metadata.json` (version, date, métriques, versions des librairies) et copie `model_v1.0.0.pkl` ; version paramétrable par `MODEL_VERSION`. |
| A7 | 12, 13 | Identité Git d'un autre auteur à recopier ; GitHub refuse les mots de passe en HTTPS. | Chacun configure sa propre identité ; authentification par jeton (PAT) ou clé SSH documentée. |
| A8 | 8, 25 | `--reload` est un mode de développement ; port à ouvrir sur la VM non mentionné. | `--reload` réservé au poste de développement ; ouverture du pare feu documentée (`sudo ufw allow 8000/tcp`). |

## 4. Remarques sur les données

* Le score latent n'utilise ni l'âge ni le revenu : ces deux variables sont du bruit, ce que montre la matrice de corrélation. C'est un bon point à commenter en soutenance (sélection de variables).
* Le signal est faible (ROC AUC d'environ 0,64 pour tous les modèles) : la formule de l'énoncé donne une probabilité de churn proche de 0,5 pour beaucoup de clients. Le dataset n'a pas été modifié pour rester fidèle à l'énoncé ; un test de qualité minimale (`ROC AUC >= 0,60`) bloque malgré tout le déploiement d'un modèle qui ne ferait pas mieux que le hasard.
* Le taux de churn est de 43 % (861 sur 2000), classes raisonnablement équilibrées : la stratification du découpage train/test reste néanmoins justifiée.
