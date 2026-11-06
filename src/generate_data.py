"""Génération d'un dataset pédagogique de churn télécom.

Correction par rapport à l'énoncé : les chemins sont calculés à partir de la
racine du projet, le script fonctionne donc quel que soit le dossier courant,
et le dossier data/raw est créé s'il n'existe pas.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "raw" / "churn.csv"

SEED = 42
N = 2000


def generate(n: int = N, seed: int = SEED) -> pd.DataFrame:
    # Même générateur que l'énoncé (np.random.seed) : le dataset est identique
    np.random.seed(seed)

    age = np.random.randint(18, 70, n)
    anciennete = np.random.randint(1, 120, n)          # en mois
    revenu = np.random.randint(150000, 1000000, n)
    nb_reclamations = np.random.poisson(2, n)
    montant_mensuel = np.random.randint(5000, 75000, n)
    retards_paiement = np.random.poisson(1, n)

    # Score latent identique à l'énoncé
    score = (
        0.04 * nb_reclamations
        + 0.08 * retards_paiement
        - 0.015 * anciennete
        + 0.00001 * montant_mensuel
    )
    probabilite = 1 / (1 + np.exp(-score))
    churn = (np.random.random(n) < probabilite).astype(int)

    return pd.DataFrame({
        "age": age,
        "anciennete": anciennete,
        "revenu": revenu,
        "nb_reclamations": nb_reclamations,
        "montant_mensuel": montant_mensuel,
        "retards_paiement": retards_paiement,
        "churn": churn,
    })


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(OUTPUT, index=False)
    print(df.head())
    print()
    print(df["churn"].value_counts())
    print(f"\nDataset écrit dans {OUTPUT.relative_to(ROOT)} ({len(df)} lignes)")


if __name__ == "__main__":
    main()
