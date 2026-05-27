"""Multikriterien-Bewertung der vier aktiven klimaneutralen Pfade.

Hintergrund: eine acht-Kriterien-Tabelle (siehe `docs/SOURCES.md`)
bewertet die Pfade qualitativ, lässt aber die Gewichtung offen. Damit
ist das Aggregations-Ergebnis ohne expliziten Gewichtungs-Vektor
unterspezifiziert — unterschiedliche Lager-Prioritäten können zu
unterschiedlichen Rankings führen.

Dieses Modul macht die Gewichtung **explizit und reproduzierbar**:

1. Die acht Kriterien-Bewertungen pro Pfad (1..3, qualitativ) stehen
   in einer einzigen Source-of-Truth (`CRITERIA_SCORES`).
2. Vier Default-Gewichtungs-Profile sind hinterlegt:
   - `default` — Standard-Gewichtung mit Realisierung doppelt.
   - `ee_lager` — EE-fokussiert (Optionalität + Lock-in stark gewichtet).
   - `kkw_lager` — KKW-fokussiert (Versorgungssicherheit + Geopolitik stark).
   - `bestand_pragmatisch` — kostenfokussiert (Forward-Cost + Realisierung stark).
3. `score_pfad(profil, pfad)` liefert den gewichteten Gesamtscore.
4. `ranking(profil)` liefert die Pfad-Reihenfolge des Profils.

**Zentrale inhaltliche Beobachtung:**

Mit den Default-Bewertungen gewinnt EE-GAS in **allen vier**
Profilen — auch im `kkw_lager`-Profil. Im KKW-Lager-Profil ist der
Vorsprung knapp (2,48 vs. 2,15 für KKW-GAS), aber er hält. Um zu
KKW-GAS als Sieger zu kommen, müssen die Kriterien-Bewertungen
selbst verändert werden, nicht nur die Gewichte. Die Aussage ist
gegenüber reiner Gewichtungs-Variation **robust**.

**Wichtig — Was das Modul NICHT tut:**

Das Modul berechnet *keine* ct/kWh-Werte. Forward-Cost, CO₂ etc. werden
qualitativ auf 1..3 abgebildet. Die quantitativen Werte stammen aus
`core/path_model.py` und `core/path_sensitivity.py`. Die Multikriterien-
Schicht ist eine Aggregations-Schicht über diese quantitativen Modelle.
"""

from __future__ import annotations

from dataclasses import dataclass

# =============================================================================
# Acht Kriterien — Source-of-Truth der Multikriterien-Bewertung
# =============================================================================

CRITERIA: tuple[str, ...] = (
    "forward_cost_2055",
    "co2_restemission_2055",
    "versorgungssicherheit_steady_state",
    "pfad_optionalitaet",
    "geopolitische_zukunftsfestigkeit",
    "realisierungs_wahrscheinlichkeit_2042",
    "investitions_lock_in_nach_2055",
    "stranded_asset_risiko",
)

CRITERIA_LABELS: dict[str, str] = {
    "forward_cost_2055": "Forward-Cost 2055",
    "co2_restemission_2055": "CO₂-Restemission 2055",
    "versorgungssicherheit_steady_state": "Versorgungssicherheit Steady-State",
    "pfad_optionalitaet": "Pfad-Optionalität (Revidierbarkeit)",
    "geopolitische_zukunftsfestigkeit": "Geopolitische Zukunftsfestigkeit",
    "realisierungs_wahrscheinlichkeit_2042": "Realisierungs-Wahrscheinlichkeit bis 2042",
    "investitions_lock_in_nach_2055": "Investitions-Lock-in nach 2055",
    "stranded_asset_risiko": "Stranded-Asset-Risiko 2042-2055",
}

PATHS: tuple[str, ...] = ("EE-GAS", "EE-H2", "KKW-GAS", "KKW-H2")

