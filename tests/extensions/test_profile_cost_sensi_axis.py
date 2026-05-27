"""Profile-Cost als Lager-Sensi-Achse.

Stellt sicher, dass der Profile-Cost-Aufschlag eine echte Lager-Achse
ist und nicht eine Konstante pro path_id.

Drei Aussagen:

1. **Lager-Variation wirkt:** Für `ee_gas`, `kkw_gas`, `bestand` produzieren
   drei Lager (`ee_optimistic` / `neutral_default` / `atom_optimistic`)
   drei verschiedene Profile-Cost-Aufschläge — und damit drei verschiedene
   LCOE-Werte.

2. **param_overrides hat Vorrang:** Ein direkter Override des
   ``profile_cost_ee_ct_kwh``-Keys verschiebt das Ergebnis um genau den
   Differenz-Betrag (LCOE-Sanity).

3. **EE-GAS bleibt im neutralen Default günstiger als KKW-GAS** — die
   lit-konservative Profile-Cost-Setzung (EE +0,7 / KKW +0,1) kippt die
   Reue-Richtung im neutral_default-Lager nicht.
"""

from __future__ import annotations

import pytest

from enesys import compute_path
from enesys.core.camp_ranges import CAMP_RANGES
from enesys.extensions.profile_costs import (
    combined_surcharge,
    profile_cost_surcharge,
)

# =============================================================================
# 1. Lager-Achse — drei Werte, drei LCOE
# =============================================================================


class TestLagerAchseWirktImAufschlag:
    """Reiner Aufschlag-Test ohne Modell-Lauf (schnell)."""

    def test_ee_lager_spreizung_monoton(self):
        """EE-Profile-Cost: ee_optimistic < neutral < atom_optimistic.

        atom_optimistic auf die Lit-Untergrenze 1,0 kalibriert (statt
        Lit-Mid-Range 1,3); die Lit-Mid-Range-Variante bleibt als
        separat prüfbare Sensi-Achse über `param_overrides`.
        """
        ee_opt = profile_cost_surcharge("ee_gas", "ee_optimistic")
        neutral = profile_cost_surcharge("ee_gas", "neutral_default")
        atom_opt = profile_cost_surcharge("ee_gas", "atom_optimistic")
        assert ee_opt < neutral < atom_opt, (
            f"EE-Spreizung verletzt: {ee_opt} / {neutral} / {atom_opt}"
        )
        # Kalibrier-Anker (Lit-Untergrenze):
        assert ee_opt == pytest.approx(0.3)
        assert neutral == pytest.approx(0.7)
        assert atom_opt == pytest.approx(1.0)

    def test_kkw_lager_nicht_monoton_aber_ee_groesser_neutral(self):
        """KKW-Profile-Cost: ee_optimistic schreibt KKW eine höhere
        Profile-Cost zu (Grundlast-Mismatch in EE-dominierter Welt),
        neutral und atom_optimistic teilen den Lit-Mittel-Wert (kein
        zusätzlicher Atom-Optimisten-Bonus, bewahrt den
        Forward-Cost-Korridor)."""
        ee_opt = profile_cost_surcharge("kkw_gas", "ee_optimistic")
        neutral = profile_cost_surcharge("kkw_gas", "neutral_default")
        atom_opt = profile_cost_surcharge("kkw_gas", "atom_optimistic")
        assert ee_opt > neutral, f"KKW-Inversion verletzt: {ee_opt} / {neutral} / {atom_opt}"
        assert atom_opt == pytest.approx(neutral), (
            f"atom_optimistic muss = neutral_default für KKW-Achse sein "
            f"(kein Optimisten-Bonus), aber: {atom_opt} ≠ {neutral}"
        )

    def test_ee_h2_und_ee_gas_teilen_achse(self):
        """Beide variablen EE-Pfade fahren dieselbe profile_cost_ee-Achse."""
        for lager in ("ee_optimistic", "neutral_default", "atom_optimistic"):
            assert profile_cost_surcharge("ee_gas", lager) == profile_cost_surcharge("ee_h2", lager)

    def test_kkw_h2_und_kkw_gas_teilen_achse(self):
        for lager in ("ee_optimistic", "neutral_default", "atom_optimistic"):
            assert profile_cost_surcharge("kkw_gas", lager) == profile_cost_surcharge(
                "kkw_h2", lager
            )

    def test_misch_pfade_teilen_achse(self):
        for lager in ("ee_optimistic", "neutral_default", "atom_optimistic"):
            assert profile_cost_surcharge("bestand", lager) == profile_cost_surcharge(
                "weiterso", lager
            )


# =============================================================================
# 2. param_overrides hat Vorrang
# =============================================================================


class TestParamOverridesVorrang:
    def test_override_ee_setzt_wert(self):
        wert = profile_cost_surcharge(
            "ee_gas",
            camp="neutral_default",
            param_overrides={"profile_cost_ee_ct_kwh": 2.5},
        )
        assert wert == pytest.approx(2.5)

    def test_override_kkw_setzt_wert(self):
        wert = profile_cost_surcharge(
            "kkw_gas",
            camp="atom_optimistic",
            param_overrides={"profile_cost_kkw_ct_kwh": 0.42},
        )
        assert wert == pytest.approx(0.42)

    def test_override_unbekannter_key_fallback_lager(self):
        """Override ohne passenden Key fällt auf CAMP_RANGES zurück."""
        wert = profile_cost_surcharge(
            "ee_gas",
            camp="neutral_default",
            param_overrides={"profile_cost_kkw_ct_kwh": 99.0},  # falscher Key
        )
        assert wert == pytest.approx(0.7)


