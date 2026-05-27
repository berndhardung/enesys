"""Tests für die externe Sektor-Kopplungs-Schicht.

Pfade mit Strom-Demand < 840 TWh (WEITER-SO, BESTAND) externalisieren
fehlende Elektrifizierung in fossile Wärme + Verbrenner-Mobility. Die
Schicht ist parallel zum Strom-LCOE und macht die Lager-Asymmetrie der
Externalisierung für WSO/BESTAND quantitativ.

Mehrkosten-Lesart: Differenz zur elektrischen Alternative (Wärmepumpe +
E-Mobility), nicht fossile Brutto-Kosten. Eine reine Brutto-Lesart würde
fossil-brutto gegen null vergleichen statt gegen elektrisch-effizient —
das überzeichnet die Externalisierung systematisch.

Methodische Setzung: Strom-LCOE bleibt unverändert; externe Mehrkosten
+ CO₂ sind eigenständige PathResult-Felder
(`sector_coupling_external_eur_per_year`, `co2_external_mt_per_year`).
"""

from __future__ import annotations

import pytest

from enesys import compute_path

# Aktive Pfade laufen das Demand-Plateau realgrad-gekoppelt an (Drei-
# Schichten-Architektur): bei nep_realisierung_grad < 1 ist die Sektor-
# Kopplung 2045 noch nicht voll abgeschlossen, daher trägt der Pfad eine
# kleine externe Schicht (fossile Restwärme + Verbrenner-Restmobility für
# die Demand-Lücke gegenüber dem 350-TWh-Soll-Plateau).
AKTIVE_PFADE = ["ee_gas", "ee_h2", "kkw_gas", "kkw_h2"]

# Referenz-Pfade haben politisch gedämpfte Demand → große externe Schicht.
REFERENZ_PFADE = ["weiterso", "bestand"]


def _r(pid: str, camp: str = "neutral_default"):
    return compute_path(pid, [2045], camp=camp)[0]


class TestAktivePfadeExterneSchichtKleinerAlsReferenz:
    """Pfade mit voller Sektor-Kopplungs-Politik (Soll-Plateau 350 TWh)
    haben durch Realgrad-Kopplung eine kleine externe Schicht in 2045,
    aber deutlich kleiner als die Referenz-Pfade (WEITER-SO/BESTAND).
    Dies sichert die methodische Aussage »volle Sektor-Kopplungs-Politik
    schließt die Mehrheit der Wärme/Mobility-Externalisierung«."""

    @pytest.mark.parametrize("pid", AKTIVE_PFADE)
    def test_extern_eur_kleiner_als_referenz(self, pid):
        aktiv_eur = _r(pid).sector_coupling_external_eur_per_year
        weiterso_eur = _r("weiterso").sector_coupling_external_eur_per_year
        bestand_eur = _r("bestand").sector_coupling_external_eur_per_year
        # Aktive Pfade müssen mindestens 30 % unter dem kleineren der
        # beiden Referenz-Pfade liegen.
        referenz_min = min(weiterso_eur, bestand_eur)
        assert aktiv_eur < 0.7 * referenz_min, (
            f"{pid}: extern_eur {aktiv_eur / 1e9:.1f} Mrd EUR/a nicht "
            f"substanziell unter Referenz-Pfaden "
            f"(WSO {weiterso_eur / 1e9:.1f}, BESTAND {bestand_eur / 1e9:.1f}). "
            f"Aktive Pfade dürfen Realgrad-bedingt Restexternalisierung "
            f"tragen, aber deutlich weniger als gedämpfte Pfade."
        )

    @pytest.mark.parametrize("pid", AKTIVE_PFADE)
    def test_co2_extern_kleiner_als_referenz(self, pid):
        aktiv_co2 = _r(pid).co2_external_mt_per_year
        weiterso_co2 = _r("weiterso").co2_external_mt_per_year
        bestand_co2 = _r("bestand").co2_external_mt_per_year
        referenz_min = min(weiterso_co2, bestand_co2)
        assert aktiv_co2 < 0.7 * referenz_min, (
            f"{pid}: co2_extern {aktiv_co2:.1f} Mt/a nicht substanziell "
            f"unter Referenz-Pfaden (WSO {weiterso_co2:.1f}, "
            f"BESTAND {bestand_co2:.1f})."
        )


