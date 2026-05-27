"""Strukturelle Mechanik-Tests für das Multikriterien-Bewertungs-Modul.

Sichert ab, dass die vier Gewichtungs-Profile auf 1.0 summieren, alle
Pfade Bewertungen für alle acht Kriterien tragen, Scores im Bereich
[1.0, 3.0] liegen und die Ranking-API vier Einträge mit eindeutigen
Rängen liefert.
"""

from __future__ import annotations

import pytest

from enesys.extensions.multicriteria import (
    CRITERIA,
    CRITERIA_SCORES,
    PATHS,
    PROFILES,
    PathScore,
    all_rankings,
    ranking,
    recommendation,
    recommendation_matrix,
    score_path,
)

# =============================================================================
# Setup-Konsistenz
# =============================================================================


def test_gewichtungs_profile_summieren_auf_eins() -> None:
    """Jedes Gewichtungs-Profil muss sich auf exakt 1.0 summieren."""
    for name, weights in PROFILES.items():
        summe = sum(weights.values())
        assert summe == pytest.approx(1.0, abs=1e-9), (
            f"Profil {name!r}: Gewichtungs-Summe {summe} ≠ 1.0"
        )


def test_all_profiles_have_all_criteria() -> None:
    """Jedes Profil muss Gewichte für alle acht Kriterien haben."""
    for name, weights in PROFILES.items():
        assert set(weights.keys()) == set(CRITERIA), (
            f"Profil {name!r}: fehlende oder zusätzliche Kriterien"
        )


def test_all_paths_evaluated_all_criteria() -> None:
    """Jeder Pfad muss Bewertungen für alle acht Kriterien haben."""
    for path in PATHS:
        assert path in CRITERIA_SCORES, f"Pfad {path!r} fehlt in Bewertung"
        assert set(CRITERIA_SCORES[path].keys()) == set(CRITERIA), (
            f"Pfad {path!r}: Kriterien-Coverage unvollständig"
        )


def test_bewertungen_in_gueltigem_bereich() -> None:
    """Alle Bewertungen müssen im Bereich [1.0, 3.0] liegen."""
    for path, scores in CRITERIA_SCORES.items():
        for krit, wert in scores.items():
            assert 1.0 <= wert <= 3.0, f"Bewertung {path}/{krit} = {wert} außerhalb [1.0, 3.0]"


# =============================================================================
# Score- und Ranking-Funktionen
# =============================================================================


def test_score_in_gueltigem_bereich() -> None:
    """Gewichteter Score muss im Bereich [1.0, 3.0] liegen.

    Da Bewertungen in [1, 3] liegen und Gewichte sich auf 1.0 summieren,
    kann der Score nicht außerhalb dieses Intervalls fallen.
    """
    for profile in PROFILES:
        for path in PATHS:
            s = score_path(profile, path)
            assert 1.0 <= s <= 3.0, f"Score {profile}/{path} = {s} außer [1, 3]"


def test_ranking_provides_all_paths() -> None:
    """Ranking muss genau vier Einträge mit eindeutigen Rängen liefern."""
    for profile in PROFILES:
        rg = ranking(profile)
        assert len(rg) == len(PATHS)
        ranks = [r.rank for r in rg]
        assert ranks == [1, 2, 3, 4], f"Profil {profile}: Ränge {ranks} ≠ [1,2,3,4]"
        paths = {r.path for r in rg}
        assert paths == set(PATHS)


def test_ranking_absteigend_nach_score() -> None:
    """Ranking muss absteigend nach Score sortiert sein."""
    for profile in PROFILES:
        rg = ranking(profile)
        scores = [r.score for r in rg]
        assert scores == sorted(scores, reverse=True), f"Profil {profile}: Ranking nicht absteigend"


def test_ranking_eintraege_sind_pfadscore() -> None:
    """Ranking-Einträge sind PathScore-Instanzen."""
    rg = ranking("default")
    for r in rg:
        assert isinstance(r, PathScore)
        assert r.profile == "default"


def test_recommendation_is_top_path() -> None:
    """`recommendation(profile)` muss dem Top-1-Pfad aus Ranking entsprechen."""
    for profile in PROFILES:
        e = recommendation(profile)
        top = ranking(profile)[0].path
        assert e == top


# =============================================================================
# Helfer-API
# =============================================================================


def test_all_rankings_provides_all_profiles() -> None:
    rg = all_rankings()
    assert set(rg.keys()) == set(PROFILES.keys())
    for _name, scores in rg.items():
        assert len(scores) == len(PATHS)


def test_recommendation_matrix_provides_all_profiles() -> None:
    em = recommendation_matrix()
    assert set(em.keys()) == set(PROFILES.keys())
    for _name, path in em.items():
        assert path in PATHS


# =============================================================================
# Fehlerpfade
# =============================================================================


def test_score_unbekanntes_profil_keyerror() -> None:
    with pytest.raises(KeyError):
        score_path("blubb", "EE-GAS")


def test_score_unbekannter_pfad_keyerror() -> None:
    with pytest.raises(KeyError):
        score_path("default", "FUSION")


def test_ranking_unbekanntes_profil_keyerror() -> None:
    with pytest.raises(KeyError):
        ranking("blubb")