# =============================================================================
# 3. CAMP_RANGES-Eintrags-Hygiene
# =============================================================================


class TestLagerRangesHygiene:
    """Profile-Cost-Einträge erfüllen das CAMP_RANGES-Schema."""

    @pytest.mark.parametrize(
        "key",
        ["profile_cost_ee_ct_kwh", "profile_cost_kkw_ct_kwh", "profile_cost_misch_ct_kwh"],
    )
    def test_alle_lager_keys_vorhanden(self, key):
        spec = CAMP_RANGES[key]
        for lager_key in (
            "neutral_default",
            "ee_optimistic",
            "atom_optimistic",
            "bestand_optimistic",
            "weiterso_optimistic",
        ):
            assert lager_key in spec, f"{key} fehlt {lager_key}"

    @pytest.mark.parametrize(
        "key",
        ["profile_cost_ee_ct_kwh", "profile_cost_kkw_ct_kwh", "profile_cost_misch_ct_kwh"],
    )
    def test_source_und_label(self, key):
        spec = CAMP_RANGES[key]
        assert "source_tag" in spec and spec["source_tag"]
        assert "label" in spec and spec["label"]


# =============================================================================
# 4. Modell-End-zu-End: Sensi-Achse verschiebt LCOE
# =============================================================================


def _lcoe(pid: str, camp: str, overrides=None):
    return compute_path(pid, [2045], camp=camp, param_overrides=overrides)[0].lcoe_ct_kwh


class TestSensiAchseImLCOE:
    """End-zu-End-Beweis: drei Lager → drei verschiedene LCOE für EE-GAS."""

    def test_ee_gas_drei_lager_drei_lcoe(self):
        lcoe_ee = _lcoe("ee_gas", "ee_optimistic")
        lcoe_neutral = _lcoe("ee_gas", "neutral_default")
        lcoe_atom = _lcoe("ee_gas", "atom_optimistic")

        # Profile-Cost-Beiträge 0,3 / 0,7 / 1,0 ct/kWh — also ~0,4 ct
        # Spreizung zwischen ee_opt und neutral, ~0,3 ct zwischen neutral
        # und atom_opt. Andere Lager-Effekte überlagern, daher nur
        # Streuung > 0,05 ct prüfen.
        assert abs(lcoe_neutral - lcoe_ee) > 0.05, (
            f"ee_optimistic↔neutral verschiebt LCOE kaum: {lcoe_ee:.3f} / {lcoe_neutral:.3f}"
        )
        assert abs(lcoe_atom - lcoe_neutral) > 0.05, (
            f"neutral↔atom_optimistic verschiebt LCOE kaum: {lcoe_neutral:.3f} / {lcoe_atom:.3f}"
        )

    def test_override_verschiebt_lcoe(self):
        """Override `profile_cost_ee_ct_kwh` 0,7 → 2,0 → +1,3 ct LCOE."""
        baseline = _lcoe("ee_gas", "neutral_default")
        verschoben = _lcoe(
            "ee_gas",
            "neutral_default",
            overrides={"profile_cost_ee_ct_kwh": 2.0},
        )
        delta = verschoben - baseline
        assert delta == pytest.approx(1.3, abs=0.02), (
            f"Override-Differenz erwartet ~1,3 ct, ist {delta:.3f}"
        )


# =============================================================================
# 5. EE-GAS-Kostenführerschaft im Default kippt nicht
# =============================================================================


class TestEEGasKostenfuehrungNeutral:
    """Erwartet EE-GAS-LCOE < KKW-GAS-LCOE unter Default-Parametern."""

    def test_ee_gas_unter_kkw_gas_neutral(self):
        ee_gas = _lcoe("ee_gas", "neutral_default")
        kkw_gas = _lcoe("kkw_gas", "neutral_default")
        assert ee_gas < kkw_gas, (
            f"Erwartet ee_gas < kkw_gas unter neutral_default; "
            f"erhalten: ee_gas={ee_gas:.3f}, kkw_gas={kkw_gas:.3f}."
        )

    def test_h1_netto_nicht_groesser_als_alternative_pfad_diff(self):
        """Sanity: H1 + H2 zusammen verschieben EE-GAS höchstens um die
        Pfad-Diff-Bandbreite, die das Modell sonst aufruft. Belegt, dass
        H1+H2 kein dominanter Hebel ist."""
        netto_ee = combined_surcharge("ee_gas", "atom_optimistic")
        netto_kkw = combined_surcharge("kkw_gas", "atom_optimistic")
        diff = netto_ee - netto_kkw
        # atom_optimistic-Lager (DSM symmetrisch −0,3 ct/kWh):
        # ee_gas Netto = 1,0 − 0,3 = 0,7 ct; kkw_gas Netto = 0,1 − 0,3 =
        # −0,2 ct. Diff = 0,9 ct. Die Asymmetrie kommt jetzt vollständig
        # aus der H1-Profile-Cost-Spreizung, weil das Atom-Lager die
        # DSM-Asymmetrie zwischen EE und KKW explizit aufhebt.
        assert 0.5 <= diff <= 1.1, f"H1+H2-Diff im atom_optimistic-Lager out-of-range: {diff:.3f}"
