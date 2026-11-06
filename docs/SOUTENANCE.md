# Éléments de réponse aux questions de soutenance

Réponses courtes, appuyées sur ce qui a été réellement fait dans le projet. À reformuler avec ses propres mots.

## Data Science

**Pourquoi ce problème est pertinent ?** Acquérir un client coûte nettement plus cher que le conserver. Identifier à l'avance les clients à risque permet de cibler les actions de rétention (offre, appel du centre de contact, traitement prioritaire des réclamations) sur ceux qui en ont besoin, au lieu d'arroser toute la base.

**Quelle est la variable cible ?** `churn` : 1 si le client part, 0 sinon. Les six autres colonnes sont les variables explicatives.

**Pourquoi s'agit il d'une classification ?** La cible est catégorielle (deux classes). Le modèle renvoie en plus une probabilité, utile pour classer les clients par niveau de risque.

**Comment avez vous séparé train et test ?** 80 % / 20 % avec `train_test_split`, `random_state=42` pour la reproductibilité et `stratify=y` pour garder 43 % de churn dans les deux jeux. Le choix du modèle se fait en validation croisée à 5 plis sur le jeu d'entraînement seulement ; le jeu de test ne sert qu'à l'évaluation finale.

**Pourquoi avoir choisi Random Forest ?** Point à nuancer : la comparaison montre que la régression logistique est meilleure ici (F1 en validation croisée 0,523 contre 0,478). C'est logique : les données sont générées par une formule logistique, donc un modèle linéaire est le plus adapté. Le Random Forest reste pertinent sur des données réelles (relations non linéaires, interactions, peu de préparation, importance des variables), et on peut le forcer avec `MODEL_NAME=random_forest`. Savoir justifier le choix par les métriques est le vrai attendu.

## API

**Pourquoi transformer le modèle en API ?** Pour que n'importe quelle application (CRM, centre de contact, interface web) puisse obtenir une prédiction par un simple appel HTTP, sans connaître Python ni le modèle. Le modèle devient un service versionné, testable, supervisé et remplaçable sans toucher aux clients.

**Pourquoi FastAPI ?** Rapide, validation automatique des entrées avec Pydantic (erreur 422 si une donnée est absente ou invalide), documentation Swagger générée automatiquement, typage Python, écosystème Prometheus disponible.

**Quelle différence entre /health et /predict ?** `/health` est une sonde technique : elle dit si le service est prêt (ici, si le modèle est chargé) et sert aux healthchecks Docker, au répartiteur de charge et à la supervision. `/predict` est la fonction métier : elle reçoit les données d'un client et renvoie la prédiction.

## Tests

**Pourquoi Pytest ?** Standard Python, syntaxe simple (`assert`), fixtures, paramétrage (un même test sur plusieurs valeurs invalides), intégration directe dans la CI.

**Pourquoi Selenium ?** Pour tester comme un utilisateur réel : ouvrir la page, saisir, cliquer sur Prédire, lire le résultat affiché. Il vérifie que toute la chaîne (navigateur, JavaScript, API, modèle) fonctionne ensemble.

**Différence entre test unitaire, intégration et E2E ?**
* Unitaire : une brique isolée (le modèle renvoie bien deux probabilités qui somment à 1 ; une forte ancienneté baisse le risque).
* Intégration : plusieurs briques ensemble (requête HTTP vers FastAPI qui appelle le modèle, validation, métriques).
* E2E : le parcours complet utilisateur dans un vrai navigateur.

## Performance

**Pourquoi JMeter ?** Outil open source de référence pour simuler de nombreux utilisateurs simultanés, avec assertions, paramétrage et rapports HTML (percentiles, débit, erreurs).

**Différence entre charge, stress et endurance ?**
* Charge : vérifier le comportement sous la charge attendue (100 utilisateurs).
* Stress : augmenter au delà (500, 1000) pour trouver le point de rupture et observer comment le service se dégrade.
* Endurance : charge normale maintenue longtemps (plusieurs heures) pour détecter fuites mémoire et dégradations progressives.

