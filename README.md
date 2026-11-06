# ML Churn Project : industrialisation d'un modèle de prédiction du churn

Projet fil rouge MLOps : transformer un modèle de prédiction du churn des clients d'un opérateur télécom en une application déployable, testée, supervisée et maintenable.

Les erreurs relevées dans l'énoncé et leurs corrections sont détaillées dans [docs/CORRECTIONS.md](docs/CORRECTIONS.md). Les éléments de réponse aux questions de soutenance sont dans [docs/SOUTENANCE.md](docs/SOUTENANCE.md).

## Architecture

```
                 Utilisateur
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
  Interface web /ui/        Swagger /docs
        └────────────┬────────────┘
                     ▼
            FastAPI  /predict ──► Modèle (scikit learn, models/model.pkl)
              │            │
     logs JSON│            │/metrics
              ▼            ▼
          Logstash     Prometheus ──► alertes
              ▼            ▼
       Elasticsearch    Grafana
              ▼
           Kibana

  Git ► Pull Request ► GitHub Actions (tests, E2E, build Docker) ► image GHCR ► VM
```

## Arborescence

```
ml-churn-project/
├── api/main.py                     API FastAPI (prédiction, logs JSON, métriques)
├── src/generate_data.py            génération du dataset
├── src/train.py                    entraînement, comparaison, sélection, versionnement
├── notebooks/exploration.ipynb     notebook Data Science (EDA, comparaison, analyse du modèle)
├── notebooks/exploration.py        version script de l'EDA (figures pour reports/)
├── data/raw/churn.csv              dataset (2000 clients)
├── models/                         model.pkl, model_v1.0.0.pkl, metadata.json
├── frontend/index.html             interface web (servie sur /ui/)
├── tests/                          pytest : modèle, API ; tests/e2e : Selenium
├── jmeter/                         plan de charge .jmx et script des tirs
├── monitoring/prometheus/          scrape + règles d'alerte
├── monitoring/grafana/             datasource et dashboard provisionnés
├── docker/logstash/                pipeline Logstash
├── scripts/                        démo, test de fumée, configuration Kibana
├── Dockerfile, .dockerignore, docker-compose.yml, .env.example
├── .github/workflows/ci.yml        pipeline CI
└── docs/                           corrections, soutenance
```

## Guide d'installation

### 1. Prérequis (Ubuntu 22.04 ou 24.04)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip docker.io docker-compose-v2 tree
sudo systemctl enable --now docker
sudo usermod -aG docker $USER      # puis se déconnecter et se reconnecter (ou: newgrp docker)
docker run hello-world
```

Le projet cible Python 3.12 (version par défaut d'Ubuntu 24.04, de l'image Docker et de la CI). Sous Ubuntu 22.04 : `sudo apt install python3.12 python3.12-venv` (dépôt deadsnakes) puis utiliser `python3.12`.

### 2. Environnement Python

```bash
git clone https://github.com/<votre-compte>/ml-churn-project.git
cd ml-churn-project
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

`requirements.txt` contient uniquement les dépendances de l'API (image Docker) ; `requirements-dev.txt` ajoute l'exploration et les tests.

### 3. Data Science

```bash
python src/generate_data.py        # data/raw/churn.csv
python notebooks/exploration.py    # figures dans reports/figures/
jupyter notebook notebooks/exploration.ipynb   # notebook complet, déjà exécuté avec ses sorties
python src/train.py                # models/model.pkl + metadata.json
```

Forcer un modèle ou une version : `MODEL_NAME=random_forest MODEL_VERSION=1.1.0 python src/train.py`.

Résultats obtenus (jeu de test, 400 clients) :

| Modèle | Accuracy | Précision | Rappel | F1 | ROC AUC | F1 validation croisée |
|---|---|---|---|---|---|---|
| Logistic Regression | 0,625 | 0,582 | 0,453 | 0,510 | 0,636 | **0,523** |
| Decision Tree | 0,633 | 0,583 | 0,512 | 0,545 | 0,623 | 0,436 |
| Random Forest | 0,635 | 0,618 | 0,395 | 0,482 | 0,639 | 0,478 |

