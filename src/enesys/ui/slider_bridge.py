"""Slider bridge for the Streamlit compare view.

Produces a ``param_overrides`` dict for ``compute_path(...)`` from a set
of slider values. The UI layout follows three layers:

- **Camp dropdown** as primary control (five camps: ``neutral_default``,
  ``ee_optimistic``, ``atom_optimistic``, ``bestand_optimistic``,
  ``weiterso_optimistic``) — selects the model setting.
- **Top levers** as always-visible override sliders: NEP realisation
  rate, nuclear realisation rate, CO₂ price (~80 % of the tornado
  effect).
- **Three expander groups** with 17 additional levers: CAPEX (8), WACC
  (6), fuel prices (3) — for full override resolution.

Default behaviour: choosing a camp loads the camp-typical slider values
and emits no overrides. A slider move that pushes a value away from the
camp default becomes an override.

Every slider carries a primary-source tag (``source_tag``) matching an
anchor in ``docs/SOURCES.md`` so the Streamlit Sources page can resolve
it to a clickable citation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

# Camp definition (book-consistent with the parameter-variation spec).
LAGER_OPTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "neutral_default",
        "Neutral (Default)",
        "Neutral (default)",
        "Empirical midpoint: NEP realisation 0.65 / nuclear realisation 0.40 / CO₂ 120 €/t.",
    ),
    (
        "ee_optimistic",
        "EE-Lager",
        "Renewables camp",
        "Optimistic on renewables build-out: low EE CAPEX/WACC, high CO₂ price.",
    ),
    (
        "atom_optimistic",
        "Atom-Lager",
        "Nuclear camp",
        "Optimistic on nuclear new-build: low nuclear WACC, low CO₂ price.",
    ),
    (
        "bestand_optimistic",
        "Bestand-Lager",
        "Existing-fleet camp",
        "Pragmatic-conservative: low realisation rates, high reliance on the existing fleet.",
    ),
    (
        "weiterso_optimistic",
        "WEITER-SO",
        "Status quo without decision",
        "Passive extrapolation of today's mix: no programme, market-driven assumptions.",
    ),
)


@dataclass(frozen=True)
class SliderSpec:
    """Specification for a single slider in the override panel.

    Attributes
    ----------
    lo, hi, step
        Numeric bounds and stride.
    fmt
        Python format string used for the displayed value.
    label_de, label_en
        Slider label, per language.
    group
        Expander group: ``top``, ``capex``, ``wacc``, or ``fuel``.
    tooltip_de, tooltip_en
        One-line explanation shown in the slider's help tooltip.
    source_tag
        Citation tag matching an anchor in ``docs/SOURCES.md``. Rendered
        in the tooltip and linked to the Sources page.
    """

    lo: float
    hi: float
    step: float
    fmt: str
    label_de: str
    label_en: str
    group: str
    tooltip_de: str
    tooltip_en: str
    source_tag: str


SLIDER_SPEC: dict[str, SliderSpec] = {
    # --- Top levers (always visible) -----------------------------------
    "nep_realization_rate": SliderSpec(
        lo=0.40,
        hi=1.00,
        step=0.05,
        fmt="%.2f",
        label_de="NEP-Realisierungsgrad",
        label_en="NEP realisation rate",
        group="top",
        tooltip_de=(
            "Anteil der NEP-Sollwerte (Übertragungsnetz- und EE-Ausbau), der "
            "tatsächlich realisiert wird — 1.0 = Plan-Soll, 0.65 = empirischer "
            "Mittelwert der vergangenen Jahre (BNetzA Q4-2025).\n\n"
            "Treibt strukturell den EE-Hochlauf in allen aktiven Pfaden. "
            "Niedrigere Werte verlangsamen den EE-Ausbau und erhöhen den "
            "fossilen Brücken-Bedarf entsprechend.\n\n"
            "Lager-Welt-Belief:\n"
            "- **EE-Lager** 0.85 — Annahme, dass die Politik den Plan "
            "  weitgehend realisiert.\n"
            "- **Neutral** 0.65 — empirischer Mittelwert (FOAK-Anker).\n"
            "- **Atom-Lager** 0.50 — »weniger Trassen wenn KKW Grundlast "
            "  trägt«.\n"
            "- **Bestand-Lager** 0.45 — gedrosselte Politik, EU-Resilienz "
            "  korrigiert nach oben.\n"
            "- **WEITER-SO** 0.30 — passive Trägheit, historisches Tempo "
            "  ohne aktive Politik.\n\n"
            "*Quelle:* BNETZA-MON-Q4-2025."
        ),
        tooltip_en=(
            "Share of the NEP target build-out (transmission grid and "
            "renewables) that is actually realised — 1.0 = plan target, "
            "0.65 = empirical average of recent years (BNetzA Q4-2025).\n\n"
            "Structurally drives the renewables ramp-up in every active "
            "pathway. Lower values slow the renewables build-out and raise "
            "the fossil bridge demand accordingly.\n\n"
            "Camp world-belief:\n"
            "- **EE camp** 0.85 — assumes policy largely delivers the plan.\n"
            "- **Neutral** 0.65 — empirical midpoint (FOAK anchor).\n"
            "- **Nuclear camp** 0.50 — 'fewer transmission lines needed if "
            "  nuclear carries baseload'.\n"
            "- **Existing-fleet camp** 0.45 — dampened policy, EU "
            "  resilience corrects upwards.\n"
            "- **WEITER-SO** 0.30 — passive inertia, historical rate "
            "  without active policy.\n\n"
            "*Source:* BNETZA-MON-Q4-2025."
        ),
        source_tag="BNETZA-MON-Q4-2025",
    ),
    "nuclear_realization_rate": SliderSpec(
        lo=0.20,
        hi=1.00,
        step=0.05,
        fmt="%.2f",
        label_de="KKW-Realisierungsgrad",
        label_en="Nuclear realisation rate",
        group="top",
        tooltip_de=(
            "Anteil des KKW-Neubau-Plans, der innerhalb der modellierten "
            "Bauzeit tatsächlich ans Netz geht. 1.0 = nominaler Plan, "
            "0.20–0.40 = empirisch realisierte Quote (Hinkley Point C, "
            "Flamanville, Olkiluoto).\n\n"
            "Lager-Welt-Belief:\n"
            "- **EE-Lager** 0.20 — Cour-des-Comptes-Empirie als oberes "
            "  Limit, niedrige Realgrade wegen Bauzeit-Überläufen und "
            "  NPS-Verzögerungen.\n"
            "- **Neutral / Bestand / WEITER-SO** 0.40 — empirischer "
            "  Mittelwert westlicher FOAK-Projekte.\n"
            "- **Atom-Lager** 1.00 — nächste EPR-/SMR-Generation mit "
            "  ausgereiftem Lieferketten- und Genehmigungsregime erfüllt "
            "  Plan-Bauzeit.\n\n"
            "Wirkt nur auf KKW-Pfade (KKW-GAS, KKW-H2); Bestand/"
            "WEITER-SO-Pfade enthalten keinen KKW-Neubau.\n\n"
            "*Quellen:* COURDESCOMPTES-FLAM (primär), EDF-HPC, NAO-HPC-2017."
        ),
        tooltip_en=(
            "Share of the nuclear new-build plan that actually connects to "
            "the grid within the modelled build time. 1.0 = nominal plan, "
            "0.20–0.40 = empirically realised rate (Hinkley Point C, "
            "Flamanville, Olkiluoto).\n\n"
            "Camp world-belief:\n"
            "- **EE camp** 0.20 — Cour des Comptes empirics as upper "
            "  bound, low realisation on the back of construction-time "
            "  overruns and NPS delays.\n"
            "- **Neutral / Existing-fleet / WEITER-SO** 0.40 — empirical "
            "  midpoint of Western FOAK projects.\n"
            "- **Nuclear camp** 1.00 — next EPR/SMR generation with "
            "  mature supply chain and licensing regime delivers planned "
            "  build time.\n\n"
            "Active only on KKW pathways (KKW-GAS, KKW-H2); existing-"
            "fleet / WEITER-SO pathways have no nuclear new-build.\n\n"
            "*Sources:* COURDESCOMPTES-FLAM (primary), EDF-HPC, NAO-HPC-2017."
        ),
        source_tag="COURDESCOMPTES-FLAM",
    ),
    "co2_price_eur_t": SliderSpec(
        lo=80.0,
        hi=180.0,
        step=5.0,
        fmt="%.0f",
        label_de="CO₂-Preis (€/t)",
        label_en="CO₂ price (€/t)",
        group="top",
        tooltip_de=(
            "ETS-CO₂-Preis 2030 in der Forward-Cost-Rechnung. Wirkt direkt "
            "auf fossile Brennstoff-Pönale und damit auf den Brücken-Pfad "
            "von WEITER-SO/BESTAND/EE-GAS.\n\n"
            "Lager-Spannweite (EU-Kommissions-Szenarien 80–180 €/t):\n"
            "- **EE-Lager** 160 €/t — folgt der ambitionierten ETS-Reform "
            "  (Tightening Linear Reduction Factor + EHS-Ausweitung).\n"
            "- **Atom-Lager** 150 €/t — ebenfalls ambitioniert (CO₂-Preis "
            "  ist klassisches Atom-Lager-Argument).\n"
            "- **Neutral / WEITER-SO** 130 €/t — Mittelwert der Pfade.\n"
            "- **Bestand-Lager** 100 €/t — argumentiert konservativ, um "
            "  fossile Erdgas-Brücke zu rechtfertigen.\n\n"
            "*Quelle:* EUKOM-2024 (ETS-Reform-Bewertung 2024, CO₂-Preispfade)."
        ),
        tooltip_en=(
            "ETS CO₂ price in 2030 used in the forward-cost calculation. "
            "Acts directly on fossil-fuel penalties and therefore on the "
            "bridge phase of WEITER-SO/BESTAND/EE-GAS.\n\n"
            "Camp spread (EU Commission scenarios 80–180 €/t):\n"
            "- **EE camp** 160 €/t — follows an ambitious ETS reform "
            "  (tightening Linear Reduction Factor + EHS expansion).\n"
            "- **Nuclear camp** 150 €/t — also ambitious (a high CO₂ price "
            "  is the classic pro-nuclear argument).\n"
            "- **Neutral / WEITER-SO** 130 €/t — the midpoint of the paths.\n"
            "- **Existing-fleet camp** 100 €/t — argues conservatively to "
            "  justify the fossil natural-gas bridge.\n\n"
            "*Source:* EUKOM-2024 (ETS reform assessment 2024, CO₂ price paths)."
        ),
        source_tag="EUKOM-2024",
    ),
    # --- CAPEX levers (expander) ---------------------------------------
    "pv.capex_eur_kw": SliderSpec(
        lo=400.0,
        hi=700.0,
        step=10.0,
        fmt="%.0f",
        label_de="PV-CAPEX (€/kW)",
        label_en="PV CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "Spezifische Investitionskosten neu errichteter Utility-Scale-PV "
            "in Deutschland. ISE-2024 nennt eine Bandbreite von 530–1.600 €/kW "
            "für 2024, mit Lernkurve nach unten.\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 423 €/kW — liest den ISE-Untergrenze-Lernpfad "
            "  (BNEF-NZS-Median, aggressive Skaleneffekte).\n"
            "- **Neutral / WEITER-SO** 510 €/kW — ISE-Mittel-Lernkurve.\n"
            "- **Atom- / Bestand-Lager** 700 €/kW — argumentiert höhere "
            "  CAPEX mit Backup-Aufwand und Cannibalization-Risiko "
            "  (Hirth-2013).\n\n"
            "*Quellen:* ISE-2024 (primär), BNEF-2025-LCOE, HIRTH-2013."
        ),
        tooltip_en=(
            "Specific CAPEX for new utility-scale PV in Germany. ISE-2024 "
            "reports a 2024 range of 530–1,600 €/kW with a downward learning "
            "curve.\n\n"
            "Camp spread:\n"
            "- **EE camp** 423 €/kW — reads the ISE lower-bound learning "
            "  path (BNEF-NZS median, aggressive scale effects).\n"
            "- **Neutral / WEITER-SO** 510 €/kW — ISE mid learning curve.\n"
            "- **Nuclear / existing-fleet camp** 700 €/kW — argues higher "
            "  CAPEX citing backup burden and cannibalisation risk "
            "  (Hirth-2013).\n\n"
            "*Sources:* ISE-2024 (primary), BNEF-2025-LCOE, HIRTH-2013."
        ),
        source_tag="ISE-2024",
    ),
    "wind_onshore.capex_eur_kw": SliderSpec(
        lo=1050.0,
        hi=1750.0,
        step=50.0,
        fmt="%.0f",
        label_de="Wind-Onshore-CAPEX (€/kW)",
        label_en="Wind onshore CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "Spezifische Investitionskosten neu errichteter Wind-Onshore-"
            "Anlagen in Deutschland. ISE-2024 nennt 1.300–1.900 €/kW; das "
            "Modell rechnet ohne Lernkurve (ISE sieht keine signifikanten "
            "CAPEX-Reduktionen bis 2045).\n\n"
            "Lager-übergreifend identisch: alle vier Lager teilen den "
            "Default 1.400 €/kW. Die Lager-Streitung läuft hier über WACC "
            "und Realisierungsgrad, nicht über CAPEX.\n\n"
            "*Quelle:* ISE-2024."
        ),
        tooltip_en=(
            "Specific CAPEX for new onshore wind in Germany. ISE-2024 "
            "reports 1,300–1,900 €/kW; the model uses no learning curve "
            "(ISE sees no significant CAPEX reductions through 2045).\n\n"
            "Identical across all four camps at the 1,400 €/kW default. "
            "Camp disagreement here flows through WACC and realisation "
            "rate, not CAPEX.\n\n"
            "*Source:* ISE-2024."
        ),
        source_tag="ISE-2024",
    ),
    "wind_offshore.capex_eur_kw": SliderSpec(
        lo=2250.0,
        hi=3750.0,
        step=50.0,
        fmt="%.0f",
        label_de="Wind-Offshore-CAPEX (€/kW)",
        label_en="Wind offshore CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "Spezifische Investitionskosten Wind-Offshore inkl. Netz"
            "anbindung. ISE-2024 nennt 2.500–4.000 €/kW; das Modell "
            "rechnet ohne Lernkurve (gleicher Grund wie Onshore).\n\n"
            "Lager-übergreifend identisch bei Default 3.000 €/kW. Offshore-"
            "Skepsis im Bestand-Lager läuft über WACC und Verfügbarkeit, "
            "nicht über CAPEX.\n\n"
            "*Quelle:* ISE-2024."
        ),
        tooltip_en=(
            "Specific CAPEX for offshore wind including grid connection. "
            "ISE-2024 reports 2,500–4,000 €/kW; the model uses no learning "
            "curve (same reasoning as onshore).\n\n"
            "Identical across camps at the 3,000 €/kW default. Offshore "
            "scepticism in the existing-fleet camp flows through WACC and "
            "availability, not CAPEX.\n\n"
            "*Source:* ISE-2024."
        ),
        source_tag="ISE-2024",
    ),
    "kkw_neubau_epr.capex_eur_kw": SliderSpec(
        lo=9000.0,
        hi=16000.0,
        step=250.0,
        fmt="%.0f",
        label_de="KKW-EPR-CAPEX (€/kW)",
        label_en="Nuclear EPR CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "EPR-Neubau-CAPEX. Die Spannweite reflektiert die Differenz "
            "zwischen Plan-CAPEX (EDF EPR2-Programm, ~9.000 €/kW) und "
            "realer FOAK-Empirie (Hinkley Point C ~16.000 €/kW nach "
            "Cost-Overruns, Flamanville analog).\n\n"
            "Lager-Spannweite:\n"
            "- **Atom-Lager** 9.000 €/kW — Plan-CAPEX der nächsten "
            "  EPR2-Generation, das KernD-Argument »FOAK-Aufschläge sind "
            "  weg«.\n"
            "- **Neutral / WEITER-SO** 14.000 €/kW — Mittel zwischen Plan "
            "  und realer Empirie.\n"
            "- **EE- / Bestand-Lager** 16.000 €/kW — folgt der NAO-Hinkley- "
            "  Audit-Empirie inkl. realer Bauzeit-Verlängerungen.\n\n"
            "*Quellen:* EDF-HPC, COURDESCOMPTES-FLAM, NAO-HPC-2017, KERND-2024."
        ),
        tooltip_en=(
            "EPR new-build CAPEX. The spread reflects the gap between "
            "plan CAPEX (EDF EPR2 programme, ~9,000 €/kW) and realised "
            "FOAK empirics (Hinkley Point C ~16,000 €/kW after cost "
            "overruns, Flamanville similar).\n\n"
            "Camp spread:\n"
            "- **Nuclear camp** 9,000 €/kW — plan CAPEX of the next EPR2 "
            "  generation, the KernD argument that 'FOAK premia are gone'.\n"
            "- **Neutral / WEITER-SO** 14,000 €/kW — midpoint between "
            "  plan and realised empirics.\n"
            "- **EE / existing-fleet camp** 16,000 €/kW — follows the NAO "
            "  Hinkley audit empirics including realised build-time "
            "  extensions.\n\n"
            "*Sources:* EDF-HPC, COURDESCOMPTES-FLAM, NAO-HPC-2017, KERND-2024."
        ),
        source_tag="EDF-HPC",
    ),
    "kkw_neubau_smr.capex_eur_kw": SliderSpec(
        lo=6000.0,
        hi=14000.0,
        step=250.0,
        fmt="%.0f",
        label_de="KKW-SMR-CAPEX (€/kW)",
        label_en="Nuclear SMR CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "SMR-Neubau-CAPEX (BWRX-300, NuScale-VOYGR, RR-SMR-Klassen). "
            "Empirie ist dünn (keine SMR-Inbetriebnahme in Europa), die "
            "Spannweite spiegelt vor allem Modul-Skalierungs-Annahmen.\n\n"
            "Lager-Spannweite:\n"
            "- **Atom-Lager** 6.000 €/kW — Modul-Lernkurven-Optimismus "
            "  (KernD-Position).\n"
            "- **Neutral / WEITER-SO** 11.500 €/kW — Mittel-Schätzung "
            "  ohne realisierte Referenzanlage.\n"
            "- **EE- / Bestand-Lager** 14.000 €/kW — Empirie-Skepsis "
            "  analog zur EPR-FOAK-Erfahrung.\n\n"
            "*Quellen:* ISE-2024, KERND-2024."
        ),
        tooltip_en=(
            "SMR new-build CAPEX (BWRX-300, NuScale VOYGR, RR-SMR class). "
            "Empirics are thin (no SMR commissioned in Europe yet); the "
            "spread mostly reflects module-scaling assumptions.\n\n"
            "Camp spread:\n"
            "- **Nuclear camp** 6,000 €/kW — module-learning optimism "
            "  (the KernD position).\n"
            "- **Neutral / WEITER-SO** 11,500 €/kW — mid estimate absent "
            "  a realised reference plant.\n"
            "- **EE / existing-fleet camp** 14,000 €/kW — empirics-based "
            "  scepticism analogous to EPR FOAK experience.\n\n"
            "*Sources:* ISE-2024, KERND-2024."
        ),
        source_tag="ISE-2024",
    ),
    "gas_h2ready.capex_eur_kw": SliderSpec(
        lo=825.0,
        hi=1375.0,
        step=25.0,
        fmt="%.0f",
        label_de="Gas-H2-Ready-CAPEX (€/kW)",
        label_en="Gas (H₂-ready) CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "CAPEX H₂-ready-Gasturbinen-Neubau für Backup-Erzeugung — "
            "konventionelle CCGT plus H₂-Umrüstoption.\n\n"
            "Lager-übergreifend identisch bei Default 1.100 €/kW. Die "
            "Lager-Streitung läuft hier über die H₂-Verfügbarkeit "
            "(Brennstoff-Preis) und die WACC der Backup-Investition, "
            "nicht über CAPEX.\n\n"
            "*Quelle:* EWI-2024, VDE-2023 (h2_gas_turbine_capex 1.100)."
        ),
        tooltip_en=(
            "CAPEX for new H₂-ready gas turbines used for backup "
            "generation — conventional CCGT plus H₂ retrofit option.\n\n"
            "Identical across camps at the 1,100 €/kW default. Camp "
            "disagreement here runs through H₂ availability (fuel price) "
            "and the WACC of the backup investment, not through CAPEX.\n\n"
            "*Sources:* EWI-2024, VDE-2023 (h2_gas_turbine_capex 1,100)."
        ),
        source_tag="EWI-2024",
    ),
    "battery.capex_eur_kw": SliderSpec(
        lo=125.0,
        hi=207.0,
        step=5.0,
        fmt="%.0f",
        label_de="Batterie-CAPEX (€/kW)",
        label_en="Battery CAPEX (€/kW)",
        group="capex",
        tooltip_de=(
            "Spezifische Investitionskosten 4-h-Li-Ion-Batteriespeicher. "
            "BNEF-2025-LIB dokumentiert eine starke Lernkurve nach unten "
            "(2024: 108 $/kWh-Pack-Preise).\n\n"
            "Lager-übergreifend identisch bei Default ~166 €/kW (aus "
            "Inventory-Lernkurve gerechnet). Lager-Differenzen laufen "
            "hier über WACC und Wirkungsgrad-Annahmen, nicht über CAPEX.\n\n"
            "*Quellen:* BNEF-2025-LIB, BNEF-2025-ESS."
        ),
        tooltip_en=(
            "Specific CAPEX for 4-hour Li-Ion battery storage. BNEF-2025-LIB "
            "documents a steep downward learning curve (2024 pack prices "
            "at 108 $/kWh).\n\n"
            "Identical across camps at the ~166 €/kW default (computed "
            "from the inventory learning curve). Camp differences here "
            "flow through WACC and efficiency assumptions, not CAPEX.\n\n"
            "*Sources:* BNEF-2025-LIB, BNEF-2025-ESS."
        ),
        source_tag="BNEF-2025-LIB",
    ),
    # --- WACC levers (expander) ----------------------------------------
    "pv.wacc_pct": SliderSpec(
        lo=0.038,
        hi=0.065,
        step=0.005,
        fmt="%.3f",
        label_de="PV-WACC",
        label_en="PV WACC",
        group="wacc",
        tooltip_de=(
            "Kapitalkostensatz PV-Neubau (real, nach Steuer). Niedrig im "
            "EE-System wegen reifer Lieferketten und etabliertem PPA-Markt; "
            "höher in skeptischen Lagern wegen Cannibalization-Risiko.\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 3.8 % — IRENA-2024-Untergrenze, reifer Markt.\n"
            "- **Neutral / WEITER-SO** 4.5 % — Mittelwert.\n"
            "- **Atom- / Bestand-Lager** 6.5 % — argumentieren Markt-Risiko "
            "  durch sinkende Markt-Werte bei hohen EE-Anteilen.\n\n"
            "*Quellen:* CALIBRATED:IRENA-2024-WACC (primär), HIRTH-2013."
        ),
        tooltip_en=(
            "Cost of capital for new PV (real, after tax). Low in an EE "
            "system thanks to mature supply chains and an established PPA "
            "market; higher in sceptical camps citing cannibalisation risk.\n\n"
            "Camp spread:\n"
            "- **EE camp** 3.8 % — IRENA-2024 lower bound, mature market.\n"
            "- **Neutral / WEITER-SO** 4.5 % — midpoint.\n"
            "- **Nuclear / existing-fleet camps** 6.5 % — argue market risk "
            "  from falling market values at high renewables shares.\n\n"
            "*Sources:* CALIBRATED:IRENA-2024-WACC (primary), HIRTH-2013."
        ),
        source_tag="CALIBRATED:IRENA-2024-WACC",
    ),
    "wind_onshore.wacc_pct": SliderSpec(
        lo=0.045,
        hi=0.075,
        step=0.005,
        fmt="%.3f",
        label_de="Wind-Onshore-WACC",
        label_en="Wind onshore WACC",
        group="wacc",
        tooltip_de=(
            "Kapitalkostensatz Wind-Onshore-Neubau (real, nach Steuer). "
            "Höher als PV wegen Genehmigungsrisiko (DE) und längerer Bau- "
            "und Erprobungszeit.\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 4.5 % — entspannte Genehmigungspraxis, BImSchG-"
            "  Reform wirksam.\n"
            "- **Neutral / WEITER-SO** 6.0 % — Mittelwert.\n"
            "- **Atom- / Bestand-Lager** 7.5 % — fortbestehendes "
            "  Genehmigungs- und Akzeptanz-Risiko.\n\n"
            "*Quellen:* CALIBRATED:IRENA-2024-WACC (primär)."
        ),
        tooltip_en=(
            "Cost of capital for new onshore wind (real, after tax). Higher "
            "than PV because of permitting risk (Germany) and longer build "
            "and commissioning time.\n\n"
            "Camp spread:\n"
            "- **EE camp** 4.5 % — relaxed permitting practice, BImSchG "
            "  reform effective.\n"
            "- **Neutral / WEITER-SO** 6.0 % — midpoint.\n"
            "- **Nuclear / existing-fleet camps** 7.5 % — persistent "
            "  permitting and acceptance risk.\n\n"
            "*Source:* CALIBRATED:IRENA-2024-WACC (primary)."
        ),
        source_tag="CALIBRATED:IRENA-2024-WACC",
    ),
    "kkw_neubau_epr.wacc_pct": SliderSpec(
        lo=0.070,
        hi=0.100,
        step=0.005,
        fmt="%.3f",
        label_de="KKW-EPR-WACC",
        label_en="Nuclear EPR WACC",
        group="wacc",
        tooltip_de=(
            "Kapitalkostensatz EPR-Neubau (real, nach Steuer). Strukturell "
            "höher als EE wegen Bauzeit-Risiko (Hinkley empirisch ~8.5 %, "
            "Flamanville analog) und Kapital-Bindung über mehrere Dekaden "
            "vor Erlös.\n\n"
            "Lager-Spannweite:\n"
            "- **Atom-Lager** 7.0 % — argumentiert staatlich abgesicherte "
            "  WACC (CfD/RAB-Modell wie UK Sizewell), entwickelter "
            "  Lieferketten-Effekt.\n"
            "- **Neutral / WEITER-SO** 9.0 % — Hinkley-empirischer Mittelwert.\n"
            "- **EE- / Bestand-Lager** 10.0 % — folgt der vollen Cost-of-"
            "  Capital-Empirie unter realistischem Bauzeit-Risiko.\n\n"
            "*Quellen:* EDF-HPC (primär), NAO-HPC-2017, CALIBRATED:HPC-"
            "Helm-Oxford+Sizewell-RAB."
        ),
        tooltip_en=(
            "Cost of capital for EPR new-build (real, after tax). "
            "Structurally higher than RE because of build-time risk "
            "(Hinkley empirically ~8.5 %, Flamanville similar) and "
            "capital tied up for decades before revenue.\n\n"
            "Camp spread:\n"
            "- **Nuclear camp** 7.0 % — argues state-backed WACC "
            "  (CfD/RAB model like UK Sizewell), supply-chain effect.\n"
            "- **Neutral / WEITER-SO** 9.0 % — Hinkley-empirical mid.\n"
            "- **EE / existing-fleet camps** 10.0 % — follows the full "
            "  cost-of-capital empirics under realistic build-time risk.\n\n"
            "*Sources:* EDF-HPC (primary), NAO-HPC-2017, CALIBRATED:HPC-"
            "Helm-Oxford+Sizewell-RAB."
        ),
        source_tag="EDF-HPC",
    ),
    "kkw_neubau_smr.wacc_pct": SliderSpec(
        lo=0.070,
        hi=0.100,
        step=0.005,
        fmt="%.3f",
        label_de="KKW-SMR-WACC",
        label_en="Nuclear SMR WACC",
        group="wacc",
        tooltip_de=(
            "Kapitalkostensatz SMR-Neubau (real, nach Steuer). Modell "
            "übernimmt die EPR-Range, weil keine realisierte SMR-Empirie "
            "in Europa existiert.\n\n"
            "Lager-Spannweite:\n"
            "- **Atom-Lager** 7.0 % — Modul-Lernkurve senkt Bauzeit-Risiko.\n"
            "- **Neutral / WEITER-SO** 9.0 % — analog EPR.\n"
            "- **EE- / Bestand-Lager** 10.0 % — FOAK-Premium auf "
            "  unerprobte Technologie.\n\n"
            "*Quellen:* EDF-HPC (primär), KERND-2024."
        ),
        tooltip_en=(
            "Cost of capital for SMR new-build (real, after tax). The "
            "model adopts the EPR range because no realised SMR empirics "
            "exist in Europe yet.\n\n"
            "Camp spread:\n"
            "- **Nuclear camp** 7.0 % — module learning reduces build-time risk.\n"
            "- **Neutral / WEITER-SO** 9.0 % — analogous to EPR.\n"
            "- **EE / existing-fleet camps** 10.0 % — FOAK premium on "
            "  untested technology.\n\n"
            "*Sources:* EDF-HPC (primary), KERND-2024."
        ),
        source_tag="EDF-HPC",
    ),
    "gas_h2ready.wacc_pct": SliderSpec(
        lo=0.065,
        hi=0.085,
        step=0.005,
        fmt="%.3f",
        label_de="Gas-H2-Ready-WACC",
        label_en="Gas (H₂-ready) WACC",
        group="wacc",
        tooltip_de=(
            "Kapitalkostensatz H₂-ready-Gasturbinen-Neubau (real, nach "
            "Steuer). Strukturelles Risiko: niedrige Volllaststunden "
            "(Backup-Rolle) plus H₂-Verfügbarkeits-Unsicherheit.\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 6.5 % — Backup im EE-System hat klare Rolle.\n"
            "- **Neutral / WEITER-SO** 7.5 % — Mittelwert.\n"
            "- **Atom- / Bestand-Lager** 8.5 % — argumentieren H₂-Risiko "
            "  und unklaren Auslastungs-Pfad.\n\n"
            "*Quellen:* BNEF-2025-LCOE (primär)."
        ),
        tooltip_en=(
            "Cost of capital for new H₂-ready gas turbines (real, after "
            "tax). Structural risk: low full-load hours (backup role) "
            "combined with H₂-availability uncertainty.\n\n"
            "Camp spread:\n"
            "- **EE camp** 6.5 % — backup in an EE system has a clear role.\n"
            "- **Neutral / WEITER-SO** 7.5 % — midpoint.\n"
            "- **Nuclear / existing-fleet camps** 8.5 % — argue H₂ risk "
            "  and an unclear utilisation path.\n\n"
            "*Source:* BNEF-2025-LCOE (primary)."
        ),
        source_tag="BNEF-2025-LCOE",
    ),
    "battery.wacc_pct": SliderSpec(
        lo=0.060,
        hi=0.085,
        step=0.005,
        fmt="%.3f",
        label_de="Batterie-WACC",
        label_en="Battery WACC",
        group="wacc",
        tooltip_de=(
            "Kapitalkostensatz Batteriespeicher (real, nach Steuer). "
            "Steiler Markt-Hochlauf, dadurch sinkende Risikoprämie über "
            "die Zeit.\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 6.0 % — Tagesausgleich ist Kerngeschäft im "
            "  EE-System.\n"
            "- **Neutral / WEITER-SO** 7.0 % — Mittelwert.\n"
            "- **Atom- / Bestand-Lager** 8.5 % — argumentieren Marktrisiko "
            "  bei Arbitrage-Erlösen.\n\n"
            "*Quellen:* BNEF-2025-LIB (primär), BNEF-2025-ESS."
        ),
        tooltip_en=(
            "Cost of capital for battery storage (real, after tax). Steep "
            "market ramp-up, which reduces the risk premium over time.\n\n"
            "Camp spread:\n"
            "- **EE camp** 6.0 % — daily balancing is core business in an "
            "  EE system.\n"
            "- **Neutral / WEITER-SO** 7.0 % — midpoint.\n"
            "- **Nuclear / existing-fleet camps** 8.5 % — argue market "
            "  risk on arbitrage revenues.\n\n"
            "*Sources:* BNEF-2025-LIB (primary), BNEF-2025-ESS."
        ),
        source_tag="BNEF-2025-LIB",
    ),
    # --- Fuel-price levers (expander) ----------------------------------
    "erdgas_inland.preis_eur_mwh": SliderSpec(
        lo=25.0,
        hi=50.0,
        step=1.0,
        fmt="%.0f",
        label_de="Erdgas-Preis (€/MWh)",
        label_en="Natural gas price (€/MWh)",
        group="fuel",
        tooltip_de=(
            "Grenzübergangspreis Erdgas-Inland Deutschland. Wirkt direkt "
            "auf den Brücken-Pfad von WEITER-SO/BESTAND und auf die "
            "Backup-Kosten in EE-GAS.\n\n"
            "Lager-Spannweite (EU-Kommissions-Szenarien):\n"
            "- **Atom-Lager** 25 €/MWh — argumentiert günstige LNG-Importe "
            "  und globalen Gasüberschuss.\n"
            "- **Bestand-Lager** 30 €/MWh — etwas vorsichtiger.\n"
            "- **Neutral / WEITER-SO** 35 €/MWh — Mittelwert der Szenarien.\n"
            "- **EE-Lager** 50 €/MWh — argumentiert geopolitische Risiken "
            "  und ETS-2-Aufschlag.\n\n"
            "*Quellen:* EUKOM-2024 (primär)."
        ),
        tooltip_en=(
            "Border-crossing price for natural gas delivered to Germany. "
            "Acts directly on the bridge phase of WEITER-SO/BESTAND and "
            "on backup costs in EE-GAS.\n\n"
            "Camp spread (EU Commission scenarios):\n"
            "- **Nuclear camp** 25 €/MWh — argues cheap LNG imports and "
            "  global gas surplus.\n"
            "- **Existing-fleet camp** 30 €/MWh — slightly more cautious.\n"
            "- **Neutral / WEITER-SO** 35 €/MWh — midpoint of scenarios.\n"
            "- **EE camp** 50 €/MWh — argues geopolitical risk and an "
            "  ETS-2 mark-up.\n\n"
            "*Source:* EUKOM-2024 (primary)."
        ),
        source_tag="EUKOM-2024",
    ),
    "h2_inland.preis_eur_mwh": SliderSpec(
        lo=80.0,
        hi=130.0,
        step=2.0,
        fmt="%.0f",
        label_de="H₂-Inland-Preis (€/MWh)",
        label_en="Domestic H₂ price (€/MWh)",
        group="fuel",
        tooltip_de=(
            "H₂-Gestehungspreis aus inländischer Elektrolyse, Endverbraucher-"
            "Preis (€/MWh-LHV). Henne-Ei-Risiko: niedrige Auslastung treibt "
            "Kosten, niedrige Kosten brauchen hohe Auslastung.\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 80 €/MWh — billiger H₂ aus EE-Überschüssen, "
            "  steile Lernkurve Elektrolyse.\n"
            "- **Neutral / WEITER-SO** 100 €/MWh — Mittelwert.\n"
            "- **Atom- / Bestand-Lager** 130 €/MWh — argumentieren H₂-"
            "  Knappheit und langsame Hochlauf-Dynamik.\n\n"
            "*Quellen:* EWI-2024 (primär), CLOETE-HIRTH-H2-2021."
        ),
        tooltip_en=(
            "Cost of H₂ produced from domestic electrolysis, end-consumer "
            "price (€/MWh-LHV). Chicken-and-egg risk: low utilisation "
            "drives cost, low cost requires high utilisation.\n\n"
            "Camp spread:\n"
            "- **EE camp** 80 €/MWh — cheap H₂ from RE surplus, steep "
            "  electrolyser learning curve.\n"
            "- **Neutral / WEITER-SO** 100 €/MWh — midpoint.\n"
            "- **Nuclear / existing-fleet camps** 130 €/MWh — argue H₂ "
            "  scarcity and a slow ramp-up dynamic.\n\n"
            "*Sources:* EWI-2024 (primary), CLOETE-HIRTH-H2-2021."
        ),
        source_tag="EWI-2024",
    ),
    "h2_import.preis_eur_mwh": SliderSpec(
        lo=90.0,
        hi=150.0,
        step=2.0,
        fmt="%.0f",
        label_de="H₂-Import-Preis (€/MWh)",
        label_en="Imported H₂ price (€/MWh)",
        group="fuel",
        tooltip_de=(
            "H₂-Importpreis frei deutsche Grenze (Schiff oder Pipeline), "
            "€/MWh-LHV. Strukturell teurer als Inland-H₂ wegen Transport- "
            "und Konversions-Verlusten (Ammoniak ↔ H₂).\n\n"
            "Lager-Spannweite:\n"
            "- **EE-Lager** 90 €/MWh — globaler H₂-Markt skaliert, "
            "  niedrige Stromkosten in Exportländern.\n"
            "- **Neutral / WEITER-SO** 120 €/MWh — Mittelwert.\n"
            "- **Atom- / Bestand-Lager** 150 €/MWh — argumentieren "
            "  Transport-Aufwand und politische Lieferunsicherheit.\n\n"
            "*Quellen:* EWI-2024 (primär), CLOETE-HIRTH-H2-2021."
        ),
        tooltip_en=(
            "Imported H₂ price delivered to the German border (shipping "
            "or pipeline), €/MWh-LHV. Structurally more expensive than "
            "domestic H₂ due to transport and conversion losses "
            "(ammonia ↔ H₂).\n\n"
            "Camp spread:\n"
            "- **EE camp** 90 €/MWh — global H₂ market scales, low "
            "  power costs in exporting countries.\n"
            "- **Neutral / WEITER-SO** 120 €/MWh — midpoint.\n"
            "- **Nuclear / existing-fleet camps** 150 €/MWh — argue "
            "  transport overhead and political supply uncertainty.\n\n"
            "*Sources:* EWI-2024 (primary), CLOETE-HIRTH-H2-2021."
        ),
        source_tag="EWI-2024",
    ),
}


GROUP_LABELS_DE: dict[str, str] = {
    "top": "🎯 Top-Hebel",
    "capex": "💰 CAPEX (€/kW)",
    "wacc": "📈 WACC (%)",
    "fuel": "⛽ Brennstoff-Preise (€/MWh)",
}


GROUP_LABELS_EN: dict[str, str] = {
    "top": "🎯 Top levers",
    "capex": "💰 CAPEX (€/kW)",
    "wacc": "📈 WACC (%)",
    "fuel": "⛽ Fuel prices (€/MWh)",
}


def _camp_realization_default(param: str, camp: str) -> float:
    """Read a realisation-rate world-belief from ``CAMP_RANGES``.

    The ``CAMP_RANGES`` dict has heterogeneous value types per parameter
    (numeric camp keys + string ``source_tag`` / ``verteilung`` /
    ``label`` keys), so the raw ``dict.get(...)`` return is typed
    ``object``. This helper narrows the lookup to a float with a safe
    fallback for unknown camps.
    """
    from enesys.core.camp_ranges import CAMP_RANGES

    raw = CAMP_RANGES[param].get(camp)
    if isinstance(raw, (int, float)):
        return float(raw)
    return 1.0


def get_camp_defaults(camp: str) -> dict[str, float]:
    """Return the default slider values for a camp.

    Used to initialise sliders on camp switch and as the reference
    against which a slider value becomes an "override". Values are
    pulled from the live ``TECH_INVENTORY`` / ``FUEL_INVENTORY`` so
    inventory edits propagate automatically.
    """
    from enesys.core.inventories import FUEL_INVENTORY, TECH_INVENTORY
    from enesys.core.path_model import _co2_price_year

    defaults: dict[str, float] = {}
    # Realisation-rate levers: pull the camp's own world-belief from
    # CAMP_RANGES so the slider reflects the active camp instead of
    # silently sitting at a fixed 1.0. Slider movement still acts as an
    # override against compute_path; the visible default just tracks
    # which camp is selected.
    defaults["nep_realization_rate"] = _camp_realization_default("nep_realization_rate", camp)
    defaults["nuclear_realization_rate"] = _camp_realization_default(
        "nuclear_realization_rate", camp
    )
    defaults["co2_price_eur_t"] = _co2_price_year(2045, camp)

    for key, spec in SLIDER_SPEC.items():
        if "." not in key:
            continue
        target, field = key.split(".", 1)
        if target in TECH_INVENTORY:
            tech = TECH_INVENTORY[target]
            attr = getattr(tech, field)
            defaults[key] = attr(2045, camp) if callable(attr) else attr
        elif target in FUEL_INVENTORY:
            fuel = FUEL_INVENTORY[target]
            defaults[key] = fuel.price_eur_mwh(2045, camp)
        else:
            # No matching inventory entry — fall back to the slider midpoint
            # so the UI still renders. The override produced by this slider
            # will not affect the model output.
            defaults[key] = (spec.lo + spec.hi) / 2.0
    return defaults


def _widen_specs_to_cover_camps() -> None:
    """Widen each slider's ``[lo, hi]`` so it always contains every camp default.

    The hand-set ranges in :data:`SLIDER_SPEC` define the intended
    *exploration* window and are deliberately wider than the camps for
    some levers (e.g. ``nep_realization_rate`` reaches 1.00 = full plan
    fulfilment, which no camp assumes). But a camp default must never
    fall *outside* its slider, or selecting that camp makes the bound
    widget raise ``StreamlitValueBelow/AboveMinError`` at render time.

    We take the *union* of the hand-set window and the camp envelope —
    the range is only ever widened, never narrowed — so the exploration
    headroom is preserved while every camp stays representable. The
    ``range ⊇ camp envelope`` invariant is pinned by
    ``tests/consistency/test_slider_camp_ranges.py``.
    """
    camp_defaults = [get_camp_defaults(camp[0]) for camp in LAGER_OPTIONS]
    for key, spec in list(SLIDER_SPEC.items()):
        vals = [d[key] for d in camp_defaults if key in d]
        if not vals:
            continue
        lo, hi = min(spec.lo, *vals), max(spec.hi, *vals)
        if lo != spec.lo or hi != spec.hi:
            SLIDER_SPEC[key] = replace(spec, lo=lo, hi=hi)


_widen_specs_to_cover_camps()


def build_overrides_from_sliders(
    slider_values: dict[str, float],
    camp: str,
) -> dict[str, float]:
    """Build a ``param_overrides`` dict for ``compute_path``.

    Compares each slider value with the camp default and emits only
    those that deviate (tolerance ``1e-3``). This lets the user switch
    camps while preserving the per-slider override semantics: a slider
    that matches the new camp default disappears from the overrides.
    """
    defaults = get_camp_defaults(camp)
    overrides: dict[str, float] = {}
    for key, value in slider_values.items():
        if key not in defaults:
            continue
        default = defaults[key]
        if abs(value - default) > max(abs(default) * 1e-3, 1e-6):
            overrides[key] = value
    return overrides


def slider_groups() -> dict[str, list[str]]:
    """Return slider keys grouped by their expander group."""
    groups: dict[str, list[str]] = {"top": [], "capex": [], "wacc": [], "fuel": []}
    for key, spec in SLIDER_SPEC.items():
        groups[spec.group].append(key)
    return groups


# Pfad-Label-Mapping: book-style label → path id (used by the Sources page
# to back-reference levers to paths).
BOOK_LABEL_TO_PATH_ID: dict[str, str] = {
    "WEITER-SO": "weiterso",
    "BESTAND": "bestand",
    "EE-GAS": "ee_gas",
    "EE-H2": "ee_h2",
    "KKW-GAS": "kkw_gas",
    "KKW-H2": "kkw_h2",
}


__all__ = [
    "BOOK_LABEL_TO_PATH_ID",
    "GROUP_LABELS_DE",
    "GROUP_LABELS_EN",
    "LAGER_OPTIONS",
    "SLIDER_SPEC",
    "SliderSpec",
    "build_overrides_from_sliders",
    "get_camp_defaults",
    "slider_groups",
]
