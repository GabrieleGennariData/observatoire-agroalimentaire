# Libreria misure DAX — Cockpit Agroalimentaire

> **Cos'è questo file:** la libreria documentata delle 30 misure, ognuna con la sua spiegazione. Serve a capire (e a rispondere in colloquio), non a essere incollato in blocco.
>
> **Per creare le misure in Power BI ci sono due strade** — vedi §0.3. Se vuoi la via rapida, usa `misure_dax_bulk.dax` (stesse 30 misure, stesso ordine, formato incollabile in un colpo solo).
>
> **Le misure sono in ordine di dipendenza:** dall'alto verso il basso, nessuna misura richiama una misura definita più sotto. Segui l'ordine del file e non incontrerai mai l'errore "impossibile trovare la misura".
>
> *Storia: la prima versione della libreria contava 43 misure. Ridotta a 28 il 2026-07-14 (decisione nel `WORKLOG.md`): via i doppioni e le varianti fotocopia, restano i tre pattern che contano — semi-additive stock, time intelligence, ranking dinamico. Il 2026-07-14, in fase di collaudo delle visual (F4), `CA N-1` è stata blindata con una guardia di comparabilità e sono state aggiunte `CA YTD N-1` e `Croissance CA YTD %` → **30 misure**.*

---

## 0. Prerequisiti

### 0.1 Tabella calcolata `dim_date`

`Modellizzazione → Nuova tabella`:

```dax
dim_date =
VAR DateDebut = DATE ( 2024, 1, 1 )
VAR DateFin = DATE ( 2026, 6, 30 )
RETURN
ADDCOLUMNS (
    CALENDAR ( DateDebut, DateFin ),
    "Année", YEAR ( [Date] ),
    "N° Mois", MONTH ( [Date] ),
    "Mois", FORMAT ( [Date], "MMM", "fr-FR" ),
    "Année-Mois", FORMAT ( [Date], "YYYY-MM" ),
    "N° Année-Mois", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Trimestre", "T" & QUARTER ( [Date] ),
    "Année-Trimestre", YEAR ( [Date] ) & "-T" & QUARTER ( [Date] ),
    "N° Année-Trimestre", YEAR ( [Date] ) * 10 + QUARTER ( [Date] ),
    "Semaine ISO", WEEKNUM ( [Date], 21 ),
    "Jour Semaine", FORMAT ( [Date], "ddd", "fr-FR" ),
    "N° Jour Semaine", WEEKDAY ( [Date], 2 )
)
```

Poi: tabella `dim_date` → **Contrassegna come tabella data** → colonna `Date`; relazioni `dim_date[Date]` → `fact_*[date]` (uno-a-molti, single-direction).

**Ordina per colonna** — obbligatorio su tutte e tre le etichette testuali, altrimenti Power BI le ordina alfabeticamente e l'asse temporale esce disordinato o invertito:

| Colonna (testo) | Ordina per colonna (numerica) |
|---|---|
| `Mois` | `N° Mois` |
| `Année-Mois` | `N° Année-Mois` |
| `Année-Trimestre` | `N° Année-Trimestre` |

*Perché conta:* `Année-Mois` in formato `YYYY-MM` sembra ordinarsi bene da solo (alfabetico ≈ cronologico), ma è una coincidenza di formato, non una garanzia del modello. La chiave numerica rende l'ordinamento una proprietà della `dim_date`, non del visual — e vale una risposta in colloquio.
Nel visual, poi: `...` → **Ordina asse** → `Année-Mois` → **crescente**.

### 0.2 Perché una date table

Le tre fact hanno granularità diverse (ventes giornaliera, production e stocks settimanali). Senza una dimensione data condivisa, uno slicer di periodo filtrerebbe una sola fact alla volta e la time intelligence non avrebbe un calendario continuo su cui lavorare. **È la prima domanda che ti faranno al colloquio: sappi rispondere in una frase.**

### 0.3 Come si creano materialmente le misure

Power BI Desktop offre due strade. Non sono equivalenti: la prima è quella che si usa nella pratica quotidiana, la seconda è quella giusta per caricare una libreria intera.

**Metodo A — Barra della formula (una misura alla volta).**
Seleziona la tabella `_Mesures` nel riquadro Dati → `Home → Nuova misura` → incolla **un solo blocco `dax`** di questo file (nome compreso, es. `CA Total = SUM ( fact_ventes[CA] )`) → Invio. Ripeti 28 volte. È lento ma è il flusso standard, e ogni misura la vedi nascere.

