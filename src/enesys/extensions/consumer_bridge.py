"""Endverbraucherpreis-Brücke vom Forward-Cost-LCOE auf die Stromrechnung.

Volkswirtschaftliche Forward-Cost-Größe (Pfad-Modell, 30-Jahres-Mittel) plus
Aufschläge (Vertrieb, Steuern, Abgaben, Marktaufschlag) = brutto auf der
Stromrechnung. UI-frei: dieses Modul enthält keine Streamlit-Calls und kann
vom Public-Mirror importiert werden, auch wenn ``enesys.ui`` ausgenommen wird.

Konsumenten:
- ``enesys.ui.streamlit_path`` — Streamlit-Verbraucher-Tab (Berechnungs-Aufruf
  + Slider-Defaults).
- ``enesys.ui.streamlit_sources`` — Slider-Tooltips greifen auf die
  Verbraucher-Komponenten zurück.
- ``tests/extensions/test_consumers_bridge.py`` und ``test_external_sources.py``
  — Konsistenz- und Brücken-Tests.
"""

from __future__ import annotations

from typing import TypedDict

from enesys.extensions.consumers import (
    BDEW_2026_HOUSEHOLD,
    BDEW_2026_INDUSTRY,
    BDEW_2026_SOURCE,
    MARKET_SURCHARGE_CALIBRATED,
    TCL_2026,
)

# Netzentgelte, die in der Forward-Cost-Definition (Pfad-Modell) bereits
# stecken — werden bei der Brücke auf die Verbraucher-Sicht herausgerechnet,
# damit das aktuelle BDEW-Netzentgelt sauber überlagert werden kann.
NETZ_IM_FORWARD_COST_CT = 7.0  # [SRC: BNetzA-2024]

# BDEW-Realwert für die Marktaufschlag-Kalibrierung (Haushalt, Mai 2026,
# 3.500 kWh/Jahr brutto). Die Differenz zwischen diesem Realwert und der
# Modell-Forward-Cost-Trajektorie definiert den Marktaufschlag bei
# `calibrated_market_surcharge()`.
BDEW_HOUSEHOLD_GROSS_TODAY_CT: float = 37.0  # [SRC: BDEW-2026]


def calibrated_market_surcharge(
    weiterso_forward_cost_ct: float,
    *,
    target_gross_ct: float = BDEW_HOUSEHOLD_GROSS_TODAY_CT,
    netz_today_ct: float = BDEW_2026_HOUSEHOLD.grid_fees,
    sales_margin_ct: float = 1.5,
    vat_pct: float = 19.0,
) -> float:
    """Marktaufschlag, der WEITER-SO heute auf den BDEW-Realwert kalibriert.

    Reverse der Brutto-Formel: gegeben WEITER-SO-Forward-Cost-LCOE und
    Soll-Brutto-Wert, wird der Marktaufschlag so berechnet, dass
    `compute_consumer_price(forward_cost=weiterso, marktaufschlag=…)`
    exakt `target_gross_ct` liefert.

    Vermeidet die manuelle Pflege einer kalibrierten Konstante, wenn
    sich das Pfad-Modell verändert (LCOE-Drift) oder der BDEW-Realwert
    aktualisiert wird.
    """
    net_target = target_gross_ct / (1.0 + vat_pct / 100.0)
    fixed_levies = TCL_2026.stromsteuer + TCL_2026.konzessionsabgabe + TCL_2026.sonstige_umlagen
    return (
        net_target
        - weiterso_forward_cost_ct
        + NETZ_IM_FORWARD_COST_CT
        - netz_today_ct
        - sales_margin_ct
        - fixed_levies
    )


class EndverbraucherKomponente(TypedDict):
    default: float
    min: float
    max: float
    label: str
    tooltip: str


class Verbrauchergruppe(TypedDict):
    label: str
    description: str
    kwh_pro_jahr: float
    use_industry_rates: bool
    expected_today: str


