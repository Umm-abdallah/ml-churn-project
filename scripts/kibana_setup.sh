#!/usr/bin/env bash
# Crée la data view "ml-churn-logs-*" dans Kibana (équivalent de
# Stack Management > Data Views > Create data view).
set -euo pipefail
KIBANA="${1:-http://localhost:5601}"
until curl -fs "$KIBANA/api/status" > /dev/null; do echo "Attente de Kibana..."; sleep 5; done
curl -fsS -X POST "$KIBANA/api/data_views/data_view" \
  -H "kbn-xsrf: true" -H "Content-Type: application/json" \
  -d '{"data_view":{"title":"ml-churn-logs-*","name":"ML Churn API logs","timeFieldName":"@timestamp"}}'
echo
echo "Data view créée. Ouvrir $KIBANA/app/discover"