**Metodo B — Vista query DAX (tutte in blocco). ← consigliato**

1. Clicca l'icona **DAX** nella barra laterale sinistra (sotto Report / Dati / Modello): è la *vista query DAX*, nativa in Power BI Desktop, gratuita.
2. Apri `misure_dax_bulk.dax` con un editor di testo, **copia tutto**, incolla nella query vuota.
3. Sopra ogni riga `MEASURE _Mesures[...]` compare un link CodeLens **"Aggiorna modello: aggiungi nuova misura"**: cliccalo per aggiungere quella misura al modello. Le misure finiscono direttamente nella tabella `_Mesures` (è specificata nella sintassi `MEASURE _Mesures[...]`: nessun rischio di sbagliare tabella host).
4. In fondo al file c'è un `EVALUATE` di controllo: premi **Esegui** e vedrai subito i 5 KPI principali coi valori attesi. Se tornano, l'intera libreria è corretta.

> Il metodo B è anche un talking point: la vista query DAX è la feature che distingue chi usa Power BI da chi lo usa bene. Sapere che esiste (e che permette di versionare le misure in un file `.dax` in Git) vale una risposta intera in colloquio.

**In entrambi i casi:** dopo la prima misura, `_Mesures` → click destro su `Colonna1` → **Nascondi nella vista report**.

---

## 1. Finance (8 misure)

```dax
CA Total = SUM ( fact_ventes[CA] )
```
*Ricavo netto totale (la remise è già scontata nella colonna `CA`). Formato: € con 0 decimali. Valore atteso senza filtri: 43 083 885,65 €.*

```dax
Coût Total = SUM ( fact_ventes[cout] )
```
*Costo del venduto: base per marge e rotazione dello stock. Atteso: 32 461 713,95 €.*

```dax
Marge = [CA Total] - [Coût Total]
```
*Marge lorda in valore assoluto. Riusa le misure invece di risommare le colonne: una sola definizione di CA in tutto il modello.*

```dax
Taux de Marge % =
DIVIDE ( [Marge], [CA Total] )
```
*Marge in percentuale del CA. `DIVIDE` e non `/`: gestisce la divisione per zero senza errore. Atteso: 24,65%.*

```dax
Quantité Vendue = SUM ( fact_ventes[quantite] )
```
*Volume venduto in unità: il denominatore di ogni KPI supply chain.*

```dax
Nb Transactions = COUNTROWS ( fact_ventes )
```
*Numero di righe di vendita: cardinalità dell'attività commerciale. Atteso: 42 534.*

```dax
Prix de Vente Moyen =
DIVIDE ( [CA Total], [Quantité Vendue] )
```
*Prezzo medio effettivo per unità (atteso: 5,40 €). Media pesata, non `AVERAGE` sul prezzo unitario: sommare i ricavi e dividere per i volumi è l'unico modo corretto.*

```dax
Rang Produit (CA) =
IF (
    HASONEVALUE ( dim_produit[libelle] ),
    RANKX (
        ALLSELECTED ( dim_produit[libelle] ),
        [CA Total],
        ,
        DESC,
        DENSE
    )
)
```
*Posizione del prodotto per CA nella selezione corrente — è il pattern di **ranking dinamico**. `ALLSELECTED` è la chiave: ignora il filtro di riga della visual (altrimenti ogni prodotto sarebbe primo su se stesso) ma **rispetta** slicer e filtri di pagina: un prodotto può essere 1° in Export e 5° in GMS, ricalcolato a ogni click. `HASONEVALUE` impedisce alla riga Totale di mostrare un rango assurdo; `DENSE` evita i buchi in caso di ex aequo.*

---

## 2. Stock semi-additivo (2 misure) — pattern avanzato

> **Il concetto:** lo stock è una fotografia, non un flusso. Su un trimestre lo stock non è la somma dei 13 snapshot settimanali: è il valore dell'ultimo snapshot. Sommarlo è l'errore classico che un modellatore Power BI non deve fare.
>
> Questa sezione viene **prima** della Supply Chain perché `Couverture Stock` e `Rotation de Stock` richiamano `[Stock Qté]`.