def compute_consumer_price(
    forward_cost: float,
    vertriebsmarge: float,
    electricity_tax: float,
    concession_levy: float,
    other_levies: float,
    vat_pct: float,
    netz_heute: float = BDEW_2026_HOUSEHOLD.grid_fees,
    marktaufschlag: float = MARKET_SURCHARGE_CALIBRATED,
    use_industry_rates: bool = False,
) -> dict:
    """Berechnet Endverbraucherpreis aus Forward Cost und Aufschlägen.

    Logik (Verbraucher-Sicht, methodisch getrennt vom Forward Cost):

        Brutto = (Forward Cost
                  − netz_im_FC (7,0 ct, BNetzA-Forward, im FC enthalten)
                  + netz_heute (9,3 ct Default, BDEW Mai 2026 fortgeschrieben)
                  + marktaufschlag (4,4 ct Default, kalibriert auf
                                    WEITER-SO heute = 37,0 ct)
                  + Vertriebsmarge
                  + Stromsteuer
                  + Konzessionsabgabe
                  + Umlagen) × (1 + MwSt)

    Hintergrund:
    -   Forward Cost ist eine LCOE-Vollkostengröße über 30-Jahres-Mittel
        (Pfad-Modell, Forschungsfrage volkswirtschaftlich).
    -   Auf der Stromrechnung kommen zusätzlich (a) der Marginalpreis-
        Effekt im Strommarkt und (b) Energiekrise-Bestandsverträge an.
        Beide werden vereinfacht zu einem konstanten Marktaufschlag
        kalibriert, sodass WEITER-SO heute = BDEW-Realwert ergibt.
        Pfad-Differenzen bleiben dadurch identisch zu Forward-Cost-
        Differenzen × (1 + MwSt) — der Marktaufschlag wirkt auf alle
        Pfade gleich (methodische Vereinfachung).
    -   Industrie ist vorsteuerabzugsberechtigt (Netto = Brutto), bekommt
        Stromsteuer-Spitzenausgleich, Konzessionsabgabe-Reduktion und
        §19-Umlage-Befreiung.
    """
    # Industrie-Rabatte
    if use_industry_rates:
        electricity_tax_effective = electricity_tax * 0.25  # Spitzenausgleich, ~0,5 ct
        concession_levy_effective = 0.11  # historisch reduzierter Industrie-Satz
        other_levies_effective = other_levies * 0.4  # §19-Befreiung et al.
    else:
        electricity_tax_effective = electricity_tax
        concession_levy_effective = concession_levy
        other_levies_effective = other_levies

    # Brücke Forward Cost (mit BNetzA-Netz 7,0) → Verbraucher-Sicht
    # (Stromrechnung mit BDEW-Netz heute fortgeschrieben).
    # Marktaufschlag kalibriert auf WEITER-SO heute = 37,0 ct (BDEW Mai 2026).
    fc_without_grid_model = forward_cost - NETZ_IM_FORWARD_COST_CT
    generation_and_market = fc_without_grid_model + marktaufschlag

    net = (
        generation_and_market
        + netz_heute
        + vertriebsmarge
        + electricity_tax_effective
        + concession_levy_effective
        + other_levies_effective
    )
    if use_industry_rates:
        gross = net  # Vorsteuerabzug
        vat_share = 0.0
    else:
        vat_share = net * (vat_pct / 100)
        gross = net + vat_share

    return {
        "forward_cost": forward_cost,
        "netz_modell": NETZ_IM_FORWARD_COST_CT,
        "netz_heute": netz_heute,
        "marktaufschlag": marktaufschlag,
        "vertriebsmarge": vertriebsmarge,
        "stromsteuer": electricity_tax_effective,
        "konzessionsabgabe": concession_levy_effective,
        "umlagen": other_levies_effective,
        "netto": net,
        "mwst": vat_share,
        "brutto": gross,
    }


# ============================================================================
# Slider-Defaults für Endverbraucher-Aufschläge
# ============================================================================
#
# Werte aus Forward-Cost-Methodik, BDEW-Strompreisanalyse Mai 2026.
# Haushalts-Durchschnitt 37,0 ct/kWh brutto =
#   Beschaffung+Vertrieb 15,2 + Netzentgelte 9,3 + Steuern/Abgaben/Umlagen 12,6.
# Werte aus ``enesys.extensions.consumers`` (Single-Source-of-Truth für BDEW Mai 2026).
# Beim BDEW-Update nur diese eine Quelle anfassen — alle Slider-Defaults hier
# aktualisieren sich automatisch.

