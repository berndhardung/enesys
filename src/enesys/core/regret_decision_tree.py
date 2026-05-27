"""Reue-Matrix nach Savage-Minimax-Regret.

Konstruktion: für **jede Welt-Sicht** und **jede Politik** liefert sie
den effektiven LCOE und die Reue als Differenz zur in dieser Welt-Sicht
**besten Politik**.

Methodische Basis:

- Savage Minimax Regret (Leonard Savage 1951): Reue einer Politik in
  Welt W = LCOE(Politik, W) − min(LCOE(*, W)). Damit ist Reue per
  Konstruktion nicht-negativ und Welt-relativ.
- Welt-Sichten sind die vier Lager-Setzungen
  (``ee_optimistic`` / ``neutral_default`` / ``atom_optimistic`` /
  ``bestand_optimistic``); Politik-Wahlen die sechs Pfade plus
  EE-/KKW-Politik-Sammelblöcke.

Die Reue-Matrix dient als Synthese-Sicht über alle Lager-Politik-
Kombinationen — eine verdichtete Entscheidungstheorie-Tabelle. Sie
liefert die Politik-Empfehlung unter Minimax-Regret: nicht der in
jeder Welt günstigste Pfad gewinnt (im atom_optimistic-Lager kippt das
zugunsten KKW-GAS), sondern derjenige mit der niedrigsten maximalen
Reue über alle Welt-Sichten.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .rolling_lcoe import rolling_lcoe

# Schaden-Skalierung
YEARS = 30
DEMAND_TWH = 858.0

# Vier kanonische Welt-Lager. Reihenfolge folgt dem »adversarial mapping«:
# ee_optimistic ist die EE-Optimisten-Welt (KKW als FOAK realistisch teuer),
# atom_optimistic ist die Atom-Optimisten-Welt (KKW als NOAK gelingend),
# bestand_optimistic ist die »EE/H2-Skeptiker«-Welt, neutral_default die
# empirische Mitte.
CAMP_WORLDS: tuple[str, ...] = (
    "ee_optimistic",
    "neutral_default",
    "atom_optimistic",
    "bestand_optimistic",
)


class PolicyChoice(Enum):
    """Sechs Politik-Wahlen.

    EE und KKW jeweils in Gas- und H2-Sub-Varianten; Voll-Matrix
    6 × 4 Welten = 24 Zellen. Die EE-Politik wird in der Auswertung
    als ein Sammel-Block aus EE_GAS und EE_H2 betrachtet; KKW-Politik
    analog aus KKW_GAS und KKW_H2.
    """

    EE_GAS = "ee_gas"
    EE_H2 = "ee_h2"
    KKW_GAS = "kkw_gas"
    KKW_H2 = "kkw_h2"
    BESTAND = "bestand"
    WEITERSO = "weiterso"


@dataclass(frozen=True)
class RegretMatrixCell:
    """Eine Zelle der Reue-Matrix: (Politik, Welt) → LCOE + Reue.

    Felder:
        policy: gewählte Politik
        world: Lager-String (Welt-Belief)
        lcoe_30y_mean_ct_kwh: 30-Jahres-Mittel-LCOE 2026-2055
        regret_ct_kwh: Reue als LCOE − min(LCOE) in dieser Welt (≥ 0)
        is_minimum: True, wenn diese Politik in dieser Welt minimal-LCOE hat
    """

    policy: PolicyChoice
    world: str
    lcoe_30y_mean_ct_kwh: float
    regret_ct_kwh: float
    is_minimum: bool


def compute_regret_matrix() -> list[RegretMatrixCell]:
    """Berechnet die vollständige Savage-Minimax-Reue-Matrix.

    Schritte:
    1. Für jede (Politik, Welt)-Kombination: Rolling-30-J-LCOE 2026-2055.
    2. Pro Welt-Sicht: minimum LCOE über alle Politiken bestimmen.
    3. Pro Zelle: Reue = LCOE − Welt-Minimum (≥ 0 garantiert).

    Rückgabe: Liste von 16 Zellen (4 Welten × 4 Politiken).
    """
    # Schritt 1: alle LCOE-Werte
    lcoes: dict[tuple[PolicyChoice, str], float] = {}
    for world in CAMP_WORLDS:
        for policy in PolicyChoice:
            lcoes[(policy, world)] = rolling_lcoe(policy.value, 2026, camp=world)

    # Schritt 2 + 3: pro Welt Min finden, Reue berechnen
    cells: list[RegretMatrixCell] = []
    for world in CAMP_WORLDS:
        world_min = min(lcoes[(p, world)] for p in PolicyChoice)
        world_argmin = next(p for p in PolicyChoice if lcoes[(p, world)] == world_min)
        for policy in PolicyChoice:
            lcoe = lcoes[(policy, world)]
            regret = lcoe - world_min
            cells.append(
                RegretMatrixCell(
                    policy=policy,
                    world=world,
                    lcoe_30y_mean_ct_kwh=lcoe,
                    regret_ct_kwh=regret,
                    is_minimum=(policy is world_argmin),
                )
            )
    return cells


def min_per_world(matrix: list[RegretMatrixCell]) -> dict[str, RegretMatrixCell]:
    """Welt → minimal-LCOE-Zelle (= günstigste Politik in dieser Welt)."""
    out: dict[str, RegretMatrixCell] = {}
    for world in CAMP_WORLDS:
        world_cells = [c for c in matrix if c.world == world]
        out[world] = min(world_cells, key=lambda c: c.lcoe_30y_mean_ct_kwh)
    return out


def minimax_regret_per_policy(matrix: list[RegretMatrixCell]) -> dict[PolicyChoice, float]:
    """Politik → maximale Reue über alle Welten (Savage-Minimax-Kriterium).

    Die Politik mit minimaler max-Reue ist die »Minimax-Regret-Wahl«:
    sie minimiert das schlimmstmögliche Bedauern über alle Welt-Sichten.
    """
    out: dict[PolicyChoice, float] = {}
    for policy in PolicyChoice:
        policy_cells = [c for c in matrix if c.policy is policy]
        out[policy] = max(c.regret_ct_kwh for c in policy_cells)
    return out


def damage_bn_eur(regret_ct_per_kwh: float) -> float:
    """Reue-Schaden in Mrd EUR über 30 Jahre.

    Skalierung: Reue × 30 J × 858 TWh / 100 (Cent-zu-Euro-Faktor).
    """
    return regret_ct_per_kwh * YEARS * DEMAND_TWH / 100
