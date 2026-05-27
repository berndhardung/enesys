"""Welt-Belief-Tabellen für die drei Realisierungs-Hebel
(NEP-Trassen, KKW-Bau, H₂-Hochlauf).

Mechanik: Politik-Wunsch (aus ``PATH_POLICY``) × Welt-Belief (diese
Tabellen) → effektive Realisierung. Der pessimistischere der beiden
Werte wirkt — **Min-Operator**.

> Die effektive Realisierung ist das Minimum aus dem, was die Politik
> beschließt, und dem, was das Lager realistisch für möglich hält.

Zwei intuitive Lese-Achsen, die beide stimmen:

1. Politik-perspektivisch: ambitionierte Politik (EE-GAS, NEP=0,85)
   wird durch skeptische Welt-Sicht (atom_optimistic) gedeckelt.
2. Welt-perspektivisch: optimistische Welt-Sicht (ee_optimistic) kann
   eine drossel-aktive Politik (BESTAND) nicht überstimmen — Politik
   darf aktiv weniger wollen.

Min statt Multiplikation: Multiplikativ würde in der
bestand × atom-Kombi zur Doppel-Bestrafung führen (0,30 × 0,77 = 0,23)
— methodisch schwer zu verteidigen. Min ist die saubere Variante.

Konsequenz für die Reue-Analyse: im atom_optimistic-Lager (NEP-Welt-
Belief 0,50, KKW-Realgrad 1,00) drosselt der Min-Operator EE-Politik
strukturell — KKW-GAS wird in diesem Lager zum günstigsten Pfad. In
den drei anderen Lagern bleibt EE-GAS Reue-Sieger. Min-Max-Regret
hält die Buch-Empfehlung EE-GAS.
"""

from __future__ import annotations

#: NEP-Realisierungsgrad pro Lager (Welt-Belief).
#:
#: Werte spiegeln die ``CAMP_RANGES["nep_realization_rate"]``-Setzungen
#: aus ``core/camp_ranges.py``: das EE-Lager glaubt an die volle NEP-
#: Realisierung, das Atom-Lager sieht Trassen-Skepsis, das BESTAND-Lager
#: glaubt nicht an den Hochlauf, WEITER-SO an passive Trägheit.
CAMP_NEP_WORLD_BELIEF: dict[str, float] = {
    "neutral_default": 0.65,  # empirischer FOAK-Anker
    "ee_optimistic": 0.85,  # NEP-Soll fast erfüllt, BNetzA-Reformen wirken
    "atom_optimistic": 0.50,  # KKW-Lager-Trassen-Skepsis
    "bestand_optimistic": 0.45,  # BESTAND-Lager glaubt nicht an Hochlauf
    "weiterso_optimistic": 0.30,  # passive Trägheit
}

#: KKW-Realisierungsgrad pro Lager (Welt-Belief).
#:
#: 1,00 lebt nur im atom_optimistic-Lager; neutral_default folgt
#: der westlichen FOAK-Bauzeit-Empirie (HPC ~14a, Flamanville 17a, OL3 18a,
#: Vogtle 14a vs. Plan 12a → ≈0,65). ee_optimistic 0,55 wegen zusätzlicher
#: politischer Hemmnisse in der EE-Welt; bestand_optimistic 0,45 wegen
#: fehlender politischer Unterstützung; weiterso_optimistic identisch.
#:
#: [SRC: Anker 4 Bauzeit-Empirie; EDF-HPC; NAO-HPC-2017;
#: Cour-des-Comptes-Flamanville; Vogtle-Cost-Overruns DOE 2024;
#: Grubler 2010 (Plateau-Serie); MIT Future of Nuclear 2018 (NOAK).]
CAMP_NUCLEAR_WORLD_BELIEF: dict[str, float] = {
    "neutral_default": 0.65,
    "ee_optimistic": 0.55,
    "atom_optimistic": 1.00,
    "bestand_optimistic": 0.45,
    "weiterso_optimistic": 0.45,
}

#: H2-Realisierungsgrad pro Lager (Welt-Belief).
#:
#: Werte folgen ``CAMP_RANGES["h2_storage_lcoe"]``-Logik und der
#: BMWK-Wasserstoff-Strategie-Diskussion: das EE-Lager glaubt an volle
#: H2-Mobilisierung (Inland + Import), das Atom-Lager sieht H2 als
#: knapp/teuer, das BESTAND-Lager fährt aktive H2-Skepsis,
#: WEITER-SO eine passive Markt-Erwartung.
CAMP_H2_WORLD_BELIEF: dict[str, float] = {
    "neutral_default": 0.65,
    "ee_optimistic": 1.00,
    "atom_optimistic": 0.50,
    "bestand_optimistic": 0.30,
    "weiterso_optimistic": 0.40,
}


def effective_realization(
    political_target: float,
    world_belief_by_camp: dict[str, float],
    camp: str,
) -> float:
    """Min-Operator zwischen Pfad-Politik und Lager-Welt-Belief.

    ``political_target`` kommt aus ``PATH_POLICY[pfad].default_policy``
    (Politik-Wunsch). ``world_belief_by_camp[camp]`` aus den drei Tabellen
    oben (Welt-Realisierungs-Erwartung). Der kleinere Wert dominiert:

    - Politik kann aktiv drosseln (BESTAND drückt unter Welt-Belief).
    - Welt kann skeptisch sein (Atom-Lager drosselt EE-Politik).

    Fallback bei unbekanntem Camp: ``neutral_default``-Wert aus der
    jeweiligen Tabelle.
    """
    world_belief = world_belief_by_camp.get(
        camp, world_belief_by_camp.get("neutral_default", political_target)
    )
    return min(political_target, world_belief)


__all__ = [
    "CAMP_NEP_WORLD_BELIEF",
    "CAMP_NUCLEAR_WORLD_BELIEF",
    "CAMP_H2_WORLD_BELIEF",
    "effective_realization",
]