ENDVERBRAUCHER_KOMPONENTEN: dict[str, EndverbraucherKomponente] = {
    "vertriebsmarge": {
        "default": 1.5,
        "min": 1.0,
        "max": 3.0,
        "label": "Vertriebsmarge (ct/kWh)",
        "tooltip": (
            "**Vertriebsmarge** · Default 1,5 ct/kWh. "
            "Marge der Stromlieferanten zwischen Großhandelspreis und "
            "Endverbraucherpreis. Bandbreite normal 1-3 ct/kWh; in "
            "Energiekrisen (2022-2023) zeitweise 5-8 ct/kWh. Quelle: "
            f"BDEW *Strompreisanalyse {BDEW_2026_SOURCE.stand}*."
        ),
    },
    "stromsteuer": {
        "default": TCL_2026.stromsteuer,
        "min": 0.0,
        "max": TCL_2026.stromsteuer,
        "label": "Stromsteuer (ct/kWh)",
        "tooltip": (
            f"**Stromsteuer** · Default {TCL_2026.stromsteuer} ct/kWh. "
            "Gesetzlich festgelegt im Stromsteuergesetz, Stand 2026 "
            "unverändert. Für Haushalte der volle Satz; für "
            "energieintensive Industrie reduziert "
            "(0,5 ct/kWh nach Spitzenausgleich). Bandbreite hier "
            f"0 (komplette Abschaffung) bis {TCL_2026.stromsteuer} (Status quo)."
        ),
    },
    "konzessionsabgabe": {
        "default": TCL_2026.konzessionsabgabe,
        "min": TCL_2026.konzessionsabgabe_min,
        "max": TCL_2026.konzessionsabgabe_max,
        "label": "Konzessionsabgabe (ct/kWh)",
        "tooltip": (
            f"**Konzessionsabgabe** · Default {TCL_2026.konzessionsabgabe} ct/kWh (Mittel). "
            "An Gemeinden für die Nutzung des öffentlichen Wegerechts. "
            f"Gestaffelt nach Gemeindegröße: {TCL_2026.konzessionsabgabe_min} ct/kWh (Großstadt) "
            f"bis {TCL_2026.konzessionsabgabe_max} ct/kWh (kleine Gemeinde). "
            f"Quelle: BDEW {BDEW_2026_SOURCE.stand}."
        ),
    },
    "umlagen": {
        "default": TCL_2026.sonstige_umlagen,
        "min": 1.5,
        "max": 4.0,
        "label": "KWKG/Offshore/§19/sonstige Umlagen (ct/kWh)",
        "tooltip": (
            f"**KWKG/Offshore/§19/sonstige Umlagen** · Default {TCL_2026.sonstige_umlagen} ct/kWh. "
            f"Rückgerechnet aus dem BDEW-Block 'Steuern/Abgaben/Umlagen' "
            f"({BDEW_2026_HOUSEHOLD.taxes_charges_levies} ct) abzüglich "
            f"Stromsteuer {TCL_2026.stromsteuer}, Konzessionsabgabe "
            f"{TCL_2026.konzessionsabgabe} und MwSt-Anteil "
            f"{BDEW_2026_HOUSEHOLD.vat_share:.2f}. "
            "Enthält: KWKG-Umlage, Offshore-Netzumlage, "
            "§19-StromNEV-Umlage, AbLaV-Umlage. EEG-Umlage seit 2022 = 0. "
            f"Bandbreite 1,5-4,0 je nach Politik-Setzung. "
            f"Quelle: BDEW {BDEW_2026_SOURCE.stand}."
        ),
    },
    "mwst": {
        "default": TCL_2026.mwst_pct,
        "min": 7.0,
        "max": TCL_2026.mwst_pct,
        "label": "Mehrwertsteuer (%)",
        "tooltip": (
            f"**Mehrwertsteuer** · Default {TCL_2026.mwst_pct:.0f} %. "
            "Wird auf den gesamten Nettopreis erhoben. "
            "Bandbreite: 7 % (ermäßigter Satz, politisch immer wieder "
            f"diskutiert für Strom als Grundbedarf) bis {TCL_2026.mwst_pct:.0f} % (Status quo)."
        ),
    },
    "netz_heute": {
        "default": BDEW_2026_HOUSEHOLD.grid_fees,
        "min": 6.0,
        "max": 12.0,
        "label": "Netzentgelte heute (ct/kWh)",
        "tooltip": (
            f"**Netzentgelte heute** · Default {BDEW_2026_HOUSEHOLD.grid_fees} ct/kWh. "
            f"BDEW-Strompreisanalyse {BDEW_2026_SOURCE.stand} "
            f"(Haushalt {BDEW_2026_HOUSEHOLD.annual_consumption_kwh} kWh/Jahr): "
            f"{BDEW_2026_HOUSEHOLD.grid_fees} ct/kWh, Rückgang um 1,6 ct/kWh ggü. Vorjahr durch "
            "Bundeszuschuss zu Übertragungsnetzentgelten. Wird in der "
            "Verbraucher-Sicht statt der im Forward Cost enthaltenen "
            "BNetzA-Forward-Trend-Komponente (7,0 ct/kWh) verwendet, "
            "damit der Verbraucher seine reale Stromrechnung wiederfindet. "
            "Bandbreite 6 (Forward-Trend ohne Zuschuss) bis 12 (worst-case "
            f"Netzausbau-Hochlauf). Quelle: BDEW {BDEW_2026_SOURCE.stand}."
        ),
    },
    "marktaufschlag": {
        "default": MARKET_SURCHARGE_CALIBRATED,
        "min": 0.0,
        "max": 8.0,
        "label": "Marktaufschlag (ct/kWh)",
        "tooltip": (
            f"**Marktaufschlag** · Default {MARKET_SURCHARGE_CALIBRATED} ct/kWh. "
            "Differenz zwischen volkswirtschaftlichen LCOE-Vollkosten "
            "(Modell-Forward-Cost) und realem Strommarkt-Preis. Im "
            "Strommarkt bestimmt das teuerste laufende Kraftwerk "
            "(Marginalpreis) den Preis aller Erzeuger; inframarginale "
            "Anlagen erzielen Marktrenten. Plus aktueller Energiekrise-"
            "Nachhall in Bestandsverträgen 2022/23, der bis ~2028 "
            "ausklingt. Default kalibriert: WEITER-SO heute = "
            f"BDEW-Realwert {BDEW_2026_HOUSEHOLD.gross} ct/kWh. "
            "Bandbreite 0 (rein LCOE-fair) bis 8 (Krisen-Spitze). "
            "Methodische Vereinfachung: konstant über alle Pfade — "
            "in EE-Pfaden strukturell kleiner."
        ),
    },
}