# =============================================================================
# Bewertungen pro (Pfad, Kriterium) — 3 stark / 2 mittel / 1 schwach
# =============================================================================
# Bewertungs-Logik:
#   3 = Pfad ist in diesem Kriterium klar im Vorteil
#   2 = mittel / akzeptabel
#   1 = klare Schwäche
#
# Halb-Stufen (2,5) bilden Tabelleneinträge "mittel-niedrig" und
# "mittel-hoch" ab, wo eine reine 1/2/3-Skala zu grob wäre.
#
# Hinweis zur Subjektivität dieser Matrix
# ---------------------------------------
# Mehrere Kriterien (Versorgungssicherheit-Steady-State, geopolitische
# Zukunftsfestigkeit, Stranded-Asset-Risiko, Realisierungs-Wahrscheinlich-
# keit, Pfad-Optionalität) sind nicht direkt quantifizierbar; die hier
# hinterlegten 1..3-Bewertungen sind eine Modell-Setzung mit Begründung
# per Inline-Kommentar, keine empirische Messung. Nur
# ``forward_cost_2055`` und ``co2_restemission_2055`` haben ein direktes
# numerisches Pendant in ``compute_path``.
#
# Wer einer Bewertung widerspricht, kann CRITERIA_SCORES vor dem Aufruf
# ``score_path`` / ``ranking`` / ``recommendation`` lokal überschreiben
# (dict-Update) und so die Sensitivität gegenüber alternativen
# Einschätzungen prüfen. Die Multikriterien-Schicht ist als Aggregations-
# Werkzeug konzipiert, nicht als kanonische Wahrheit.

CRITERIA_SCORES: dict[str, dict[str, float]] = {
    "EE-GAS": {
        "forward_cost_2055": 3.0,  # günstigster aktiver Pfad
        "co2_restemission_2055": 2.0,  # Bridge-Erdgas-Rest
        "versorgungssicherheit_steady_state": 2.0,  # Backup vorhanden, Saisonspeicher offen
        "pfad_optionalitaet": 3.0,  # Erdgas-Backup als Rückfall
        "geopolitische_zukunftsfestigkeit": 2.5,  # 8% Backup, gepuffert; Komponenten mittel
        "realisierungs_wahrscheinlichkeit_2042": 3.0,  # Technologie reif
        "investitions_lock_in_nach_2055": 3.0,  # 20-30 J Anlagen-Lebensdauer
        "stranded_asset_risiko": 3.0,  # niedrig (H2-ready Backups)
    },
    "EE-H2": {
        "forward_cost_2055": 2.0,
        "co2_restemission_2055": 3.0,  # praktisch null
        "versorgungssicherheit_steady_state": 1.0,  # H2-Saison-Speicher kritisch
        "pfad_optionalitaet": 2.0,  # kein fossiler Rückfall
        "geopolitische_zukunftsfestigkeit": 1.0,  # H2-Import dauerhaft
        "realisierungs_wahrscheinlichkeit_2042": 2.0,  # H2-Hochlauf-Wette
        "investitions_lock_in_nach_2055": 3.0,  # flexibel + H2
        "stranded_asset_risiko": 3.0,  # niedrig
    },
    "KKW-GAS": {
        "forward_cost_2055": 2.0,
        "co2_restemission_2055": 2.0,  # Backup-Rest
        "versorgungssicherheit_steady_state": 3.0,  # Atom-Grundlast
        "pfad_optionalitaet": 1.0,  # 60J KKW-Lock-in
        "geopolitische_zukunftsfestigkeit": 2.0,  # Uran gut, KKW-Hersteller-Konzentration
        "realisierungs_wahrscheinlichkeit_2042": 1.5,  # niedrig-mittel (Bauzeit 13-17 J)
        "investitions_lock_in_nach_2055": 1.0,  # strukturell (60 J)
        "stranded_asset_risiko": 2.0,  # mittel (KKW-Bauzeit, Endlager)
    },
    "KKW-H2": {
        "forward_cost_2055": 1.0,  # ~20,8 ct/kWh, klar teuerster Pfad
        "co2_restemission_2055": 3.0,  # H2-Backup
        "versorgungssicherheit_steady_state": 2.0,  # Atom + H2-Risiko
        "pfad_optionalitaet": 1.0,  # Lock-in plus H2-Bindung
        "geopolitische_zukunftsfestigkeit": 1.5,  # Uran gut + H2 niedrig
        "realisierungs_wahrscheinlichkeit_2042": 1.0,  # KKW-Bauzeit + H2-Wette gleichzeitig
        "investitions_lock_in_nach_2055": 1.0,  # KKW-Plateau + H2-Lieferketten
        "stranded_asset_risiko": 1.5,  # mittel-hoch
    },
}