Le modèle retenu automatiquement est la régression logistique (meilleur F1 en validation croisée, critère calculé sur le seul jeu d'entraînement).

### 4. API

```bash
uvicorn api.main:app --reload      # développement uniquement
```

| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | Informations de l'application |
| `/health` | GET | Santé : 200 si le modèle est chargé, 503 sinon |
| `/model/info` | GET | Nom, version, date d'entraînement, features, métriques |
| `/predict` | POST | Prédiction CHURN / NO_CHURN et probabilité |
| `/metrics` | GET | Métriques Prometheus |
| `/docs` | GET | Swagger UI |
| `/ui/` | GET | Interface web |

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"age":35,"anciennete":5,"revenu":450000,"nb_reclamations":2,"montant_mensuel":25000,"retards_paiement":2}'
```

Réponse obtenue (la durée varie selon la machine) :

```json
{"prediction":"CHURN","probability":0.599,"model_version":"1.0.0","duration_ms":3.29,"request_id":"8fcb8a71-..."}
```

### 5. Tests

```bash
pytest                 # 18 tests : données, modèle, API, validation, métriques (E2E exclus)
pytest -m e2e          # 3 tests Selenium (Chrome requis), le serveur est lancé automatiquement
BASE_URL=http://SERVER_IP:8000 pytest -m e2e   # contre une API déjà déployée
```

### 6. Docker

```bash
docker build -t ml-churn-api:1.0 .
docker run -d --name ml-churn-api -p 8000:8000 ml-churn-api:1.0
docker ps                          # colonne STATUS : (healthy)
./scripts/smoke_test.sh http://localhost:8000
docker rm -f ml-churn-api
```

### 7. Pile complète (API, ELK, Prometheus, Grafana)

Elasticsearch demande environ 4 Go de RAM libre et ce réglage du noyau :

```bash
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-elasticsearch.conf
```

```bash
cp .env.example .env               # puis changer le mot de passe Grafana
docker compose up -d --build       # ou seulement l'API : docker compose up -d api
docker compose ps
./scripts/kibana_setup.sh          # crée la data view ml-churn-logs-*
```

| Service | URL | Usage |
|---|---|---|
| API | http://localhost:8000 | /docs, /ui/, /metrics |
| Prometheus | http://localhost:9090 | Status > Targets : ml-churn-api doit être UP ; onglet Alerts |
| Grafana | http://localhost:3000 | admin / mot de passe du .env ; dossier « ML Churn » |
| Kibana | http://localhost:5601 | Discover, data view « ML Churn API logs » |
| Elasticsearch | http://localhost:9200 | `curl localhost:9200/_cat/indices?v` |

Recherches Kibana utiles (KQL) :

```
event_type : "prediction"
level : "ERROR"
model_version : "1.0.0"
response_time_ms > 50
prediction : "CHURN" and probability > 0.8
```

Le dashboard Grafana « ML Churn API : supervision » contient : nombre de requêtes, nombre de prédictions, nombre d'erreurs, taux d'erreur, latence p50/p95/p99, requêtes par route, prédictions par résultat, part de CHURN (dérive), distribution des probabilités, durée d'inférence, état du modèle.

### 8. Test de charge JMeter

```bash
# Interface graphique : conception et débogage du plan seulement
jmeter -t jmeter/churn_load_test.jmx
# Tirs 100, 500 et 1000 utilisateurs en mode non GUI, rapports HTML générés
./jmeter/run_load_tests.sh localhost 8000
```

Mesure préliminaire sans JMeter, même profil : `python scripts/load_probe.py http://localhost:8000 100 500 1000`.

Indicateurs à relever dans chaque rapport (`jmeter/report-XXXu/index.html`) : temps moyen, médiane, 90e, 95e et 99e percentiles, débit (requêtes par seconde), pourcentage d'erreurs. Observer en parallèle le dashboard Grafana pendant le tir.

### 9. Git et GitHub

```bash
git config --global user.name "Prénom NOM"
git config --global user.email "votre.email@exemple.com"
git init && git add . && git commit -m "Initialisation du projet ML Churn"
git branch -M main
git checkout -b develop
git checkout -b feature/model
# ... modifications ...
git add . && git commit -m "Ajout du modèle de prédiction du churn"
git checkout develop && git merge --no-ff feature/model
git remote add origin https://github.com/<votre-compte>/ml-churn-project.git
git push -u origin main develop
```

GitHub n'accepte plus les mots de passe en HTTPS : utiliser un jeton personnel (Settings > Developer settings > Personal access tokens) ou une clé SSH. En pratique, `main` est mise à jour par Pull Request depuis `develop`, après passage de la CI.

### 10. Déploiement sur une VM

```bash
sudo apt update && sudo apt install -y git docker.io docker-compose-v2
git clone https://github.com/<votre-compte>/ml-churn-project.git && cd ml-churn-project
sudo ufw allow 8000/tcp            # et 3000, 5601, 9090 si les outils doivent être accessibles
docker compose up -d --build api   # ou toute la pile
./scripts/smoke_test.sh http://SERVER_IP:8000
```

Variante sans build sur la VM : utiliser l'image publiée par la CI, `docker pull ghcr.io/<votre-compte>/ml-churn-project:latest`.

## Pipeline CI (GitHub Actions)

| Job | Contenu |
|---|---|
| Tests unitaires et API | Installation, génération des données, entraînement, `pytest`, archivage du modèle et de ses métriques |
| Tests E2E Selenium | Chrome headless, scénario complet sur l'interface web |
| Build Docker | Construction de l'image, test de fumée (`/health` puis `/predict`), publication GHCR sur `main` |

## Limites connues

* Une seule instance uvicorn : les métriques Prometheus sont par processus. Pour plusieurs workers, activer le mode multiprocessus de `prometheus_client` ou mettre plusieurs conteneurs derrière un répartiteur.
* Sécurité Elasticsearch désactivée pour le TP ; à activer en production (mots de passe, TLS).
* Pas d'authentification sur l'API : à ajouter (clé d'API ou OAuth2) avant une exposition publique.