VERBRAUCHERGRUPPEN: dict[str, Verbrauchergruppe] = {
    "haushalt": {
        "label": "🏠 Privater Haushalt",
        "description": "3.500 kWh/Jahr · 4-Personen-Familie",
        "kwh_pro_jahr": BDEW_2026_HOUSEHOLD.annual_consumption_kwh,
        "use_industry_rates": False,
        "expected_today": (
            f"{BDEW_2026_HOUSEHOLD.gross:.1f} ct/kWh brutto "
            f"(BDEW {BDEW_2026_SOURCE.stand})".replace(".", ",")
        ),
    },
    "mittelstand": {
        "label": "🏢 Mittelstand",
        "description": "500 MWh/Jahr · z.B. mittlerer Gewerbebetrieb",
        "kwh_pro_jahr": 500_000,
        "use_industry_rates": False,
        "expected_today": (
            f"{BDEW_2026_INDUSTRY.kleine_mittlere:.1f} ct/kWh netto "
            f"(BDEW {BDEW_2026_SOURCE.stand}, kleine bis mittlere Industrie)"
        ).replace(".", ","),
    },
    "industrie": {
        "label": "🏭 Großindustrie",
        "description": "≥ 100 GWh/Jahr · z.B. Aluminium-, Stahl-, Chemiewerk",
        "kwh_pro_jahr": 100_000_000,
        "use_industry_rates": True,
        "expected_today": "6-12 ct/kWh netto (mit Privilegien <8 ct)",
    },
}
