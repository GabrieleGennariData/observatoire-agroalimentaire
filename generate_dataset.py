"""
Genere un jeu de donnees synthetique pour le projet Cockpit Power BI.
Domaine: agroalimentaire (volaille + traiteur). Donnees 100% synthetiques.
Marques et sites anonymises (Marque A/B..., Usine 01/02...).
Sortie: 5 CSV en schema en etoile (2 dim + 3 fact). Seed fixe: reproductible.
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
rng = np.random.default_rng(SEED)
OUT = Path("dataset")
OUT.mkdir(exist_ok=True)

DATE_START = "2024-01-01"
DATE_END = "2026-06-30"

# DIM PRODUIT (produits generiques du secteur, marques anonymisees)
produits = [
    ("P001", "Poulet entier",         "Volaille brute", "Marque A", "Volaille"),
    ("P002", "Cuisse de poulet",       "Decoupe",        "Marque B", "Volaille"),
    ("P003", "Filet de poulet",        "Decoupe",        "Marque B", "Volaille"),
    ("P004", "Escalope de dinde",      "Decoupe",        "Marque C", "Volaille"),
    ("P005", "Nuggets de poulet",      "Elabore",        "Marque C", "Volaille"),
    ("P006", "Cordon bleu",            "Elabore",        "Marque B", "Volaille"),
    ("P007", "Magret de canard",       "Decoupe",        "Marque A", "Volaille"),
    ("P008", "Quiche lorraine",        "Traiteur",       "Marque D", "Traiteur"),
    ("P009", "Plat asiatique",         "Traiteur",       "Marque E", "Traiteur"),
    ("P010", "Pizza jambon fromage",   "Traiteur",       "Marque D", "Traiteur"),
    ("P011", "Oeufs plein air x6",     "Oeufs",          "Marque F", "Traiteur"),
    ("P012", "Saucisse de volaille",   "Elabore",        "Marque B", "Volaille"),
]
dim_produit = pd.DataFrame(produits, columns=["code_produit", "libelle", "categorie", "marque", "pole"])

# DIM USINE (sites anonymises, regions generiques)
usines = [
    ("U01", "Usine 01", "Region Ouest",      "France"),
    ("U02", "Usine 02", "Region Ouest",      "France"),
    ("U03", "Usine 03", "Region Nord-Ouest", "France"),
    ("U04", "Usine 04", "Region Nord-Ouest", "France"),
    ("U05", "Usine 05", "Region Sud-Ouest",  "France"),
    ("U06", "Usine 06", "Region Ouest",      "France"),
    ("U07", "Usine 07", "Region Centre-Est", "France"),
    ("U08", "Usine 08", "Region Europe",     "Pologne"),
]
dim_usine = pd.DataFrame(usines, columns=["code_usine", "nom_usine", "region", "pays"])

prix_base = {
    "P001": (6.90, 5.30), "P002": (4.20, 3.10), "P003": (7.80, 5.60),
    "P004": (6.50, 4.70), "P005": (5.40, 3.60), "P006": (5.90, 4.10),
    "P007": (12.50, 9.20), "P008": (3.80, 2.40), "P009": (4.60, 3.00),
    "P010": (3.20, 2.10), "P011": (2.50, 1.70), "P012": (4.90, 3.40),
}
canaux = ["GMS", "RHF", "Export", "Industrie"]
canal_p = [0.55, 0.20, 0.15, 0.10]
dates = pd.date_range(DATE_START, DATE_END, freq="D")

def saisonnalite(d):
    m = d.month
    base = 1.0 + 0.25 * np.sin((m - 3) / 12 * 2 * np.pi)
    if m in (11, 12):
        base *= 1.35
    return base

# FACT VENTES
rows = []
for d in dates:
    s = saisonnalite(d)
    for _ in range(rng.integers(35, 60)):
        p = dim_produit.sample(1, random_state=rng.integers(1e9)).iloc[0]
        u = dim_usine.sample(1, random_state=rng.integers(1e9)).iloc[0]
        canal = rng.choice(canaux, p=canal_p)
        pu, cu = prix_base[p["code_produit"]]
        qte = int(max(1, rng.normal(180, 60) * s))
        remise = rng.uniform(0.0, 0.12) if canal in ("GMS", "Industrie") else rng.uniform(0.0, 0.05)
        ca = round(qte * pu * (1 - remise), 2)
        cout = round(qte * cu * rng.uniform(0.97, 1.06), 2)
        rows.append((d.date(), p["code_produit"], u["code_usine"], canal, qte, ca, cout))
fact_ventes = pd.DataFrame(rows, columns=["date", "code_produit", "code_usine", "canal", "quantite", "CA", "cout"])

# FACT PRODUCTION
prod_rows = []
for d in pd.date_range(DATE_START, DATE_END, freq="W-MON"):
    s = saisonnalite(d)
    for _, u in dim_usine.iterrows():
        for _, p in dim_produit.sample(rng.integers(4, 8), random_state=rng.integers(1e9)).iterrows():
            qte_prod = int(max(50, rng.normal(9000, 3000) * s))
            qte_rebut = int(qte_prod * rng.uniform(0.008, 0.045))
            prod_rows.append((d.date(), u["code_usine"], p["code_produit"], qte_prod, qte_rebut))
fact_production = pd.DataFrame(prod_rows, columns=["date", "code_usine", "code_produit", "qte_produite", "qte_rebut"])

# FACT STOCKS
stock_rows = []
for d in pd.date_range(DATE_START, DATE_END, freq="W-MON"):
    for _, u in dim_usine.iterrows():
        for _, p in dim_produit.sample(rng.integers(5, 9), random_state=rng.integers(1e9)).iterrows():
            pu, _ = prix_base[p["code_produit"]]
            stock_q = 0 if rng.uniform() < 0.06 else int(max(0, rng.normal(2500, 1200)))
            stock_val = round(stock_q * pu * 0.75, 2)
            stock_rows.append((d.date(), p["code_produit"], u["code_usine"], stock_q, stock_val))
fact_stocks = pd.DataFrame(stock_rows, columns=["date", "code_produit", "code_usine", "stock_qte", "stock_valeur"])

dim_produit.to_csv(OUT / "dim_produit.csv", index=False)
dim_usine.to_csv(OUT / "dim_usine.csv", index=False)
fact_ventes.to_csv(OUT / "fact_ventes.csv", index=False)
fact_production.to_csv(OUT / "fact_production.csv", index=False)
fact_stocks.to_csv(OUT / "fact_stocks.csv", index=False)

print("dim_produit:", len(dim_produit), "| dim_usine:", len(dim_usine))
print("fact_ventes:", len(fact_ventes), "| fact_production:", len(fact_production), "| fact_stocks:", len(fact_stocks))
print("marques:", sorted(dim_produit['marque'].unique()))
print("CA total:", round(fact_ventes['CA'].sum()/1e6, 1), "M EUR | marge:", round((1-fact_ventes['cout'].sum()/fact_ventes['CA'].sum())*100,1), "%")