class TestReferenzPfadeMitExternerSchicht:
    """WEITER-SO und BESTAND haben Lücke → externe Kosten + CO₂."""

    def test_weiterso_extern_im_korridor(self):
        r = _r("weiterso")
        # Mehrkosten-Lesart-Erwartung: ~21 Mrd EUR/a (Hand-Berechnung:
        # 35,6 fossil + 9,6 CO₂-Pönale neutral − 14,55 Substitutions-
        # Strom = 30,7 → tatsächlich 21,1 wegen exakter Lücke-Skala
        # 0,67 × 200 TWh Wärme). 30J = ~630 Mrd EUR.
        eur_mrd = r.sector_coupling_external_eur_per_year / 1e9
        assert 17 <= eur_mrd <= 26, (
            f"WEITER-SO externe Mehrkosten {eur_mrd:.1f} Mrd EUR/a außerhalb "
            f"Erwartungs-Korridor 17-26 (Mehrkosten gegenüber "
            f"Wärmepumpe+E-Mobility)."
        )

    def test_bestand_extern_im_korridor(self):
        r = _r("bestand")
        eur_mrd = r.sector_coupling_external_eur_per_year / 1e9
        # BESTAND-Lücke ~10 % größer als WSO → ~23 Mrd EUR/a, 30J ~700 Mrd.
        assert 19 <= eur_mrd <= 28, (
            f"BESTAND externe Mehrkosten {eur_mrd:.1f} Mrd EUR/a außerhalb "
            f"Erwartungs-Korridor 19-28 (Mehrkosten gegenüber "
            f"Wärmepumpe+E-Mobility)."
        )

    def test_weiterso_co2_extern_im_korridor(self):
        r = _r("weiterso")
        assert 60 <= r.co2_external_mt_per_year <= 85, (
            f"WEITER-SO externe CO₂ {r.co2_external_mt_per_year:.1f} Mt/a "
            f"außerhalb Korridor 60-85 (Erwartung ~74)."
        )

    def test_bestand_co2_extern_groesser_weiterso(self):
        """BESTAND hat größere Lücke (330 vs. 300 TWh) → mehr CO₂."""
        ws = _r("weiterso")
        bs = _r("bestand")
        assert bs.co2_external_mt_per_year > ws.co2_external_mt_per_year, (
            "BESTAND-Lücke ist größer als WSO-Lücke; CO₂ extern muss höher sein."
        )


class TestLagerModulation:
    """CO₂-Pönale ist lager-spezifisch (asymmetrische Welt-Belief-
    Spreizung). Die externen EUR-Kosten variieren entsprechend,
    CO₂-Mengen sind lager-invariant (Hand-Schätzung-Mengen)."""

    def test_co2_mengen_lager_invariant(self):
        """Mengen sind nicht lager-abhängig (Hand-Schätzung-Konstanten)."""
        bs_neutral = _r("bestand", "neutral_default")
        bs_atom = _r("bestand", "atom_optimistic")
        # Mengen aus _FOSSIL_HEAT_TWH_FULL × Lücke-Faktor, nicht
        # vom Lager abhängig → exakt gleich.
        # Lücke kann minimal variieren (Demand-Trajektorie pro Lager),
        # daher kleine Toleranz.
        assert abs(bs_neutral.co2_external_mt_per_year - bs_atom.co2_external_mt_per_year) < 2.0

    def test_co2_pönale_lager_asymmetrisch(self):
        """EUR-Kosten in bestand_optimistic-Welt sind niedriger als in
        atom_optimistic-Welt (CO₂-Preis 100 vs 150 €/t — asymmetrische
        Welt-Belief-Spreizung)."""
        ws_atom = _r("weiterso", "atom_optimistic")
        ws_bestand = _r("weiterso", "bestand_optimistic")
        # atom-Welt: höherer CO₂-Preis → höhere Pönale → höhere EUR
        # bestand-Welt: niedriger CO₂-Preis → niedrigere EUR
        assert (
            ws_atom.sector_coupling_external_eur_per_year
            > ws_bestand.sector_coupling_external_eur_per_year
        ), (
            "atom_optimistic mit 150 €/t CO₂ muss höhere externe "
            "EUR-Kosten erzeugen als bestand_optimistic mit 100 €/t."
        )


class TestStromLcoeUnberuehrt:
    """Schicht-Invariante: Strom-LCOE bleibt unverändert. Die externe
    Sektor-Kopplungs-Schicht ist parallel, nicht in den LCOE integriert."""

    @pytest.mark.parametrize("pid", AKTIVE_PFADE + REFERENZ_PFADE)
    def test_lcoe_components_kein_sektor_kopplung(self, pid):
        """lcoe_components darf KEINEN sektor_kopplung-Eintrag haben."""
        r = _r(pid)
        assert "sektor_kopplung" not in r.lcoe_components, (
            f"{pid}: lcoe_components hat einen sektor_kopplung-Eintrag — "
            f"die externe Schicht muss parallel zum LCOE laufen, "
            f"nicht in ihn integriert sein."
        )

    @pytest.mark.parametrize("pid", REFERENZ_PFADE)
    def test_lcoe_strom_unter_25ct(self, pid):
        """WSO/BESTAND-Strom-LCOE bleibt im realistischen Korridor
        (16-18 ct/kWh ohne externe Schicht)."""
        r = _r(pid)
        assert r.lcoe_ct_kwh < 25, (
            f"{pid}: Strom-LCOE {r.lcoe_ct_kwh:.2f} ct ist zu hoch — "
            f"vermutlich Aufschlag fälschlich im LCOE statt extern."
        )
