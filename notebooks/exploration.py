"""Exploration des données (EDA).

Corrections par rapport à l'énoncé :
* chemins calculés depuis la racine du projet (plus besoin de faire cd notebooks) ;
* backend matplotlib non interactif quand il n'y a pas d'écran (serveur, CI, Docker),
  sinon plt.show() bloque ou plante ;
* les figures sont rangées dans reports/figures et non dans data/ ;
* plt.figure() avant chaque graphique pour ne pas superposer les deux figures.
"""
import os
from pathlib import Path

import matplotlib

if not os.environ.get("DISPLAY") and os.name != "nt":
    matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw" / "churn.csv"
FIGURES = ROOT / "reports" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA)

print(df.head())
print("\nDimensions :")
print(df.shape)
print("\nTypes :")
print(df.dtypes)
print("\nValeurs manquantes :")
print(df.isnull().sum())
print("\nStatistiques :")
print(df.describe().T)
print("\nRépartition du churn :")
print(df["churn"].value_counts())
print(df["churn"].value_counts(normalize=True).round(3))

print("\nMoyennes par classe :")
print(df.groupby("churn").mean().T.round(2))

# 1. Répartition de la cible
plt.figure(figsize=(6, 4))
sns.countplot(data=df, x="churn")
plt.title("Répartition des clients selon le churn")
plt.tight_layout()
plt.savefig(FIGURES / "churn_distribution.png", dpi=120)
plt.show()

# 2. Corrélations
plt.figure(figsize=(10, 6))
sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0)
plt.title("Corrélations")
plt.tight_layout()
plt.savefig(FIGURES / "correlation.png", dpi=120)
plt.show()

# 3. Distribution de l'ancienneté selon le churn (variable la plus discriminante)
plt.figure(figsize=(8, 4))
sns.histplot(data=df, x="anciennete", hue="churn", bins=30, element="step")
plt.title("Ancienneté (mois) selon le churn")
plt.tight_layout()
plt.savefig(FIGURES / "anciennete_vs_churn.png", dpi=120)
plt.show()

print(f"\nFigures enregistrées dans {FIGURES.relative_to(ROOT)}")
