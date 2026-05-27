"""Pfad-spezifische Profile-Costs (H1) und DSM-Rabatt (H2).

Diese Erweiterung modelliert zwei ökonomische Effekte, die die
Mengen-Bilanz im Pfad-Modell nicht direkt erfasst:

H1 — **Profile-Costs (Stunden-Versatz-Marktwert-Asymmetrie).**
Variable EE-Anlagen produzieren disproportional in Stunden mit
niedrigem Strompreis (sonnige Mittage, windige Nächte). Der
Marktwert der EE-Erzeugung sinkt mit steigender Penetration. Hirth/
Ueckerdt/Edenhofer (2015) quantifizieren das bei 30-40 % Wind-Anteil
mit Integration-Costs 25-35 €/MWh, davon Profile-Komponente 15-25
€/MWh.

H2 — **DSM-Rabatt (Lastflexibilität-Wertschöpfung).**
Verschiebbare Lasten (Wärmepumpen, E-Autos, Industrie) können EE-
Spitzen ausgleichen und H2-Backup-Stunden vermeiden. Agora (2024)
quantifiziert 100 TWh flexible Haushaltslast bis 2035 → ~4,8 Mrd EUR
Einsparung = ~0,48 ct/kWh System-Mittel.

---

## Methodische Anmerkung: Double-Counting-Vermeidung

Die Sekundär-Schicht (`_sekundaer_aufschlag` in path_model.py) enthält
bereits drei Komponenten, die Teile von Hirths Integration-Costs
abdecken:

| Hirth-Komponente | Sekundär-Pendant | Status |
|---|---|---|
| Grid-Cost (Netz-Erweiterung VRE) | _NETZ_EE_AUFSCHLAG_CT_KWH × ee_anteil | abgedeckt (2,0 ct max bei 100 % EE) |
| Balancing-Cost (Speicher, Regelreserve) | Speicher-Komponente + Stabilität-Komponente | abgedeckt (~2,0 ct EE-GAS) |
| **Profile-Cost (Markt­wert-Asymmetrie)** | **fehlt in der Sekundär-Schicht** | **diese Datei deckt das** |

Konsequenz: Der volle Hirth-Wert (2,0-2,5 ct EE) darf NICHT als reiner
Profile-Aufschlag addiert werden — das wäre Double-Counting mit der
Sekundär-Schicht (Netz + Speicher + Stabilität zusammen ~7,6 ct EE-GAS,
die schon Hirth-Balancing + Hirth-Grid enthalten).

**Lit-konservative Setzung:**
- EE-Profile +0,7 ct/kWh (Mitte Hirth-Bandbreite minus
  Internalisierungs-Abzug)
- KKW-Profile +0,1 ct/kWh (KKW-Bandlast wirkt Stunden-Versatz
  entgegen, geringerer Profile-Cost)
- BESTAND/WEITER-SO +0,3 ct/kWh (Mittel, weil teilweise EE-Anteil)

**H2-DSM-Aufteilung (lager-abhängig):**
- `neutral_default` / `ee_optimistic`: EE-Pfade −0,5 ct/kWh,
  KKW-Pfade −0,15 ct/kWh (Grenznutzen-Asymmetrie nach
  AGORA-DEMAND-FLEX-2024 + ARIADNE-FLEX-2024 — DSM-Hebel in volatilen
  EE-Systemen höher als in
  Bandlast-dominierten).
- `atom_optimistic` / `bestand_optimistic` / `weiterso_optimistic`:
  EE und KKW symmetrisch −0,3 ct/kWh (Atom-Lager-Position »KKW
  verhindert DSM-Vorteil für EE nicht«).
- BESTAND/WEITER-SO −0,3 ct/kWh konstant über alle Lager (Misch-Pfade
  haben keine eigene Differenzierungs-Position).

---

## Sensi-Achse über CAMP_RANGES

H1 und H2 sind als Sensi-Achsen modelliert: sechs CAMP_RANGES-Einträge
(`profile_cost_ee_ct_kwh`, `profile_cost_kkw_ct_kwh`,
`profile_cost_misch_ct_kwh`, `dsm_ee_ct_kwh`, `dsm_kkw_ct_kwh`,
`dsm_misch_ct_kwh`) tragen je Lager unterschiedliche Werte.

Lager-Spreizung folgt Quellen-Memos:
- H1 Profile-Cost: Hirth/Ueckerdt-Obergrenze vs. Agora-Untergrenze,
  korrigiert um sekundär-bereits-internalisierte Komponenten. Die
  KKW-Achse ist nicht-monoton — das EE-Lager schreibt KKW eine höhere
  Profile-Cost zu als das atom-Lager.
- H2 DSM: AGORA-DEMAND-FLEX-2024 + ARIADNE-FLEX-2024 stützen die EE-vs-KKW-Asymmetrie
  qualitativ (Grenznutzen DSM steigt mit Preisvolatilität). Atom-
  und Bestand-Lager symmetrisieren die Asymmetrie (»KKW-Bandlast
  verhindert DSM-Vorteil für EE nicht«).

`param_overrides`-Keys (für Monte-Carlo / Tornado, analog zu anderen
Modell-Hebeln):
- `"profile_cost_ee_ct_kwh"` / `"profile_cost_kkw_ct_kwh"` /
  `"profile_cost_misch_ct_kwh"`
- `"dsm_ee_ct_kwh"` / `"dsm_kkw_ct_kwh"` / `"dsm_misch_ct_kwh"`

---

## Lit-Quellen

- Hirth, Ueckerdt, Edenhofer (2015): "Integration costs revisited",
  Renewable Energy 74, 925-939
- Hirth (2013): "Market Value of Variable Renewables",
  Energy Economics 38, 218-236
- Agora Energiewende (2024): "Haushalts-Flexibilität bis 2035"
- Ariadne (2024): "Flexibilität deutsches Energiesystem bis 2045"
- DIW/Schill/Neuhoff/Kittel/Kröger/Roth (2024) SichER-Studie
"""

