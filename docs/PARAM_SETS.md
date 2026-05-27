# PARAM_SETS.md — Externe Annahmen-Vergleichspunkte als first-class Konstrukt

## Was ist ein ParamSet?

Ein **ParamSet** bündelt das Default-Annahmen-Substrat einer externen
Modellfamilie (PyPSA-DE/Ariadne, NEA-IEA PCGE, BNEF, Fraunhofer ISE, …)
als reproduzierbares Override-Dict für `compute_path`. Es übersetzt
die Tech-Namen der externen Quelle auf enesys-Tech-IDs und liefert
Trajektorien-Werte für CAPEX, FOM, VOM, WACC und Brennstoffpreise über
die Stützstellen 2030 / 2040 / 2050.

## Abgrenzung zu CAMP_RANGES

| Aspekt | CAMP_RANGES | ParamSet |
|---|---|---|
| Argument | politisch | methodisch |
| Frage | »Was würde dieses Lager als Bandbreite akzeptieren?« | »Bleibt unser Befund unter dem Annahmen-Substrat eines anderen Modells erhalten?« |
| Inhalt | EE-/Atom-/Bestand-optimistisch, Neutral-Default | konkrete Default-Werte einer externen Quelle |
| Repräsentation | Bandbreiten pro Tech | Stützstellen-Trajektorie pro Tech |
| Override-Mechanismus | gemeinsam: `param_overrides` in `compute_path` | gemeinsam: `param_overrides` in `compute_path` |

Beide Strukturen sind kompatibel zur Tornado-/Monte-Carlo-Infrastruktur.

## Verwendung

```python
from enesys import rolling_all_paths

# Standard enesys-Annahmen (Rolling 30-J ab 2026, kanonisch):
default = rolling_all_paths(year=2026)

# Mit externem Substrat (Ariadne/PyPSA):
ariadne = rolling_all_paths(year=2026, param_set="ariadne_pypsa")

# Verfügbare Sets:
from enesys import PARAM_SETS
print(list(PARAM_SETS))
```

Pfad-für-Pfad-Aufruf:

```python
from enesys import compute_path

result = compute_path(
    "ee_gas",
    years=[2030, 2040, 2050],
    param_set="ariadne_pypsa",  # Trajektorie wirkt jahresweise
)
```

Kombination mit konstanten Overrides (z.B. für Monte-Carlo-Sample):

```python
# Trajektorie als Basis, konstanter Override hat Vorrang:
compute_path(
    "ee_gas",
    [2045],
    param_set="ariadne_pypsa",
    param_overrides={"co2_price_eur_t": 200.0},
)
```

CLI-Inspektion (Override-Werte für ein Jahr anzeigen):

```bash
python -m enesys.core.param_sets.ariadne_pypsa
```

## Verfügbare Sets

### ariadne_pypsa

PyPSA-Tech-Data Default-Annahmen 2030 / 2040 / 2050 — das Annahmen-Substrat
der BMBF-Ariadne-Modellfamilie.