```dax
Stock Qté =
LASTNONBLANKVALUE (
    dim_date[Date],
    SUM ( fact_stocks[stock_qte] )
)
```
*Giacenza a fine periodo. `LASTNONBLANKVALUE` scandisce le date di `dim_date` nel contesto di filtro e restituisce il valore dell'**ultima data con dati**: su un mese dà l'ultimo lunedì, su un anno l'ultimo snapshot dell'anno. Mai una somma. Nota: su un singolo giorno non-lunedì è BLANK — atteso, gli snapshot sono settimanali; la dashboard lavora a mese/trimestre e non incontra mai il caso.*

```dax
Valeur Stock =
LASTNONBLANKVALUE (
    dim_date[Date],
    SUM ( fact_stocks[stock_valeur] )
)
```
*Stessa logica sul valorizzato: è la misura da mettere nella card "Stock immobilisé". Atteso senza filtri (ultimo snapshot, 2026-06-29): ~588 806 €.*

---

## 3. Supply Chain (7 misure)

```dax
Nb Lignes Stock = COUNTROWS ( fact_stocks )
```
*Numero di righe snapshot (produit × usine × semaine): denominatore del tasso di rottura. Atteso: 6 840.*

```dax
Nb Ruptures =
CALCULATE (
    COUNTROWS ( fact_stocks ),
    fact_stocks[stock_qte] = 0
)
```
*Conta le combinazioni produit/usine/semaine a giacenza zero (atteso: 539). `CALCULATE` con predicato sulla colonna: filtro applicato, non un `IF` riga per riga.*

```dax
Taux de Rupture % =
DIVIDE ( [Nb Ruptures], [Nb Lignes Stock] )
```
*KPI centrale della pagina Supply Chain. Atteso: **7,88%**. Se leggi un altro numero senza filtri attivi, la relazione o la misura sono sbagliate.*

```dax
Ventes Moy Jour (Qté) =
DIVIDE (
    [Quantité Vendue],
    DISTINCTCOUNT ( fact_ventes[date] )
)
```
*Vendite medie giornaliere in unità: denominatore della couverture. Conta solo i giorni con vendite effettive, non i giorni di calendario.*

```dax
Couverture Stock (jours) =
DIVIDE ( [Stock Qté], [Ventes Moy Jour (Qté)] )
```
*Quanti giorni di vendita copre la giacenza attuale. Il KPI che un direttore supply chain guarda per primo. Atteso senza filtri: ~14,6 giorni.*

```dax
Stock Moyen Valorisé =
AVERAGEX (
    VALUES ( dim_date[Date] ),
    CALCULATE ( SUM ( fact_stocks[stock_valeur] ) )
)
```
*Media della giacenza valorizzata sugli snapshot del periodo. `AVERAGEX` su `VALUES(dim_date[Date])` ignora automaticamente i giorni senza snapshot (restituiscono BLANK), quindi la media resta corretta anche con granularità settimanale.*

```dax
Rotation de Stock =
DIVIDE ( [Coût Total], [Stock Moyen Valorisé] )
```
*Numero di volte in cui lo stock si rinnova nel periodo (COGS / stock medio). Un valore basso su un prodotto fresco è un allarme. Sull'intero periodo di 2,5 anni il valore è alto (~61): normale per il fresco, va letto su periodi brevi.*

---

## 4. Production (6 misure)

```dax
Qté Produite = SUM ( fact_production[qte_produite] )
```
*Volumi prodotti (additivo: sommare è corretto, a differenza dello stock). Atteso: ~54,55 M unità.*

```dax
Qté Rebut = SUM ( fact_production[qte_rebut] )
```
*Volumi scartati. Atteso: ~1,45 M unità.*

```dax
Taux de Rebut % =
DIVIDE ( [Qté Rebut], [Qté Produite] )
```
*Tasso di scarto: il KPI industriale del settore. Atteso: **2,65%**.*

```dax
Qté Produite Nette = [Qté Produite] - [Qté Rebut]
```
*Produzione utilizzabile, al netto degli scarti.*

```dax
Ratio Production / Ventes =
DIVIDE ( [Qté Produite Nette], [Quantité Vendue] )
```
*> 1 = si produce più di quanto si vende (lo stock cresce); < 1 = si sta smaltendo giacenza. Misura che attraversa due fact tables: dimostra che il modello a stella funziona. Nei dati sintetici produzione e vendite hanno scale diverse (~6,7): il valore assoluto conta meno del confronto tra prodotti.*

