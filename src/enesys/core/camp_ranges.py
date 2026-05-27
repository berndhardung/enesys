"""
enesys — Lager-Bandbreiten für Sensitivitätsanalysen

Reine Datenstruktur-Datei: zentrale Tabelle der Bandbreiten zwischen
EE-Lager- und Atom-Lager-Position für die Schlüsselparameter.

- ``LAGER_RANGES``: Single Source für die Lager-Schlüssel-Konvention
  (``ee_optimistic`` / ``neutral_default`` / ``atom_optimistic`` /
  ``bestand_optimistic`` / ``weiterso_optimistic``). Wird von
  Mengen-Bilanz-Schicht, Tornado-/Sensitivitäts-Auswertung, UI-Bridge
  und Inventars als gemeinsame Quelle konsumiert.

- ``lager_range()``: Helper, der für einen Parameter die Tupel-Range
  ``(low, high)`` liefert.

Bewusst getrennt vom UI: Diese Datei kennt kein Streamlit.

Konvention:
    - Alle Kosten in Euro-Cent pro kWh (ct/kWh), wenn nicht anders vermerkt
    - Alle Kapazitäten in GW
    - Alle Energiemengen in TWh
    - Alle Emissionen in g CO2/kWh oder Mt CO2/a
"""

# ---------------------------------------------------------------------------
# Lager-Bandbreiten — zentrale Quelle für Sensitivitäts- und Robustheitsanalysen
# ---------------------------------------------------------------------------
#
# Statt ad-hoc-Bandbreiten (±25 %) verwenden Tornado- und Monte-Carlo-Analysen
# realistische Lager-Positionen, die aus SOURCES.md belegt sind.
#
# Jeder Eintrag definiert die Spannweite zwischen dem optimistischsten Wert,
# den ein Lager realistisch verteidigt, und dem pessimistischsten Wert, den
# das Gegenlager als Erwartung anführt. Die Bandbreite zwischen diesen
# beiden Werten ist die methodisch verteidigbare Sensitivitäts-Range.
#
# Konvention:
#   ee_optimistic        = Wert, den das EE-Lager als realistisch ansieht
#   atom_optimistic      = Wert, den das Atom-Lager als realistisch ansieht
#   bestand_optimistic   = Wert, den das Bestand-Lager (aktive Fossil-
#                          Stabilisierung) als realistisch ansieht
#   weiterso_optimistic  = Wert, den die WEITER-SO-Position (passive
#                          Trägheit, »Markt regelt das«) als realistisch
#                          ansieht. Welt-Belief-Parameter (Kat 2)
#                          markt-getrieben → meist Kopie von neutral_default;
#                          Politik-Parameter (Kat 1) mit eigenen passiv-
#                          trägen Werten.
#   neutral_default      = Mittelwert / Konsens-Schätzung / Empirisch-Mittel
#
# Für Pro-EE-Parameter (z.B. PV-LCOE) ist ee_optimistic der niedrigere Wert.
# Für Pro-Atom-Parameter (z.B. nuclear_lcoe) ist atom_optimistic der niedrigere.
# ---------------------------------------------------------------------------