# =============================================================================
# Gewichtungs-Profile
# =============================================================================
# Gewichtungen müssen sich pro Profil auf 100 % summieren.
# Die `default`-Gewichtung folgt der Standard-Empfehlungs-Logik:
# Realisierungs-Wahrscheinlichkeit ist das schwerwiegendste Kriterium —
# ein nicht realisierbarer Pfad ist wertlos, egal wie gut die anderen
# Kriterien aussehen. Daher 20 %. Forward-Cost, CO₂, Optionalität gleich
# bei 15 %. Andere bei 10 %, Stranded-Asset bei 5 %.
#
# Die drei Lager-Profile zeigen, wie die Empfehlung mit der Gewichtung
# variiert. Sie sind nicht "richtig" oder "falsch" — sie sind explizit
# unterschiedliche Werteurteile, sichtbar gemacht.

DEFAULT_WEIGHTS: dict[str, float] = {
    "forward_cost_2055": 0.15,
    "co2_restemission_2055": 0.15,
    "versorgungssicherheit_steady_state": 0.10,
    "pfad_optionalitaet": 0.15,
    "geopolitische_zukunftsfestigkeit": 0.10,
    "realisierungs_wahrscheinlichkeit_2042": 0.20,  # Doppelt gewichtet: Frist-Härte 2042 zentral
    "investitions_lock_in_nach_2055": 0.10,
    "stranded_asset_risiko": 0.05,
}

EE_CAMP_WEIGHTS: dict[str, float] = {
    "forward_cost_2055": 0.10,
    "co2_restemission_2055": 0.20,  # Klimaneutralität priorisiert
    "versorgungssicherheit_steady_state": 0.05,
    "pfad_optionalitaet": 0.20,  # Optionalität priorisiert
    "geopolitische_zukunftsfestigkeit": 0.05,
    "realisierungs_wahrscheinlichkeit_2042": 0.15,
    "investitions_lock_in_nach_2055": 0.20,  # Lock-in-Vermeidung
    "stranded_asset_risiko": 0.05,
}

KKW_CAMP_WEIGHTS: dict[str, float] = {
    "forward_cost_2055": 0.10,
    "co2_restemission_2055": 0.10,
    "versorgungssicherheit_steady_state": 0.30,  # Zentrale KKW-These
    "pfad_optionalitaet": 0.05,  # weniger relevant
    "geopolitische_zukunftsfestigkeit": 0.25,  # Brennstoff-Souveränität
    "realisierungs_wahrscheinlichkeit_2042": 0.10,
    "investitions_lock_in_nach_2055": 0.05,
    "stranded_asset_risiko": 0.05,
}

BESTAND_PRAGMATIC_WEIGHTS: dict[str, float] = {
    "forward_cost_2055": 0.30,  # Kosten zuerst
    "co2_restemission_2055": 0.10,
    "versorgungssicherheit_steady_state": 0.15,
    "pfad_optionalitaet": 0.10,
    "geopolitische_zukunftsfestigkeit": 0.10,
    "realisierungs_wahrscheinlichkeit_2042": 0.20,  # Was real schaffbar ist
    "investitions_lock_in_nach_2055": 0.025,
    "stranded_asset_risiko": 0.025,
}

