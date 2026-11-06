# Captures d'écran du projet

## Captures réalisées (exécutions réelles du projet)

| Fichier | Contenu |
|---|---|
| `01a_eda_churn.png` | Répartition de la cible (1139 NO_CHURN, 861 CHURN) |
| `01b_eda_correlation.png` | Matrice de corrélation |
| `01c_eda_anciennete.png` | Ancienneté selon le churn |
| `02_entrainement.png` | Sortie de `python src/train.py` (comparaison des 3 modèles) |
| `04_interface_web.png` | Interface /ui/ après clic sur Prédire |
| `06_pytest.png` | `pytest -v` : 18 tests réussis |
| `07_prometheus_targets.png` | Cible ml-churn-api à l'état UP |
| `08a_prometheus_p95.png` | p95 serveur de /predict pendant les tirs 100 puis 500 utilisateurs |
| `08b_prometheus_predictions.png` | Prédictions par seconde, CHURN et NO_CHURN |
| `08c_prometheus_requetes.png` | Requêtes /predict par seconde (plafond vers 100 req/s) |
| `09_prometheus_alertes.png` | Les 4 règles d'alerte chargées |
| `16_github_actions.png` | Pipeline CI ML Churn #1 : 3 jobs réussis en 1 min 39 s |

Prometheus a été lancé ici avec le binaire officiel 2.55.1 et la cible `localhost:8000` (même configuration que dans compose, seul le nom d'hôte change).

## Captures de la pile complète (workflow GitHub Actions « Captures de la pile complète »)

Prises automatiquement par `.github/workflows/captures.yml` sur un runner GitHub (Ubuntu, 4 vCPU) : la pile complète est démarrée avec `docker compose`, les 3 tirs JMeter sont lancés, puis `scripts/capture_screens.py` prend les captures avec un navigateur headless.

| Fichier | Contenu |
|---|---|
| `03_swagger.png` | Swagger UI, liste des routes |
| `05_swagger_predict.png` | POST /predict exécuté depuis Swagger, réponse 200 |
| `10_grafana_dashboard.png` | Dashboard Grafana sur les 15 minutes des tirs JMeter |
| `11_kibana_discover.png` | Kibana Discover, 16 001 logs de prédiction |
| `12_kibana_erreurs.png` | Recherche `level : "ERROR"` : aucune erreur |
| `13_jmeter_100u.png` | Rapport JMeter, 100 utilisateurs |
| `14_jmeter_500u.png` | Rapport JMeter, 500 utilisateurs |
| `15_jmeter_1000u.png` | Rapport JMeter, 1000 utilisateurs |
| `17_docker_ps.png` | Les 6 services démarrés |
| `jmeter_summary.json` | Chiffres des 3 rapports JMeter |

Pour les refaire : onglet Actions, « Captures de la pile complète », Run workflow.
