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

from .inventories.tech_inventory import override_kkw_epr_startjahr
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


# ---------------------------------------------------------------------------
# Robustheits-Check: Minimax-Reue als Funktion des KKW-Startjahrs.
#
# Die kanonischen Lager-Startjahre (atom_optimistic 2036, neutral_default
# / bestand 2046, ee_optimistic 2050) folgen aus
# ``KKW_EPR_APPROVAL_YEAR`` plus sqrt-Streckung der Bauzeit je
# Lager-Realisierungsgrad — sie sind also vom Realgrad-Belief abhängig.
# Eine separate Frage ist: wie verschiebt sich die Minimax-Reue, wenn
# das KKW-Startjahr unabhängig vom Lager-Realgrad direkt variiert wird?
# ``nuclear_start_year_regret_analysis`` verwendet den Kontext-Manager
# ``override_kkw_epr_startjahr`` aus ``tech_inventory``, der das
# Startjahr für jedes Lager einheitlich auf den Kandidaten-Wert X setzt
# und nach dem ``with``-Block den Original-Zustand wiederherstellt.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NuclearStartYearRegretPoint:
    """Ein Punkt aus dem KKW-Startjahr-Robustheits-Check.

    Felder:
        nuclear_start_year: angenommenes Startjahr (für alle Lager
            identisch gesetzt)
        max_regret_per_policy: max-Reue pro Politik über die vier Welten
        minimax_winner: Politik mit minimaler max-Reue (regret-optimal)
        kkw_gas_regret_ee_world: Reue von KKW-GAS in der ee_optimistic-
            Welt (häufig der bindende Term für KKW-Politik)
    """

    nuclear_start_year: int
    max_regret_per_policy: dict[PolicyChoice, float]
    minimax_winner: PolicyChoice
    kkw_gas_regret_ee_world: float


def nuclear_start_year_regret_analysis(
    nuclear_start_years: range | list[int] | tuple[int, ...],
) -> list[NuclearStartYearRegretPoint]:
    """Reue-Matrix als Funktion des KKW-Startjahrs.

    Für jeden Kandidaten wird ``tech_inventory.kkw_epr_startjahr`` über
    ``override_kkw_epr_startjahr`` so gesetzt, dass *alle* Lager
    dieses Startjahr liefern (das Lager-Heterogen des
    KKW-Realisierungsgrads wird damit ausgeschaltet — die Funktion
    beantwortet die hypothetische Frage »wenn KKW in jeder Welt
    verlässlich zu Jahr X verfügbar wäre …«).

    Args:
        nuclear_start_years: Iterable über Startjahr-Kandidaten
            (z. B. ``range(2028, 2056, 2)``).

    Returns:
        Liste von ``NuclearStartYearRegretPoint`` in Eingabe-Reihenfolge.
    """
    points: list[NuclearStartYearRegretPoint] = []
    for year in nuclear_start_years:
        with override_kkw_epr_startjahr(int(year)):
            matrix = compute_regret_matrix()
            max_regret = minimax_regret_per_policy(matrix)
            winner = min(max_regret, key=lambda p: max_regret[p])
            kkw_gas_in_ee_world = next(
                c.regret_ct_kwh
                for c in matrix
                if c.policy is PolicyChoice.KKW_GAS and c.world == "ee_optimistic"
            )
            points.append(
                NuclearStartYearRegretPoint(
                    nuclear_start_year=int(year),
                    max_regret_per_policy=dict(max_regret),
                    minimax_winner=winner,
                    kkw_gas_regret_ee_world=kkw_gas_in_ee_world,
                )
            )
    return points


def kkw_regret_crossover_year(
    search_range: range | tuple[int, int] = (2026, 2055),
) -> int | None:
    """Frühestes KKW-Startjahr, ab dem eine KKW-Politik regret-optimal wird.

    Liefert ``None``, wenn KKW-Politik im gesamten Suchbereich nicht
    Minimax-Regret-Sieger wird — das Startjahr ist dann nicht der
    bindende Constraint, und eine frühere KKW-Verfügbarkeit würde die
    Empfehlung nicht kippen.

    Args:
        search_range: ``range`` oder ``(low, high)``-Tupel,
            interpretiert als ``range(low, high + 1)``.

    Returns:
        Frühestes Startjahr, ab dem der Minimax-Sieger eine KKW-Politik
        ist, oder ``None`` falls KKW im Bereich nie gewinnt.
    """
    if isinstance(search_range, tuple):
        lo, hi = search_range
        years = range(lo, hi + 1)
    else:
        years = search_range

    analysis = nuclear_start_year_regret_analysis(years)
    kkw_policies = {PolicyChoice.KKW_GAS, PolicyChoice.KKW_H2}
    for point in analysis:
        if point.minimax_winner in kkw_policies:
            return point.nuclear_start_year
    return None