**Que signifie le 95e percentile du temps de réponse ?** 95 % des requêtes ont été servies en moins de ce temps ; 5 % ont été plus lentes. Il est plus représentatif de l'expérience utilisateur que la moyenne, qui masque les requêtes lentes.

## DevOps

**Pourquoi Git ?** Historique de toutes les modifications, retour en arrière possible, travail à plusieurs, traçabilité (qui a changé quoi et pourquoi), point de départ de la CI.

**Pourquoi des branches ?** Isoler chaque développement (`feature/model`) sans casser la version stable : `main` (production), `develop` (intégration), fusion par Pull Request après revue et CI verte.

**Pourquoi Docker ?** L'application, ses dépendances et le modèle sont empaquetés dans une image identique partout : « ça marche sur ma machine » devient « ça marche partout ». Déploiement et retour arrière rapides par simple changement de tag.

**Pourquoi CI/CD ?** Chaque push déclenche automatiquement entraînement, tests, tests E2E et build de l'image. Les erreurs sont détectées tout de suite, avant la production, et la livraison devient répétable.

## Observabilité

**Différence entre logs et métriques ?** Un log est un événement détaillé et unitaire (telle requête, tel client, tel résultat, telle erreur) : il sert à enquêter. Une métrique est une valeur numérique agrégée dans le temps (requêtes par seconde, p95, taux d'erreur) : elle sert à surveiller et à alerter.

**Pourquoi ELK ?** Centraliser les logs de tous les conteneurs, les rechercher rapidement (par `request_id`, niveau ERROR, version du modèle) et construire des visualisations. Logstash collecte et transforme, Elasticsearch indexe, Kibana affiche.

**Pourquoi Prometheus ?** Il interroge périodiquement `/metrics`, stocke des séries temporelles et évalue des règles d'alerte (API indisponible, taux d'erreur, latence, dérive).

**Pourquoi Grafana ?** Visualiser les métriques Prometheus dans des tableaux de bord lisibles, partagés par l'équipe d'exploitation.

**Que surveiller sur une API ML en production ?** Disponibilité, latence (p95, p99), taux d'erreur, débit ; et spécifiquement ML : distribution des entrées (dérive des données), distribution des probabilités et part de CHURN prédite (dérive des prédictions), version du modèle servie, et dès que la vérité terrain arrive, la performance réelle (rappel, précision).

## MLOps

**Comment versionner le modèle ?** Chaque entraînement produit `model_v<version>.pkl` et un `metadata.json` (version, date, métriques, features, versions des librairies). La version est exposée par `/model/info`, dans chaque réponse et dans les logs. L'image Docker est taguée avec la même version. Outils dédiés pour aller plus loin : MLflow Model Registry, DVC.

**Que faire si un nouveau modèle est moins performant ?** Ne pas le déployer : un seuil de qualité (test `ROC AUC >= 0,60`) bloque la CI, et on compare toujours le candidat au modèle en production sur le même jeu de test. En production, déploiement progressif (canary ou A/B) avant de basculer tout le trafic.

**Comment détecter une dégradation du modèle ?** Surveiller la dérive des entrées et des prédictions (alerte `PredictionDrift` sur la part de CHURN), puis mesurer la performance réelle quand on sait quels clients sont effectivement partis. Une baisse déclenche un réentraînement.

**Comment gérer plusieurs versions du modèle ?** Une image par version (`ml-churn-api:1.0.0`, `1.1.0`), le label `model_version` sur toutes les métriques et logs, et un routage (répartiteur ou paramètre) pour servir deux versions en parallèle pendant une comparaison.

**Comment revenir à une ancienne version ?** Redéployer l'image précédente : `MODEL_VERSION=1.0.0 docker compose up -d api`, ou recharger `model_v1.0.0.pkl` via `MODEL_PATH`. Le retour arrière prend quelques secondes car rien n'est reconstruit.