```dax
Écart Taux de Rebut vs Moy. Usines =
VAR TauxUsine = [Taux de Rebut %]
VAR TauxMoyenToutesUsines =
    CALCULATE ( [Taux de Rebut %], REMOVEFILTERS ( dim_usine ) )
RETURN
TauxUsine - TauxMoyenToutesUsines
```
*Benchmark: scarto di un sito rispetto alla media di tutti i siti. `REMOVEFILTERS` sulla sola `dim_usine` conserva il filtro di periodo e di prodotto — è il modo giusto di costruire un confronto "vs media".*

---

## 5. Time intelligence — YoY / YTD / MAT (7 misure) — pattern avanzato

> **Prerequisito assoluto:** `dim_date` marcata come tabella data. Senza, queste misure restituiscono numeri plausibili ma sbagliati.

```dax
CA N-1 =
VAR PremiereDateModele =
    CALCULATE ( MIN ( dim_date[Date] ), REMOVEFILTERS ( dim_date ) )
VAR DebutN1 =
    EDATE ( MIN ( dim_date[Date] ), -12 )
RETURN
    IF (
        DebutN1 >= PremiereDateModele,
        CALCULATE (
            [CA Total],
            SAMEPERIODLASTYEAR ( dim_date[Date] )
        )
    )
```
*CA dello stesso periodo dell'anno precedente, **con guardia di comparabilità**.*

*Perché la guardia (bug reale trovato in F4, 2026-07-14). La versione ingenua — `CALCULATE([CA Total], SAMEPERIODLASTYEAR(dim_date[Date]))` — è corretta a livello mensile ma **mente sul totale generale**. Senza filtri il contesto è `2024-01-01 → 2026-06-30` (30 mesi); `SAMEPERIODLASTYEAR` lo sposta su `2023-01-01 → 2025-06-30`, ma il 2023 non esiste nella `dim_date` e viene silenziosamente scartato. Restano 18 mesi: la misura confronta **30 mesi contro 18 mesi** e produce un +67,8% privo di senso.*

*La guardia verifica che l'inizio del periodo N-1 (`EDATE(..., -12)`) cada dentro il calendario del modello. Se no → BLANK. `REMOVEFILTERS(dim_date)` serve a leggere la prima data del **modello**, non della selezione. A grana mensile nulla cambia (giugno 2026 → giugno 2025 ✓); sui bordi del calendario e sul totale la misura tace invece di produrre un numero falso. **È un talking point forte: mostra che sai distinguere un risultato DAX corretto da un risultato di business corretto.***

```dax
Écart CA YoY % =
VAR CAN1 = [CA N-1]
RETURN
DIVIDE ( [CA Total] - CAN1, CAN1 )
```
*Crescita percentuale YoY. `DIVIDE` restituisce BLANK se il denominatore è BLANK o zero: nessun errore di divisione, nessun ∞ nella visual. Con `CA N-1` blindata, questa misura è BLANK su tutto il 2024 e sul totale generale — **usala nelle visual con asse temporale, mai in una card senza filtro di periodo** (per la card vedi `Croissance CA YTD %`).*

```dax
CA YTD =
TOTALYTD ( [CA Total], dim_date[Date] )
```
*Cumulato da inizio anno civile fino alla data del contesto. Per un anno fiscale diverso da gennaio si passa il terzo argomento (es. `"30/06"`).*

```dax
CA YTD N-1 =
CALCULATE (
    [CA YTD],
    SAMEPERIODLASTYEAR ( dim_date[Date] )
)
```
*Cumulato da inizio anno dell'anno precedente. `SAMEPERIODLASTYEAR` sposta il contesto di filtro indietro di 12 mesi, poi `TOTALYTD` ricalcola il cumulato **dentro** il contesto spostato: si annida time intelligence dentro time intelligence, ed è il modo canonico di farlo.*