- **Quelle:** [PyPSA/technology-data](https://github.com/PyPSA/technology-data)
- **Primäre Zitate:** Lazard 16.0 (Nuclear, Coal), Danish Energy Agency
  (Renewables, Gas, Electrolysis), ENTSO-E/ENTSOG TYNDP 2024 (Brennstoffpreise)
- **Stützstellen:** 2030 / 2040 / 2050
- **Preisbasis:** EUR_2025

**Methodische Einordnung.** PyPSA-DE ist als Modell-Framework EE-leaning
(Default-Szenarien ohne Kernkraft); die einzelnen Parameter-Werte sind
jedoch sauber primärquellen-gestützt und nicht atom-feindlich.
Nuclear-CAPEX (10 806 EUR/kW, Lazard 16.0) ist fast deckungsgleich mit
enesys-neutral (11 000 EUR/kW).


## Wie füge ich ein neues Set hinzu?

1. **Template kopieren:**
   ```bash
   cp src/enesys/core/param_sets/_template.py src/enesys/core/param_sets/{name}.py
   ```
2. **Werte hard-coden** aus der Primärquelle. *Nicht* zur Laufzeit aus CSVs
   laden — explizite Werte im Code sind das Ziel für Reproduzierbarkeit.
3. **Mapping anpassen:**
   - Externe Tech-Namen → enesys-Tech-IDs in `_TECH_MAPPING`
   - Externe Fuel-Namen → enesys-Fuel-IDs in `_FUEL_MAPPING`
   - Vorsicht bei 1:n-Mappings (z.B. externes »nuclear« → enesys
     `kkw_bestand` + `kkw_neubau_epr` + `kkw_neubau_smr`)
4. **Caveats vollständig dokumentieren** — was differiert methodisch zwischen
   der Quelle und enesys? Lerneffekte, WACC-Behandlung, Bauzeit-
   Modellierung, Fuel-Preise.
5. **Registry-Eintrag** in `src/enesys/core/param_sets/__init__.py`:
   ```python
   from enesys.core.param_sets.{name} import {NAME}_SET
   PARAM_SETS[{NAME}_SET.name] = {NAME}_SET
   ```
6. **Convergence-Test** `tests/consistency/test_{name}_convergence.py`
   nach Vorbild von `test_ariadne_convergence.py`. Sechs Test-Slots:
   Registry-Eintrag, Override-Keys-Hygiene, LCOE-Plausibilität,
   Pfad-Reihenfolge-Konvergenz, Diff-Bandbreite, Trajektorie-Interpolation.

## Daten-Konventionen

### Trajektorie-Wert-Format

```python
{
    # zeitkonstant:
    "kkw_neubau_epr.capex_eur_kw": 10805.70,

    # Stützstellen (≥ 1, beliebige Jahre):
    "pv.capex_eur_kw": {2030: 482.48, 2040: 403.38, 2050: 367.87},

    # nur 2 Stützstellen — Interpolation zwischen denen, konstant außerhalb:
    "steinkohle.preis_eur_mwh": {2030: 7.82, 2050: 6.72},
}
```

`ParamSet.overrides(year)` löst Stützstellen via linearer Interpolation
auf. Außerhalb des Bereichs wird der nächstgelegene Rand-Wert konstant
fortgesetzt — keine Trend-Extrapolation, weil Lerneffekte jenseits der
Quell-Horizonte spekulativ sind.

### Erlaubte Override-Felder

`compute_path` akzeptiert nur die folgenden Override-Keys:

| Key-Muster | Bedeutung |
|---|---|
| `<tech_id>.capex_eur_kw` | TechEntry-CAPEX in EUR/kW |
| `<tech_id>.wacc_pct` | WACC als **Anteil** (0.0536 = 5.36%) — *Name ist irreführend* |
| `<tech_id>.opex_fix_eur_kw_a` | fixe Betriebskosten in EUR/kW/a |
| `<tech_id>.opex_var_eur_mwh` | variable Betriebskosten in EUR/MWh |
| `<tech_id>.vlh_normal` | Volllaststunden im Normalbetrieb |
| `<fuel_id>.preis_eur_mwh` | Brennstoffpreis in EUR/MWh_th |
| `co2_price_eur_t` | globaler CO₂-Preis |

Andere Felder (lifetime, efficiency etc.) sind nicht über
`param_overrides` überschreibbar und müssen ggf. tech-inventory-seitig
geändert werden.

### Werte hard-coden statt CSV laden

Externe Quellen werden bewusst hard-coded in `*.py` übernommen, nicht
zur Laufzeit aus CSV gelesen. Begründung:

- **Reproduzierbarkeit** ohne externe Datei-Abhängigkeit
- **Explizite Werte im Code** — Lesbarkeit, Diff-fähig
- **Bewusste Re-Pflege** bei Quell-Updates statt stiller Drift
- **Keine pandas-Abhängigkeit** für den Override-Pfad

Jede Set-Datei dokumentiert im Modul-Docstring den Quell-Commit/-Stand,
damit der Wert-Übertrag rückverfolgbar bleibt.

## Architektur-Robustheit

Bei neuen Sets ändert sich am Bestands-Code:

- **Eine neue Datei** `src/enesys/core/param_sets/{name}.py`
- **Eine Registry-Zeile** in `__init__.py`
- **Optional** ein eigener Convergence-Test

**Was nicht angefasst werden muss:** `compute_path()`, `baseline_all_paths()`,
`path_model.py`, CAMP_RANGES, bestehende Tests, Tech-/Fuel-Inventare.

**Bekannte Risiko-Stelle:** enesys-Tech-ID-Umbenennung würde alle Sets
gleichzeitig brechen. Mitigation: `assert_known_keys()` im Convergence-Test
failt mit klarer Liste der unbekannten Keys — Refactor-Pflicht wird sichtbar
statt durch obskuren Modell-Crash.

## Multi-Year-Overrides

`compute_path` unterstützt drei Override-Quellen mit klarer Priorität:

1. `param_set` (Trajektorie, niedrigste Priorität)
2. `param_overrides` (konstant über alle Jahre)
3. `param_overrides_yearly` (pro Jahr, höchste Priorität)

Bei mehrjährigen Läufen wird die ParamSet-Trajektorie jahresweise aufgelöst
— die Lerneffekte wirken also echt, kein Bezugsjahr-Mittel.
