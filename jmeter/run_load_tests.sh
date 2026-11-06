#!/usr/bin/env bash
# Tirs de charge successifs : 100, 500 puis 1000 utilisateurs (mode non GUI).
# Usage : ./jmeter/run_load_tests.sh [HOST] [PORT]
set -euo pipefail
HOST="${1:-localhost}"
PORT="${2:-8000}"
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/results"

for USERS in 100 500 1000; do
  echo "=== Tir avec ${USERS} utilisateurs ==="
  rm -rf "$DIR/report-${USERS}u" "$DIR/results/${USERS}u.jtl"
  jmeter -n -t "$DIR/churn_load_test.jmx" \
    -Jhost="$HOST" -Jport="$PORT" \
    -Jthreads="$USERS" -Jrampup=10 -Jloops=10 \
    -l "$DIR/results/${USERS}u.jtl" \
    -e -o "$DIR/report-${USERS}u"
  echo "Rapport HTML : $DIR/report-${USERS}u/index.html"
  sleep 15   # laisser l'API revenir au repos entre deux tirs
done