CAMP_RANGES = {
    # --- Erzeugungskosten (ct/kWh) ----------------------------------------
    # bestand_optimistic ist der vierte Lager-Wert für die Bestands-Lager-
    # Position. Wo BESTAND keine differenzierte Position hat (z.B. KKW-
    # Parameter — BESTAND fährt 0 % Atom), wird der Atom-Lager-Wert
    # übernommen, weil die Bestand-Position dem Atom-Lager in seiner
    # Skepsis gegenüber EE-Hochlauf und H2 ähnelt.
    #
    # weiterso_optimistic ist der fünfte Lager-Wert für die WEITER-SO-
    # Position (passive Trägheit). Welt-Belief-Parameter markt-getrieben
    # → meist Kopie von neutral_default.
    "pv_lcoe": {
        "neutral_default": 6.0,
        "ee_optimistic": 4.5,  # ISE-2024 Untergrenze
        "atom_optimistic": 8.0,  # KernD argumentiert höhere Werte wegen Backup
        "bestand_optimistic": 6.5,  # zwischen neutral und atom — Bestands-Lager-EE-Skepsis  [SRC: BDI-2024]
        "weiterso_optimistic": 6.0,  # markt-getrieben, Mittel-Schätzung
        "source_tag": "ISE-2024",
        "verteilung": "normal",
        "label": "PV-LCOE",
    },
    "wind_onshore_lcoe": {
        "neutral_default": 6.5,
        "ee_optimistic": 5.0,  # guter Standort, neue WEA-Generation
        "atom_optimistic": 8.5,  # ISE-Obergrenze + DE-Genehmigungspraxis
        "bestand_optimistic": 7.5,  # gedämpfter Onshore-Ausbau, BDI-Position  [SRC: BDI-2024]
        "weiterso_optimistic": 6.5,  # markt-getrieben
        "source_tag": "ISE-2024",
        "verteilung": "normal",
        "label": "Wind onshore",
    },
    "wind_offshore_lcoe": {
        "neutral_default": 9.0,
        "ee_optimistic": 7.5,  # neue große Turbinen
        "atom_optimistic": 11.0,  # inkl. Netzanbindung, BNEF-2025-Anstieg
        "bestand_optimistic": 10.0,  # Bestands-Lager-Position zur Offshore-Skepsis  [SRC: BDI-2024]
        "weiterso_optimistic": 9.0,  # markt-getrieben
        "source_tag": "ISE-2024",
        "verteilung": "normal",
        "label": "Wind offshore",
    },
    "nuclear_lcoe": {
        "neutral_default": 14.0,
        "ee_optimistic": 18.0,  # reale Hinkley/Flamanville-Erfahrung
        "atom_optimistic": 9.0,  # Plan-LCOE neuer EPR-Generation
        # BESTAND fährt 0 % Atom (kkw_neubau_*: forbidden) — Wert
        # praktisch nur für Tornado-Lager-Sweeps relevant. Platzhalter =
        # neutral_default, weil BESTAND keine KKW-Lager-Position hat:
        # weder Optimismus zur Plan-LCOE (atom_optimistic) noch
        # Skepsis aus realer Erfahrung (ee_optimistic) ist BESTANDs
        # Argument.
        "bestand_optimistic": 14.0,
        "weiterso_optimistic": 14.0,  # WEITER-SO baut keinen Neubau, Platzhalter = neutral
        "source_tag": "EDF-HPC, COURDESCOMPTES-FLAM",
        "verteilung": "lognormal",  # asymmetrisch, weil Kostenüberläufe häufiger
        "label": "Kernkraft-LCOE",
    },
    "nuclear_full_load_hours": {
        "neutral_default": 6500,
        "ee_optimistic": 5500,  # 80%-EE-System drosselt KKW
        "atom_optimistic": 7800,  # KKW als Grundlast-privilegiert
        "bestand_optimistic": 6500,  # Platzhalter = neutral (BESTAND kein KKW; keine Lager-Position)
        "weiterso_optimistic": 6500,  # Platzhalter = neutral (WEITER-SO kein Neubau)
        "source_tag": "ISE-2024, RUHNAU-2021",
        "verteilung": "normal",
        "label": "KKW-Volllaststunden",
    },
    "h2_storage_lcoe": {
        "neutral_default": 32.0,
        "ee_optimistic": 25.0,  # billiger H2 aus Importen
        "atom_optimistic": 50.0,  # H2-Knappheit, Kavernenmangel
        # BESTAND-Lager-H2-Skepsis (Programm hat kein H2-ready).
        # Bestands-Lager teilt KKW-Lager-Position »H2-Hochlauf unsicher«.
        "bestand_optimistic": 45.0,  # [SRC: BDI-2024]
        "weiterso_optimistic": 32.0,  # markt-getrieben, kein Push, kein Bremse
        "source_tag": "EWI-2024",
        "verteilung": "lognormal",  # asymmetrisch, weil Henne-Ei-Risiko
        "label": "H2-Backup",
    },
    "battery_lcos": {
        "neutral_default": 7.0,
        "ee_optimistic": 5.0,  # BNEF-Lernkurve, China-Preise
        "atom_optimistic": 14.0,  # konservativ, lokale Aufschläge
        # BESTAND akzeptiert Batterien als Komplement zur Erdgas-Flotte
        # (»Tagesausgleich neben Backup«). Mittlere Annahme.
        "bestand_optimistic": 8.0,
        "weiterso_optimistic": 7.0,  # markt-getriebene Lernkurve
        "source_tag": "BNEF-2025-LIB, BNEF-2025-ESS",
        "verteilung": "lognormal",  # Lernkurve drückt nach unten
        "label": "Batterie-LCOS",
    },
    # --- System (ct/kWh) ---------------------------------------------------
    "grid_surcharge": {
        "neutral_default": 7.0,
        "ee_optimistic": 6.0,  # smarte Netzführung senkt Kosten
        "atom_optimistic": 9.0,  # konservativ, hohe Trassenkosten
        # BESTAND-Programm investiert moderat ins Netz, weniger
        # Trassenausbau als aktive Pfade (zentrale Erdgas-Flotte
        # ersetzt Smart-Grid-Bedarf teilweise).
        "bestand_optimistic": 7.5,
        "weiterso_optimistic": 7.0,  # kein NEP-Push, Status-quo-Ausbau
        "source_tag": "BNETZA-VS-2025",
        "verteilung": "normal",
        "label": "Netz",
    },
    "co2_price_eur_t": {
        "neutral_default": 120.0,
        "ee_optimistic": 150.0,  # Klimaziel-konsistente Preise
        "atom_optimistic": 80.0,  # konservativ, ETS-Schwäche
        # BESTAND-Lager-Position »EU-ETS-Trajektorie aufweichen«.
        # Sensi-Bandbreite-Untergrenze bleibt 80 als untere Sensi-Variation;
        # Hauptmodell-Default in BestandParams.co2_price_eur_t_2030 auf 120.
        "bestand_optimistic": 80.0,
        # WEITER-SO »Markt regelt das« heißt politisch: keine aktive
        # Klima-Verschärfung, EU-ETS-Korridor-Unterkante akzeptiert.
        # Selbe Lager-Position wie BESTAND (80 €/t) — beide Untätigkeits-
        # Lager teilen die ETS-Skepsis. [SRC: IFW-REAKTIV-2025]
        "weiterso_optimistic": 80.0,
        "source_tag": "EUKOM-2024 + IFW-REAKTIV-2025",
        "verteilung": "normal",
        "label": "CO2-Preis",
    },
    "nep_realization_rate": {
        # Sensi-Achse: Realisierungsgrad des NEP-Soll-Ausbaus bis 2045.
        # Forward-Cost-Hebel, kein Versorgungssicherheits-Hebel.
        #
        # ACHTUNG: Diese CAMP_RANGES-Werte sind die Welt-Belief-
        # Spannweite pro Lager (»was hält das Lager realistisch für
        # erwartbar«), getrennt von PATH_POLICY.<pfad>.default_policy.
        # nep_realization_rate (»was setzt die Politik im Pfad«). Die
        # Werte können bewusst auseinanderlaufen — z.B. fährt der
        # bestand-Pfad eine aktive Drossel auf 0,30 (PATH_POLICY), das
        # bestand_optimistic-Lager hält aber 0,45 für realistisch, weil
        # EU-Mindest-Resilienz die Politik-Drossel korrigiert. Wer beide
        # Tabellen nebeneinanderlegt, sieht scheinbar vertauschte
        # Werte zwischen bestand und weiterso — das ist Absicht, nicht
        # Bug. compute_path() liest den Pfad-Default; Tornado liest die
        # Lager-Spannweite.
        #
        # Bandbreite empirisch verteidigbar:
        #  - 0,85 (ee_optimistic): NEP-Soll fast erfüllt, BNetzA-
        #    Reformen wirken voll
        #  - 0,65 (neutral_default): empirischer Mittelwert nach
        #    EnLAG-/HGÜ-/BBPlG-Erfahrung Pre-Reform
        #  - 0,50 (atom_optimistic): KKW-Lager nutzt Trassen-
        #    Skepsis (»wir brauchen weniger Trassen, wenn KKW
        #    Grundlast trägt«)
        #  - 0,45 (bestand_optimistic): Bestand-Lager-Welt-Belief —
        #    auch unter Drossel-Politik korrigiert EU-Resilienz nach
        #    oben (nicht zu verwechseln mit PATH_POLICY.bestand=0,30
        #    Politik-Wunsch)
        #  - 0,30 (weiterso_optimistic): WEITER-SO-Position »kein
        #    Push, kein Bremse; Status-quo-Tempo« — historischer
        #    BNetzA-Mon-Wert ohne aktive Politik (nicht zu
        #    verwechseln mit PATH_POLICY.weiterso=0,45 als Politik-
        #    Default für den passive-Drift-Pfad)
        # Modell-Default Szenario A: 0,9 (»NEP-Soll erfüllt 2045«).
        # LAGER_RANGES.neutral_default: 0,65 als empirischer FOAK-Anker
        # für Sensi.
        "neutral_default": 0.65,
        "ee_optimistic": 0.85,
        "atom_optimistic": 0.50,
        "bestand_optimistic": 0.45,
        "weiterso_optimistic": 0.30,  # passive Trägheit
        "source_tag": "BNETZA-MON-Q4-2025, ENLAG-WIKI",
        "verteilung": "normal",
        "label": "NEP-Realisierungsgrad",
    },
    "wacc_nuclear": {
        # Sensi-Achse: KKW-WACC. Forward-Cost-Hebel.
        # Lager-Konvention: ee_optimistic = was das EE-Lager für plausibel
        # hält; atom_optimistic = was das Atom-Lager für plausibel hält.
        # Bandbreite politisch geprägt:
        #  - 0,100 (ee_optimistic): EE-Lager-Position »KKW teuer ohne
        #    staatliche Garantien« — Privatfinanzierung 10 % als Norm.
        #  - 0,090 (neutral_default): Hinkley Point C realisiert
        #    (Helm-Oxford), DE-realistisch ohne RAB-Modell.
        #  - 0,070 (atom_optimistic): Atom-Lager-Position »KKW billig
        #    finanzierbar mit RAB-Modell« — Sizewell-RAB als Anker.
        #  - 0,090 (bestand_optimistic): BESTAND-Lager hat keine
        #    KKW-Position — neutral_default als Platzhalter.
        #  - 0,090 (weiterso_optimistic): WEITER-SO baut keinen Neubau,
        #    Platzhalter = neutral.
        # Default 0,090. Effekt: ±1 Prozentpunkt verschiebt
        # nuclear_lcoe um ~0,8 ct/kWh.
        #
        # alle drei Werte sind real (nicht nominal). HPC-CfD ist CPI-
        # indexiert mit Equity-IRR 9,04 % auf £79,7 Mrd Real-Cashflow
        # (UK Parliament HPC0003); Sizewell-RAB 6,7 % real CPIH (UK GOV).
        "neutral_default": 0.090,
        "ee_optimistic": 0.100,
        "atom_optimistic": 0.070,
        "bestand_optimistic": 0.090,
        "weiterso_optimistic": 0.090,  # kein Neubau, Platzhalter
        "source_tag": "CALIBRATED:HPC-Helm-Oxford+Sizewell-RAB",
        "verteilung": "normal",
        "label": "WACC Kernkraft",
    },
    "profile_cost_ee_ct_kwh": {
        # H1 Profile-Cost-Aufschlag für variable EE-Pfade (ee_gas, ee_h2)
        # in ct/kWh. Erfasst die Marktwert-Asymmetrie der fluktuierenden
        # Erzeugung (Hirth/Ueckerdt/Edenhofer 2015); die Sekundär-Schicht
        # deckt Grid + Balancing, nicht Profile-Cost.
        # Lit-gestützte Bandbreite:
        #  - 0,3 (ee_optimistic): Agora-konsistent, Profile-Cost niedrig in
        #    effizientem EE-System mit DSM/Speicher-Internalisierung.
        #  - 0,7 (neutral_default): Mitte Hirth/Agora minus Sekundär-
        #    internalisierte Komponenten.
        #  - 1,0 (atom_optimistic): Lit-Untergrenze des Ueckerdt-atom-
        #    Bereichs 1,0-1,5. Korrektur um Sekundär-Internalisierung und
        #    Konvergenz mit Agora-Obergrenze.
        # KKW-Pfade laufen ihre eigene Achse (profile_cost_kkw_ct_kwh, nicht-
        # monoton, weil Lager unterschiedlich zuschreiben).
        "neutral_default": 0.7,
        "ee_optimistic": 0.3,
        "atom_optimistic": 1.0,
        "bestand_optimistic": 0.7,
        "weiterso_optimistic": 0.7,  # markt-getrieben
        "source_tag": "HIRTH-UECKERDT-2015, AGORA-2014",
        "verteilung": "normal",
        "label": "Profile-Cost EE",
    },
    "profile_cost_kkw_ct_kwh": {
        # H1 Profile-Cost-Aufschlag für KKW-Pfade (kkw_gas, kkw_h2) in
        # ct/kWh. KKW-Bandlast wirkt dem Stunden-Versatz entgegen,
        # deutlich kleinerer Effekt als EE.
        # Lager-Werte sind nicht-monoton: das EE-Lager schreibt KKW eine
        # höhere Profile-Cost zu (Grundlast-Mismatch zur EE-dominierten
        # Resterzeugung), neutral_default und atom_optimistic bleiben auf
        # Lit-Mittel-Wert.
        #  - 0,3 (ee_optimistic): EE-Lager-Perspektive »Grundlast-Mismatch
        #    in EE-dominierter Welt«.
        #  - 0,1 (neutral_default): Lit-Mittel.
        #  - 0,1 (atom_optimistic): identisch zu neutral.
        "neutral_default": 0.1,
        "ee_optimistic": 0.3,
        "atom_optimistic": 0.1,
        "bestand_optimistic": 0.1,
        "weiterso_optimistic": 0.1,
        "source_tag": "HIRTH-UECKERDT-2015",
        "verteilung": "normal",
        "label": "Profile-Cost KKW",
    },
    "profile_cost_misch_ct_kwh": {
        # H1 Profile-Cost-Aufschlag für Misch-Pfade (bestand, weiterso)
        # in ct/kWh. Liegt zwischen EE- und KKW-Werten, weil Misch-Pfade
        # teilweise variable EE enthalten.
        #  - 0,3 (ee_optimistic): EE-Lager »Misch-System effizient«.
        #  - 0,3 (neutral_default): Mitte-Schätzung.
        #  - 0,5 (atom_optimistic): konservativer Aufschlag bei Misch-Last,
        #    Lit-Mittel zwischen EE- und KKW-Aufschlag.
        "neutral_default": 0.3,
        "ee_optimistic": 0.3,
        "atom_optimistic": 0.5,
        "bestand_optimistic": 0.3,
        "weiterso_optimistic": 0.3,
        "source_tag": "HIRTH-UECKERDT-2015",
        "verteilung": "normal",
        "label": "Profile-Cost Misch",
    },
    "dsm_ee_ct_kwh": {
        # H2 DSM-Rabatt für EE-Pfade (ee_gas, ee_h2) in ct/kWh, negativ = Rabatt.
        # Lastflexibilität (Demand-Side-Management) hat in EE-Systemen
        # mit hoher Preisvolatilität höheren Grenznutzen als in Bandlast-
        # dominierten Systemen.
        # Lit-gestützte Spannweite (AGORA-DEMAND-FLEX-2024 + ARIADNE-FLEX-2024,
        # qualitativ — beide Studien stützen die EE-vs-KKW-Asymmetrie auf
        # System-Mittel-Ebene, nicht durch Punkt-Schätzung):
        #  - -0,5 (ee_optimistic / neutral_default): hoher DSM-Grenznutzen in
        #    volatilen EE-Systemen.
        #  - -0,3 (atom_optimistic / bestand_optimistic): bewusste
        #    Konstruktion (Atom-Lager-Belief »KKW verhindert DSM-Vorteil
        #    für EE nicht«); kein direktes Lit-Backing für »−0,3« als
        #    Mittelwert, sondern Symmetrisierung der EE/KKW-Achsen als
        #    Lager-Wahl.
        #  - -0,3 (weiterso_optimistic): markt-getrieben, symmetrische
        #    Annahme wie atom.
        "neutral_default": -0.5,
        "ee_optimistic": -0.5,
        "atom_optimistic": -0.3,
        "bestand_optimistic": -0.3,
        "weiterso_optimistic": -0.3,
        "source_tag": "AGORA-DEMAND-FLEX-2024 + ARIADNE-FLEX-2024",
        "verteilung": "normal",
        "label": "DSM-Rabatt EE",
    },
    "dsm_kkw_ct_kwh": {
        # H2 DSM-Rabatt für KKW-Pfade (kkw_gas, kkw_h2) in ct/kWh, negativ = Rabatt.
        # KKW-Bandlast reduziert das DSM-Potential — Preistäler werden durch
        # die Grundlast geglättet, weniger Hebel für Lastverschiebung.
        # Spannweite:
        #  - -0,15 (ee_optimistic / neutral_default): KKW-Bandlast nimmt
        #    Preistäler weg, DSM-Grenznutzen klein.
        #  - -0,3 (atom_optimistic / bestand_optimistic): symmetrische
        #    Annahme — Atom-Lager-Position »KKW verhindert DSM-Vorteil
        #    nicht«. Bewusste Konstruktion (kein Lit-Backing für KKW-
        #    spezifisches »−0,3«), spiegelt die EE-Achse symmetrisch.
        #  - -0,3 (weiterso_optimistic): markt-getrieben, symmetrische
        #    Annahme.
        "neutral_default": -0.15,
        "ee_optimistic": -0.15,
        "atom_optimistic": -0.3,
        "bestand_optimistic": -0.3,
        "weiterso_optimistic": -0.3,
        "source_tag": "AGORA-DEMAND-FLEX-2024",
        "verteilung": "normal",
        "label": "DSM-Rabatt KKW",
    },
    "dsm_misch_ct_kwh": {
        # H2 DSM-Rabatt für Misch-Pfade (bestand, weiterso) in ct/kWh.
        # Konstanter Mittelwert über alle Lager — Misch-Pfade haben keine
        # eigene DSM-Differenzierungs-Position.
        "neutral_default": -0.3,
        "ee_optimistic": -0.3,
        "atom_optimistic": -0.3,
        "bestand_optimistic": -0.3,
        "weiterso_optimistic": -0.3,
        "source_tag": "AGORA-DEMAND-FLEX-2024",
        "verteilung": "normal",
        "label": "DSM-Rabatt Misch",
    },
    # Nuclear-Provision-Summen-Lesart (gesamt = Decom + Waste pro MWh):
    #   atom_optimistic:    2,0 + 1,0 =  3,0 €/MWh  (≈ HPC-CfD-Untergrenze)
    #   neutral_default:    3,5 + 1,5 =  5,0 €/MWh  (HPC-Mid + konservativ)
    #   ee_optimistic:     10,0 + 4,0 = 14,0 €/MWh  (NEA-Obergrenze + Liability-
    #                                                Externalisierung explizit)
    # Spreizung 3-14 €/MWh = 4,7× — Lager-Dissens, nicht numerische Willkür.
    # Verteilung lognormal: Fat-Tail durch Liability-Externalisierung
    # (NDA-Reststaat-Sozialisierung als modellierte EE-Lager-Position).
    "nuclear_decom_provision_eur_mwh": {
        # KKW-Neubau Decommissioning-Rückstellung pro MWh Output (€/MWh).
        # Wirkt nur auf kkw_neubau_epr + kkw_neubau_smr (kkw_bestand
        # hat KENFO-Fonds historisch abgelegt — siehe sunk_*-Doku-Felder).
        # HPC-CfD-Bandbreite + NEA-Cross-Validation:
        #  - 2,0 (atom_optimistic): HPC-Untergrenze £1/MWh ≈ €2/MWh —
        #    Atom-Lager-Position »Decom-Risiken eng kalkulierbar,
        #    Funded Decommissioning Programme deckt Rückbau«.
        #  - 3,5 (neutral_default): HPC-Mid-Range £2/MWh ≈ €2,5/MWh,
        #    konservativ auf €3,5/MWh aufgerundet wegen Endlager-
        #    unsicherer Lebenszyklus-Phase.
        #  - 10,0 (ee_optimistic): NEA-Korridor-Obergrenze (»Projected
        #    Costs of Generating Electricity 2020«, 0,1-2,4 ct/kWh) plus
        #    Liability-Externalisierung — EE-Lager-Position »vertragliche
        #    Funded Decommissioning unterdeckt die echten Lifecycle-
        #    Kosten, Sozialisierung über NDA-Reststaat üblich«.
        #  - 3,5 (bestand_optimistic / weiterso_optimistic): wie neutral
        #    (kein eigenes KKW-Programm).
        "neutral_default": 3.5,
        "ee_optimistic": 10.0,
        "atom_optimistic": 2.0,
        "bestand_optimistic": 3.5,
        "weiterso_optimistic": 3.5,
        "source_tag": "EDF-HPC-CFD + NEA-PROJECTED-COSTS-2020",
        "verteilung": "lognormal",  # asymmetrisch, Liability-Externalisierung
        "label": "KKW-Decommissioning-Beitrag",
    },
    "nuclear_waste_transfer_eur_mwh": {
        # KKW-Neubau Endlager-Waste-Transfer-Price pro MWh Output (€/MWh).
        # Pendant zum HPC-CfD »Waste Transfer Price« (NDA-Regulierung
        # plus Funded Decommissioning Programme).
        #  - 1,0 (atom_optimistic): HPC-Untergrenze £1/MWh ≈ €1/MWh —
        #    Atom-Lager: »Konsolidierungs-Lager läuft«.
        #  - 1,5 (neutral_default): HPC-Mid-Range £1,5/MWh ≈ €1,8/MWh,
        #    konservativ auf €1,5/MWh kalibriert.
        #  - 4,0 (ee_optimistic): Tieflager-Suche unbekannt + Konditionierung
        #    + Transport-Kosten — EE-Lager-Position »Endlager-Realisierung
        #    nicht im HPC-Tarif abgebildet«.
        #  - 1,5 (bestand_optimistic / weiterso_optimistic): wie neutral.
        "neutral_default": 1.5,
        "ee_optimistic": 4.0,
        "atom_optimistic": 1.0,
        "bestand_optimistic": 1.5,
        "weiterso_optimistic": 1.5,
        "source_tag": "EDF-HPC-CFD + NEA-PROJECTED-COSTS-2020",
        "verteilung": "lognormal",
        "label": "KKW-Endlager-Beitrag",
    },
    "battery_discharge_vlh": {
        # Battery-Tagesarbitrage-VLH pro installierter GW im annual-aggregate.
        # Steuert den RTE-Verlust-Bedarf der Generatoren über
        # discharge_twh × (1/RTE − 1).
        # Lit-Bandbreite (BNEF-2025-ESS Outlook für Cycle-Häufigkeit,
        # BATTERY-CHARTS-RWTH + FIGGENER-2022 für DE-Bestands-Empirie,
        # MODO-2025 für DE-spezifische Tagesarbitrage-Modellierung):
        #  - 300 (atom_optimistic / bestand_optimistic): KKW-Bandlast bzw.
        #    Erdgas-Bestand reduzieren Tagesarbitrage-Bedarf — Battery dient
        #    eher Frequenz-Stabilität (wenige Zyklen × kurze Discharge-
        #    Dauer ≈ 75 Tageszyklen × 4h).
        #  - 500 (neutral_default): BNEF-DE-Mid-Range, ~125 Tageszyklen × 4h.
        #  - 800 (ee_optimistic): hohe PV-Penetration → mehr Tageszyklen
        #    (~200 Zyklen × 4h, BNEF-Obergrenze für marktorientierte Systeme).
        #  - 500 (weiterso_optimistic): markt-getrieben, Mittel.
        # Harte Obergrenze aus Battery-Lifetime-Cycles 6.000 / 15 a × 4h
        # = 1.600 h/a. Wirtschaftlich rentable Nutzung 50-70 % davon
        # ≈ 800-1.100 h/a für aktive EE-Systeme.
        # Anmerkung 4-h-Discharge-Annahme: Forecast-Standard ab BNEF 2027.
        # DE-Bestand 2024 liegt bei ~2-h-Systemen (BATTERY-CHARTS-RWTH);
        # die VLH-Werte gelten für die 4-h-projizierte 2030+-Generation.
        "neutral_default": 500.0,
        "ee_optimistic": 800.0,
        "atom_optimistic": 300.0,
        "bestand_optimistic": 300.0,
        "weiterso_optimistic": 500.0,
        "source_tag": "BNEF-2025-ESS, MODO-2025, BATTERY-CHARTS-RWTH",
        "verteilung": "normal",
        "label": "Battery-Discharge-VLH",
    },
    "nuclear_realization_rate": {
        # Sensi-Achse: KKW-Realisierungsgrad. Forward-Cost-Hebel auf
        # KKW-Pfade (zeitliche Verschiebung im Hauptmodell, monetärer
        # Aufschlag im Snapshot-Modell — Mechanik-Asymmetrie zu
        # nep_realisierung_grad ist methodisch begründet).
        # Bandbreite empirisch verteidigbar:
        #  - 1,00 (atom_optimistic): KKW-Lager-Optimum, Plan-Bauzeit
        #    erfüllt mit FOAK-Lernkurven-Kompensation.
        #  - 0,40 (neutral_default): Empirisch-Mittel der westlichen
        #    FOAK-Reaktoren mit moderater Lernkurven-Korrektur (OL3 18 J,
        #    Flam 17 J, Hinkley 13+J Plan, Vogtle 14-15 J).
        #  - 0,20 (ee_optimistic): EE-Lager-Position »KKW-Bauzeit-Risiko
        #    ist Hinkley-realistisch ohne staatliche Intervention«.
        #  - 0,40 (bestand_optimistic): BESTAND-Lager hat keine eigene
        #    KKW-Position — neutral_default als Platzhalter.
        #  - 0,40 (weiterso_optimistic): WEITER-SO baut keinen Neubau,
        #    Platzhalter wie bestand.
        # Default 0,40. Effekt im Snapshot: linearer Aufschlag
        # auf KKW-Pfad-Forward-Cost (3,1 ct/kWh pro Einheit (1-grad)).
        # Im Hauptmodell zeitliche Verschiebung der Hochlauf-Trajektorie
        # via sqrt-symmetrischer Aufteilung auf Bauzeit + Zielkapa.
        "neutral_default": 0.40,
        "ee_optimistic": 0.20,
        "atom_optimistic": 1.00,
        "bestand_optimistic": 0.40,
        "weiterso_optimistic": 0.40,  # kein Neubau, Platzhalter
        "source_tag": "WNA-2025, OECD-NEA-REDCOST-2020",
        "verteilung": "normal",
        "label": "KKW-Realisierungsgrad",
    },
}


def camp_range(param: str) -> tuple:
    """Liefert ``(low, high)`` für einen Parameter aus den Lager-Bandbreiten.

    Die Reihenfolge ist immer ``(numerisch_niedriger, numerisch_höher)`` —
    unabhängig davon, welches Lager den niedrigeren Wert vertritt.
    Damit wird die Bandbreite einheitlich nutzbar für Tornado-Analyse
    und Monte-Carlo.
    """
    r = CAMP_RANGES[param]
    ee_opt = r["ee_optimistic"]
    atom_opt = r["atom_optimistic"]
    assert isinstance(ee_opt, int | float) and isinstance(atom_opt, int | float)
    return (min(ee_opt, atom_opt), max(ee_opt, atom_opt))