PROFILES: dict[str, dict[str, float]] = {
    "default": DEFAULT_WEIGHTS,
    "ee_lager": EE_CAMP_WEIGHTS,
    "kkw_lager": KKW_CAMP_WEIGHTS,
    "bestand_pragmatisch": BESTAND_PRAGMATIC_WEIGHTS,
}


# =============================================================================
# Validierung — Setup-Checks
# =============================================================================


def _validate_weights(profile_name: str, weights: dict[str, float]) -> None:
    """Sicherstellen, dass die Gewichtung sich auf 1.0 summiert.

    Toleranz: 1e-6 (Float-Rundung).
    """
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Profil {profile_name!r}: Gewichtungs-Summe {total} weicht von 1.0 ab. "
            f"Bitte korrigieren — sonst sind Scores nicht vergleichbar."
        )
    missing = set(CRITERIA) - set(weights.keys())
    if missing:
        raise ValueError(f"Profil {profile_name!r}: Fehlende Kriterien {missing}.")
    extra = set(weights.keys()) - set(CRITERIA)
    if extra:
        raise ValueError(f"Profil {profile_name!r}: Unbekannte Kriterien {extra}.")


# Eager-Validierung beim Modul-Import — Fehler werden früh sichtbar
for _name, _gew in PROFILES.items():
    _validate_weights(_name, _gew)


# =============================================================================
# Public API
# =============================================================================


@dataclass(frozen=True)
class PathScore:
    """Ein Score-Eintrag für einen Pfad in einem Gewichtungs-Profil."""

    path: str
    profile: str
    score: float
    rank: int


def score_path(profile: str, path: str) -> float:
    """Berechnet den gewichteten Gesamtscore für einen Pfad in einem Profil.

    Parameters
    ----------
    profile : str
        Name eines Gewichtungs-Profils — einer von ``PROFILES.keys()``.
    path : str
        Pfad-Name — einer von ``PATHS``.

    Returns
    -------
    float
        Gewichteter Score, im Bereich [1.0, 3.0]. Höher = besser.
    """
    if profile not in PROFILES:
        raise KeyError(f"Unbekanntes Profil {profile!r}. Verfügbar: {list(PROFILES)}")
    if path not in CRITERIA_SCORES:
        raise KeyError(f"Unbekannter Pfad {path!r}. Verfügbar: {list(CRITERIA_SCORES)}")
    scores = CRITERIA_SCORES[path]
    weights = PROFILES[profile]
    return sum(scores[k] * weights[k] for k in CRITERIA)


def ranking(profile: str) -> list[PathScore]:
    """Liefert das Ranking aller Pfade für ein Profil — bester Pfad zuerst.

    Returns
    -------
    list[PathScore]
        Sortiert nach absteigendem Score. Rang 1 = bester Pfad.
    """
    if profile not in PROFILES:
        raise KeyError(f"Unbekanntes Profil {profile!r}. Verfügbar: {list(PROFILES)}")
    pairs = sorted(
        ((p, score_path(profile, p)) for p in CRITERIA_SCORES),
        key=lambda x: x[1],
        reverse=True,
    )
    return [
        PathScore(path=p, profile=profile, score=round(s, 4), rank=i + 1)
        for i, (p, s) in enumerate(pairs)
    ]


def recommendation(profile: str) -> str:
    """Liefert den Top-1-Pfad für ein Profil."""
    return ranking(profile)[0].path


def all_rankings() -> dict[str, list[PathScore]]:
    """Ranking pro Profil. Praktisch für Tabellen-Generierung."""
    return {name: ranking(name) for name in PROFILES}


def recommendation_matrix() -> dict[str, str]:
    """Pro Profil den Top-Pfad. Praktisch für Übersichts-Tabellen."""
    return {name: recommendation(name) for name in PROFILES}
