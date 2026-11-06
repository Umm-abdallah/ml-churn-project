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

## Captures à faire sur votre machine

Ces outils n'ont pas pu être exécutés dans l'environnement de préparation (téléchargements bloqués). Après `docker compose up -d --build`, prendre les captures suivantes et les enregistrer sous ces noms dans `docs/captures/` :

| Fichier | Où | Quoi montrer |
|---|---|---|
| `03_swagger.png` | http://localhost:8000/docs | Liste des routes |
| `05_swagger_predict.png` | /docs, POST /predict, Try it out, Execute | Réponse 200 avec prediction et probability |
| `10_grafana_dashboard.png` | http://localhost:3000, dossier ML Churn | Dashboard complet pendant un tir JMeter |
| `11_kibana_discover.png` | http://localhost:5601, Discover | Logs `event_type : "prediction"` avec les colonnes prediction, probability, response_time_ms |
| `12_kibana_erreurs.png` | Discover | Recherche `level : "ERROR"` (provoquer une erreur ou montrer 0 résultat) |
| `13_jmeter_100u.png` | `jmeter/report-100u/index.html` | Tableau Statistics |
| `14_jmeter_500u.png` | `jmeter/report-500u/index.html` | Tableau Statistics |
| `15_jmeter_1000u.png` | `jmeter/report-1000u/index.html` | Tableau Statistics et graphe Response Times Over Time |
| `17_docker_ps.png` | Terminal | `docker compose ps` avec les 6 services |
