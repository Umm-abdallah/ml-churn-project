#!/usr/bin/env bash
# Vérifie une API déployée : ./scripts/smoke_test.sh http://SERVER_IP:8000
set -euo pipefail
URL="${1:-http://localhost:8000}"
echo "--- /health";     curl -fsS "$URL/health"; echo
echo "--- /model/info"; curl -fsS "$URL/model/info"; echo
echo "--- /predict"
curl -fsS -X POST "$URL/predict" -H "Content-Type: application/json" \
  -d '{"age":35,"anciennete":5,"revenu":450000,"nb_reclamations":2,"montant_mensuel":25000,"retards_paiement":2}'
echo
echo "--- /metrics (extrait)"; curl -fsS "$URL/metrics" | grep -E "^churn_predictions_total" || true
