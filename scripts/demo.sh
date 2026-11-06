#!/usr/bin/env bash
# Démonstration de bout en bout (partie 26) sur la machine locale.
set -euo pipefail
cd "$(dirname "$0")/.."
python src/generate_data.py
python src/train.py
pytest
echo "Lancement de l'API sur http://127.0.0.1:8000 (Ctrl+C pour arrêter)"
uvicorn api.main:app --reload