from enesys.core.camp_ranges import CAMP_RANGES

_PATH_ID_ZU_PROFILE_KEY: dict[str, str] = {
    "ee_gas": "profile_cost_ee_ct_kwh",
    "ee_h2": "profile_cost_ee_ct_kwh",
    "kkw_gas": "profile_cost_kkw_ct_kwh",
    "kkw_h2": "profile_cost_kkw_ct_kwh",
    "bestand": "profile_cost_misch_ct_kwh",
    "weiterso": "profile_cost_misch_ct_kwh",
}

_PATH_ID_ZU_DSM_KEY: dict[str, str] = {
    "ee_gas": "dsm_ee_ct_kwh",
    "ee_h2": "dsm_ee_ct_kwh",
    "kkw_gas": "dsm_kkw_ct_kwh",
    "kkw_h2": "dsm_kkw_ct_kwh",
    "bestand": "dsm_misch_ct_kwh",
    "weiterso": "dsm_misch_ct_kwh",
}


def profile_cost_surcharge(
    path_id: str,
    camp: str = "neutral_default",
    param_overrides: dict[str, float] | None = None,
) -> float:
    """Pfad-spezifischer Profile-Cost-Aufschlag (H1) in ct/kWh.

    Wird im LCOE pro Pfad als zusätzlicher Aufschlag addiert, parallel
    zur Sekundär-Schicht (Netz/Speicher/Stabilität).

    Auflösungs-Reihenfolge:
    1. ``param_overrides[<lager_key>]`` (Monte-Carlo / Tornado)
    2. ``LAGER_RANGES[<lager_key>][lager]``

    ``lager_key`` ist eines aus ``profile_cost_ee_ct_kwh`` /
    ``profile_cost_kkw_ct_kwh`` / ``profile_cost_misch_ct_kwh``.
    """
    lager_key = _PATH_ID_ZU_PROFILE_KEY.get(path_id)
    if lager_key is None:
        return 0.0
    if param_overrides and lager_key in param_overrides:
        return float(param_overrides[lager_key])
    spec = CAMP_RANGES[lager_key]
    return float(spec.get(camp, spec["neutral_default"]))  # type: ignore[arg-type]


def dsm_rebate(
    path_id: str,
    camp: str = "neutral_default",
    param_overrides: dict[str, float] | None = None,
) -> float:
    """Pfad-spezifischer DSM-Rabatt (H2) in ct/kWh (Rückgabe negativ).

    Wird im LCOE pro Pfad addiert (negativer Wert = Rabatt). H2 ist als
    Sensi-Achse über drei CAMP_RANGES-Einträge modelliert
    (``dsm_ee_ct_kwh``, ``dsm_kkw_ct_kwh``, ``dsm_misch_ct_kwh``).

    Auflösungs-Reihenfolge:
    1. ``param_overrides[<lager_key>]`` (Monte-Carlo / Tornado)
    2. ``CAMP_RANGES[<lager_key>][camp]``
    """
    lager_key = _PATH_ID_ZU_DSM_KEY.get(path_id)
    if lager_key is None:
        return 0.0
    if param_overrides and lager_key in param_overrides:
        return float(param_overrides[lager_key])
    spec = CAMP_RANGES[lager_key]
    return float(spec.get(camp, spec["neutral_default"]))  # type: ignore[arg-type]


def combined_surcharge(
    path_id: str,
    camp: str = "neutral_default",
    param_overrides: dict[str, float] | None = None,
) -> float:
    """H1 + H2 zusammen für ``path_id``. Netto-Wirkung in ct/kWh.

    Beide Komponenten sind lager-/override-abhängig.

    Beispiel-Werte (neutral_default-Lager):
    - ee_gas: +0,7 - 0,5 = +0,2 ct/kWh netto
    - kkw_gas: +0,1 - 0,15 = -0,05 ct/kWh netto
    - bestand: +0,3 - 0,3 = 0,0 ct/kWh netto
    - weiterso: +0,3 - 0,3 = 0,0 ct/kWh netto

    Beispiel atom_optimistic-Lager (DSM-Asymmetrie aufgehoben):
    - ee_gas: +1,0 - 0,3 = +0,7 ct/kWh netto
    - kkw_gas: +0,1 - 0,3 = -0,2 ct/kWh netto
    """
    return profile_cost_surcharge(path_id, camp, param_overrides) + dsm_rebate(
        path_id, camp, param_overrides
    )
