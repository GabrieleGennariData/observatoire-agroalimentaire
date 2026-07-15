"""Validazione F0 dei 5 CSV del progetto Cockpit Agroalimentaire.

Controlli: schema, integrita referenziale fact->dim, range e granularita date,
duplicati, valori negativi/nulli, rotture stock, tasso di scarto.
"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "dataset"
DATE_MIN = pd.Timestamp("2024-01-01")
DATE_MAX = pd.Timestamp("2026-06-30")


def load() -> dict[str, pd.DataFrame]:
    """Carica i 5 CSV con parsing delle date."""
    frames = {
        "dim_produit": pd.read_csv(DATA / "dim_produit.csv"),
        "dim_usine": pd.read_csv(DATA / "dim_usine.csv"),
        "fact_ventes": pd.read_csv(DATA / "fact_ventes.csv", parse_dates=["date"]),
        "fact_production": pd.read_csv(DATA / "fact_production.csv", parse_dates=["date"]),
        "fact_stocks": pd.read_csv(DATA / "fact_stocks.csv", parse_dates=["date"]),
    }
    return frames


def main() -> None:
    f = load()
    dp, du = f["dim_produit"], f["dim_usine"]
    fv, fp, fs = f["fact_ventes"], f["fact_production"], f["fact_stocks"]

    print("=== 1. VOLUMI E SCHEMA ===")
    for name, df in f.items():
        print(f"{name:16} righe={len(df):>7}  colonne={list(df.columns)}")

    print("\n=== 2. CHIAVI DIMENSIONI (unicita) ===")
    print("dim_produit.code_produit unico:", dp["code_produit"].is_unique, "| n =", dp["code_produit"].nunique())
    print("dim_usine.code_usine unico:", du["code_usine"].is_unique, "| n =", du["code_usine"].nunique())
    print("null nelle dim:", int(dp.isna().sum().sum() + du.isna().sum().sum()))

    print("\n=== 3. INTEGRITA REFERENZIALE fact -> dim ===")
    prods, usines = set(dp["code_produit"]), set(du["code_usine"])
    for name, df in [("fact_ventes", fv), ("fact_production", fp), ("fact_stocks", fs)]:
        orphan_p = set(df["code_produit"]) - prods
        orphan_u = set(df["code_usine"]) - usines
        print(
            f"{name:16} orfani produit={len(orphan_p)} {sorted(orphan_p) or ''} | "
            f"orfani usine={len(orphan_u)} {sorted(orphan_u) or ''} | "
            f"null FK={int(df[['code_produit', 'code_usine']].isna().sum().sum())}"
        )
    print("dim_produit non usati in ventes:", sorted(prods - set(fv["code_produit"])) or "nessuno")
    print("dim_usine non usati in ventes:", sorted(usines - set(fv["code_usine"])) or "nessuno")

    print("\n=== 4. RANGE E GRANULARITA DATE ===")
    for name, df in [("fact_ventes", fv), ("fact_production", fp), ("fact_stocks", fs)]:
        dmin, dmax = df["date"].min(), df["date"].max()
        ndays = df["date"].nunique()
        in_range = bool(dmin >= DATE_MIN and dmax <= DATE_MAX)
        gaps = ""
        if name == "fact_ventes":
            expected = pd.date_range(DATE_MIN, DATE_MAX, freq="D")
            missing = len(set(expected) - set(df["date"].unique()))
            gaps = f"| giorni mancanti nel range={missing}"
        else:
            dows = df["date"].dt.day_name().unique()
            gaps = f"| giorni settimana={list(dows)}"
        print(f"{name:16} {dmin.date()} -> {dmax.date()} | date distinte={ndays:>4} | in range={in_range} {gaps}")

    print("\n=== 5. QUALITA MISURE ===")
    print("-- fact_ventes")
    print("  quantite <= 0:", int((fv["quantite"] <= 0).sum()), "| CA <= 0:", int((fv["CA"] <= 0).sum()),
          "| cout <= 0:", int((fv["cout"] <= 0).sum()))
    print("  righe con cout > CA (marge negativa):", int((fv["cout"] > fv["CA"]).sum()),
          f"({(fv['cout'] > fv['CA']).mean() * 100:.2f}%)")
    print("  duplicati esatti:", int(fv.duplicated().sum()))
    ca, cout = fv["CA"].sum(), fv["cout"].sum()
    print(f"  CA totale: {ca / 1e6:.2f} M EUR | cout: {cout / 1e6:.2f} M EUR | marge: {(1 - cout / ca) * 100:.2f}%")
    print("  canaux:", fv["canal"].value_counts().to_dict())

    print("-- fact_production")
    print("  qte_produite <= 0:", int((fp["qte_produite"] <= 0).sum()), "| qte_rebut < 0:", int((fp["qte_rebut"] < 0).sum()))
    print("  rebut > produite:", int((fp["qte_rebut"] > fp["qte_produite"]).sum()))
    taux = fp["qte_rebut"].sum() / fp["qte_produite"].sum()
    print(f"  taux de rebut globale: {taux * 100:.2f}% | min riga={fp['qte_rebut'].div(fp['qte_produite']).min() * 100:.2f}%"
          f" max riga={fp['qte_rebut'].div(fp['qte_produite']).max() * 100:.2f}%")
    print("  duplicati (date, usine, produit):", int(fp.duplicated(subset=["date", "code_usine", "code_produit"]).sum()))

    print("-- fact_stocks")
    ruptures = (fs["stock_qte"] == 0).sum()
    print(f"  righe stock_qte = 0 (rupture): {ruptures} ({ruptures / len(fs) * 100:.2f}%)")
    print("  stock_qte < 0:", int((fs["stock_qte"] < 0).sum()), "| stock_valeur < 0:", int((fs["stock_valeur"] < 0).sum()))
    print("  incoerenze qte=0 ma valeur>0:", int(((fs["stock_qte"] == 0) & (fs["stock_valeur"] > 0)).sum()))
    print("  duplicati (date, produit, usine):", int(fs.duplicated(subset=["date", "code_produit", "code_usine"]).sum()))
    print(f"  stock medio valorizzato per snapshot: {fs.groupby('date')['stock_valeur'].sum().mean() / 1e6:.2f} M EUR")
    rup_by_usine = fs.assign(rupture=fs["stock_qte"].eq(0)).groupby("code_usine")["rupture"].mean().mul(100).round(2)
    print("  taux rupture per usine (%):", rup_by_usine.to_dict())

    print("\n=== 6. COPERTURA INCROCIATA (per il modello a stella) ===")
    print("  coppie produit x usine in ventes:", fv.groupby(["code_produit", "code_usine"]).ngroups, "/ 96 possibili")
    print("  produits in stocks ma mai venduti:", sorted(set(fs["code_produit"]) - set(fv["code_produit"])) or "nessuno")
    print("  produits prodotti ma mai venduti:", sorted(set(fp["code_produit"]) - set(fv["code_produit"])) or "nessuno")


if __name__ == "__main__":
    main()