```dax
Croissance CA YTD % =
VAR YTD_N = [CA YTD]
VAR YTD_N1 = [CA YTD N-1]
RETURN
    DIVIDE ( YTD_N - YTD_N1, YTD_N1 )
```
*La misura da mettere nella **card "Croissance CA (YTD vs N-1)"** della pagina Finance. Comparabile per costruzione: senza filtri confronta gen-giu 2026 contro gen-giu 2025 (6 mesi contro 6 mesi), non 30 contro 18. È la risposta al problema descritto sopra: quando il totale generale non è comparabile, non si aggiusta la percentuale — **si cambia la domanda**.*

```dax
CA MAT (12 mois glissants) =
CALCULATE (
    [CA Total],
    DATESINPERIOD (
        dim_date[Date],
        MAX ( dim_date[Date] ),
        -12,
        MONTH
    )
)
```
*Moving Annual Total: CA dei 12 mesi che terminano alla data selezionata. Neutralizza la stagionalità (qui forte: picco novembre-dicembre).*

```dax
Taux de Rebut % N-1 =
CALCULATE (
    [Taux de Rebut %],
    SAMEPERIODLASTYEAR ( dim_date[Date] )
)
```
*Stesso pattern applicato alla pagina Production: lo scarto migliora o peggiora rispetto all'anno scorso? Nota: si applica `SAMEPERIODLASTYEAR` alla **misura di rapporto**, non ai suoi componenti — il rapporto si ricalcola nel contesto spostato.*

---

## 6. Collaudo (criterio di accettazione)

Valori attesi **senza alcun filtro attivo**, calcolati dai CSV con `valida_dataset.py`:

| Misura | Valore atteso |
|---|---|
| `CA Total` | 43 083 885,65 € |
| `Coût Total` | 32 461 713,95 € |
| `Marge` | 10 622 171,70 € |
| `Taux de Marge %` | 24,65 % |
| `Prix de Vente Moyen` | 5,40 € |
| `Nb Transactions` | 42 534 |
| `Nb Lignes Stock` | 6 840 |
| `Nb Ruptures` | 539 |
| `Taux de Rupture %` | 7,88 % |
| `Taux de Rebut %` | 2,65 % |
| `CA N-1` sul 2024 | BLANK ← **corretto** |
| `CA N-1` senza filtri (totale) | BLANK ← **corretto** (periodo N-1 non comparabile) |
| `Écart CA YoY %` senza filtri | BLANK ← **corretto** |
| `Croissance CA YTD %` senza filtri | valore definito (gen-giu 2026 vs gen-giu 2025) |

Quattro controlli strutturali (dettagli e diagnosi in `F3-checklist-misure.md` §3):

- `Stock Qté` per mese **non deve crescere linearmente**: se lo fa, la semi-additività non funziona.
- `CA N-1` deve essere BLANK sul 2024 e ≈ 17,23 M€ sul 2025.
- `Écart CA YoY %` **deve essere BLANK sul totale generale**. Se mostra un numero (tipicamente ~+68%), la guardia di comparabilità non è stata applicata e stai confrontando 30 mesi con 18.
- `Rang Produit (CA)` deve **cambiare** applicando uno slicer su `fact_ventes[canal]`: è la prova che `ALLSELECTED` funziona.

## 7. Formattazione (2 minuti, effetto grande)

- Valuta €, 0 decimali: `CA Total`, `Coût Total`, `Marge`, `Valeur Stock`, `Stock Moyen Valorisé`, `CA N-1`, `CA YTD`, `CA YTD N-1`, `CA MAT`.
- Valuta €, 2 decimali: `Prix de Vente Moyen`.
- Percentuale: `Taux de Marge %`, `Taux de Rupture %`, `Taux de Rebut %`, `Écart CA YoY %`, `Croissance CA YTD %`, `Taux de Rebut % N-1`.
- Percentuale, 2 decimali: `Écart Taux de Rebut vs Moy. Usines`.
- Numero decimale, 1 decimale: `Couverture Stock (jours)`, `Rotation de Stock`, `Ratio Production / Ventes`.
- **Display folder** (5 cartelle): `01 Finance` (incluso `Rang Produit (CA)`), `02 Stock`, `03 Supply Chain`, `04 Production`, `05 Time Intelligence`. Un modello ordinato è la prima cosa che vede chi apre il `.pbix`.

**Totale: 30 misure** — 8 Finance (incluso il ranking dinamico), 2 stock semi-additivo, 7 Supply Chain, 6 Production, 7 time intelligence. Tutti i riferimenti a colonne verificati contro lo schema reale dei CSV.
