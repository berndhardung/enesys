"""Visual Style Master — Farbpalette, Schriften, Lookups.

Single Source of Truth für Farben und Schriften. Matplotlib-Adapter lebt
in `viz.matplotlib_style`, Plotly-Adapter in `viz.plotly_style`, Marken-
Elemente (Wortmarke, Footer) in `viz.brand`.

Hintergrund-Konvention: ``COLORS["bg"]`` ist weiß als Default für
analytische Charts. ``COLORS["bg_paper"]`` ist warm-beige für Pauspapier-
Look (optionale Alternativ-Schicht). ``COLORS["bg_panel"]`` ist eine
leicht dunklere Variante für Korridor-Bänder.

Lager-Achse läuft Grün (EE) → Grau (neutral) → Rotorange (Atom), Pfad-
Familien teilen sich die Lager-Farbe als Grundton.

Drift-Test in tests/architecture/ prüft, dass das ausgelagerte
palette.json mit dieser Datei synchron ist.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Farbpalette — Single Source of Truth
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    # --- Lager-Achse (drei Welten) ----------------------------------------
    # Wichtigste Regel: KKW-Pfade sind NICHT rot — Rot ist reserviert für
    # Reue/Defizit/Warnung. KKW läuft in einer Orange-Braun-Skala
    # (lager-symmetrischer, weil Rot auf Pfade automatisch wertend wirkt).
    "lager_ee": "#4FA77B",  # EE-Lager — gedecktes Grün
    "lager_neutral": "#8B8B8B",  # Empirisches Mittel — trockenes Grau
    "lager_atom": "#C96A5B",  # Atom-Lager — gedecktes Ziegelrot
    "lager_bestand": "#7A6850",  # BESTAND-Lager — warmes Braun
    # --- Pfad-Familien (EE-Grün-Skala) -------------------------------------
    "pfad_ee_gas": "#46B38A",  # EE-GAS — sattes Grün
    "pfad_ee_h2": "#2E8F68",  # EE-H2 — dunkleres Grün
    # --- Pfad-Familien (KKW: Orange-Braun, NICHT rot) ----------------------
    "pfad_kkw_gas": "#D89A3B",  # KKW-GAS — warmes Orange
    "pfad_kkw_h2": "#8E5B2A",  # KKW-H2 — dunkles Braun
    # --- Referenz-Pfade (passive Drift / Bestandserhalt) -------------------
    "pfad_bestand": "#7A6850",  # BESTAND-Pfad — warmes Braun
    "pfad_weiter_so": "#8F8F8F",  # WEITER-SO — mittel-grau
    # --- Hintergrund + Achsen ----------------------------------------------
    # bg: weiß als Default für analytische Charts. Pauspapier-Look
    # (warm-beige) lebt als bg_paper für optionale Alternativ-Schichten.
    "bg": "#FFFFFF",  # Default — weiß
    "bg_paper": "#F5F3EE",  # Pauspapier-Look — warm-beige Alternative
    "bg_panel": "#F0EAD6",  # Korridor-Band — leicht dunkler warmes Beige
    "grid": "#E4E0D8",  # Grid Paper — deutlich sichtbar, nicht dominant
    "edge": "#404040",  # Marker-/Balken-Konturen
    "text_dark": "#222222",  # Haupttext (nie reines #000000)
    "text_muted": "#666666",  # Achsen-Zahlen, Subtitel, Methodik-Hinweise
    # --- Warn-/Pointen-Farben (NUR diese sind rot/grün-saturiert) ----------
    "accent_red": "#A63D2F",  # Reue/Defizit — exklusiv für Warnsignal
    "accent_green": "#2E6E4A",  # Robustheit / leere Reue-Welt
    "accent_uncertainty": "#D8C9A6",  # Unsicherheitsband / Spannweite
    "accent_navy": "#1F3D5C",  # Hyperlinks, Verweise
}


# Lager → Marker-Form-Mapping (Form-Codierung ZUSÄTZLICH zu Farbe).
# Rettet Smartphone-Lesbarkeit, Graustufen-Druck und Farbsehschwächen.
_LAGER_MARKER_MAP = {
    "ee_optimistic": "o",  # EE: gefüllter Kreis
    "ee_lager": "o",
    "EE-Lager": "o",
    "neutral_default": "s",  # Neutral: Quadrat
    "neutral": "s",
    "Neutral": "s",
    "atom_optimistic": "^",  # Atom: Dreieck
    "atom_lager": "^",
    "Atom-Lager": "^",
    "bestand_optimistic": "D",  # Bestand: Raute
    "BESTAND-Lager": "D",
}


# Pfad-Name → Farbschlüssel-Mapping (für robusten get_path_color-Lookup)
_PFAD_COLOR_MAP = {
    "EE-GAS": "pfad_ee_gas",
    "EE-H2": "pfad_ee_h2",
    "KKW-GAS": "pfad_kkw_gas",
    "KKW-H2": "pfad_kkw_h2",
    "BESTAND": "pfad_bestand",
    "WEITER-SO": "pfad_weiter_so",
}

# Lager-Name → Farbschlüssel-Mapping
_LAGER_COLOR_MAP = {
    "ee_optimistic": "lager_ee",
    "ee_lager": "lager_ee",
    "EE-Lager": "lager_ee",
    "neutral_default": "lager_neutral",
    "neutral": "lager_neutral",
    "Neutral": "lager_neutral",
    "atom_optimistic": "lager_atom",
    "atom_lager": "lager_atom",
    "Atom-Lager": "lager_atom",
    "bestand_optimistic": "lager_bestand",
    "bestand_lager": "lager_bestand",
    "BESTAND-Lager": "lager_bestand",
}


# ---------------------------------------------------------------------------
# Chart-spezifische Farb- und Label-Mappings
# ---------------------------------------------------------------------------
#
# Wiederverwendbare Pfad- und Schicht-Konstanten für Chart-Generatoren.
# Single-Source: alle Farben werden aus COLORS abgeleitet, keine eigenen
# Hex-Werte.

# Pfad-ID → Hex-Farbe (für plot()-Aufrufe ohne get_path_color-Lookup).
PATH_COLORS: dict[str, str] = {
    "weiterso": COLORS["pfad_weiter_so"],
    "ee_gas": COLORS["pfad_ee_gas"],
    "ee_h2": COLORS["pfad_ee_h2"],
    "bestand": COLORS["pfad_bestand"],
    "kkw_gas": COLORS["pfad_kkw_gas"],
    "kkw_h2": COLORS["pfad_kkw_h2"],
}

# Pfad-ID → Anzeige-Label (für Legenden, Achsen-Beschriftung).
PATH_LABELS: dict[str, str] = {
    "weiterso": "WEITER-SO",
    "ee_gas": "EE-GAS",
    "ee_h2": "EE-H2",
    "bestand": "BESTAND",
    "kkw_gas": "KKW-GAS",
    "kkw_h2": "KKW-H2",
}

# Pfad-ID → matplotlib-Linien-Stil (für Graustufen-Sicherheit).
# Zweite Codierungs-Dimension neben Farbe: in Graustufen-Render bleibt
# jeder Pfad anhand der Linien-Form unterscheidbar. Plus dritte Dimension
# über Endpunkt-Marker (siehe PATH_END_MARKERS).
PATH_LINESTYLES: dict[str, Any] = {
    "weiterso": (0, (1, 1)),  # gepunktet
    "ee_gas": "solid",  # durchgezogen (Hauptpfad)
    "ee_h2": (0, (5, 2)),  # langgestrichelt
    "bestand": (0, (3, 1, 1, 1)),  # strich-punkt
    "kkw_gas": (0, (5, 5)),  # gleichmäßig gestrichelt
    "kkw_h2": (0, (1, 2)),  # eng-gepunktet
}

# Pfad-ID → Endpunkt-Marker (matplotlib marker string).
# Dritte Codierungs-Dimension: am Endpunkt jeder Trajektorie sitzt ein
# pfad-spezifischer Marker, der auch ohne Farbe und Linien-Stil noch
# erkennen lässt, welcher Pfad das ist.
PATH_END_MARKERS: dict[str, str] = {
    "weiterso": "D",  # Raute
    "ee_gas": "o",  # Kreis gefüllt
    "ee_h2": "o",  # Kreis offen (durch markerfacecolor='white' gesteuert)
    "bestand": "s",  # Quadrat
    "kkw_gas": "^",  # Dreieck gefüllt
    "kkw_h2": "^",  # Dreieck offen (durch markerfacecolor='white' gesteuert)
}

# Welche Pfade „offene" (face=white) Marker bekommen — semantisch das
# H2-/Sekundär-Pendant zum jeweiligen Lager.
PATH_OPEN_MARKERS: frozenset[str] = frozenset({"ee_h2", "kkw_h2"})

# Lager-Farben als Direkt-Aliase (für Chart-Code, der COLORS[...] zu
# umständlich findet).
COLOR_EE: str = COLORS["lager_ee"]
COLOR_STATUSQUO: str = COLORS["lager_neutral"]
COLOR_ATOM: str = COLORS["lager_atom"]


# Mengen-Bilanz-Schicht-Farben + Labels — zentrale Pflege für alle
# Hochlauf-Charts (Mix + Stress). Stack-Reihenfolge (unten → oben):
# Grundlast-Sockel (Kohle, KKW) → weitere Grundlast (Wasser, Bio) →
# EE-fluktuierend → Demand-Shifter → Importe → Bridge-Backup →
# Stress-Aggregat.
MENGENBILANZ_SCHICHT_COLORS: dict[str, str] = {
    # Grundlast-Sockel
    "kohle": "#1A1A1A",
    "kkw": "#7A4A1F",
    # Weitere Grundlast
    "hydro": "#6BB6E0",
    "biomasse": "#5C9C5A",
    # EE-fluktuierend
    "pv": "#FFC93C",
    "wind_on": "#4ABF87",
    "wind_off": "#2A7B5A",
    # Demand-Shifter
    "battery": "#A06CB4",
    "dsm": "#CE93D8",
    # Importe (Strom-Markt)
    "importe": "#9B7BBF",
    # Bridge-Backup
    "erdgas_bestand": "#D4B883",
    "gas_h2ready_erdgas": "#A87F3D",
    "gas_h2ready_h2": "#1F4E8C",
    # Notfall-Reserve (Stufe 4 BNetzA-Engpass-Konzept)
    "strategische_reserve": "#8B0000",
    # Stress-spezifische Aggregat-Schicht
    "ee_supply": "#FFC93C",
}

MENGENBILANZ_SCHICHT_LABELS: dict[str, str] = {
    "kohle": "Kohle",
    "kkw": "Kernkraft",
    "hydro": "Wasserkraft",
    "biomasse": "Biomasse",
    "pv": "PV",
    "wind_on": "Wind onshore",
    "wind_off": "Wind offshore",
    "battery": "Batterie",
    "dsm": "DSM",
    "importe": "Importe",
    "erdgas_bestand": "Erdgas-Bestand (Bridge)",
    "gas_h2ready_erdgas": "Gas-h2ready (auf Erdgas)",
    "gas_h2ready_h2": "Gas-h2ready (auf H2)",
    "strategische_reserve": "Strategische Reserve (§13b)",
    "ee_supply": "EE-Supply (Stunden-Mittel)",
}

# Schicht-Farben für das Vier-Schichten-Stack-Diagramm.
LAYER_COLORS: dict[str, str] = {
    "Erzeugung": "#3B7B6B",
    "Speicher": "#E8A93B",
    "Netz": "#7A8AA0",
    "Stabilität": "#9C5A8A",
    "CO₂ & System": "#C45D3F",
}


# ---------------------------------------------------------------------------
# Schriften
# ---------------------------------------------------------------------------

FONTS: dict[str, str | int] = {
    # Druck-Familie (für SVG-Export, harmoniert mit Pagella-Serife)
    "main_serif": "DejaVu Serif",  # Fallback, falls TeX Gyre Pagella nicht im System
    # Sans-Familie für Digital/PNG
    # Empfohlen: IBM Plex Sans (Werkstatt-/Labornotizbuch-Charakter, hervorragende
    # Zahlen). Falls nicht installiert: DejaVu Sans als Fallback. Matplotlib
    # nimmt den ersten verfügbaren aus der Liste.
    "main_sans": "IBM Plex Sans",
    "mono": "IBM Plex Mono",
    # Größen (Smartphone-/OpenGraph-tauglich, Hierarchie aus externen Reviews)
    "size_title": 18,
    "size_subtitle": 12,
    "size_panel_title": 14,
    "size_axis_label": 11,
    "size_tick": 10,
    "size_legend": 10,
    "size_annotation": 9,
}


# ---------------------------------------------------------------------------
# Lookup-Helfer
# ---------------------------------------------------------------------------


def get_camp_color(camp: str) -> str:
    """Liefert die Hex-Farbe für einen Lager-Namen.

    Akzeptiert sowohl Code-Namen (ee_optimistic, atom_optimistic, ...) als auch
    deutsche Anzeige-Namen (EE-Lager, Atom-Lager, Neutral, ...).
    """
    key = _LAGER_COLOR_MAP.get(camp)
    if key is None:
        raise KeyError(f"Unbekanntes Lager '{camp}'. Erlaubt: {sorted(_LAGER_COLOR_MAP)}")
    return COLORS[key]


def get_path_color(path: str) -> str:
    """Liefert die Hex-Farbe für einen Pfad-Namen (z.B. 'EE-GAS', 'KKW-H2')."""
    key = _PFAD_COLOR_MAP.get(path)
    if key is None:
        raise KeyError(f"Unbekannter Pfad '{path}'. Erlaubt: {sorted(_PFAD_COLOR_MAP)}")
    return COLORS[key]


def get_camp_marker(camp: str) -> str:
    """Liefert das Matplotlib-Marker-Symbol für ein Lager.

    Form-Codierung zusätzlich zur Farbe — wichtig für Graustufen-Druck,
    Farbsehschwäche, Smartphone-Lesbarkeit.
    """
    marker = _LAGER_MARKER_MAP.get(camp)
    if marker is None:
        raise KeyError(f"Unbekanntes Lager '{camp}'. Erlaubt: {sorted(_LAGER_MARKER_MAP)}")
    return marker


# ---------------------------------------------------------------------------
# Matplotlib- und Plotly-Adapter — Re-Exports für Backward-Compatibility
# ---------------------------------------------------------------------------
#
# Die eigentlichen Implementierungen leben in viz.matplotlib_style und
# viz.plotly_style. Diese Re-Exports erhalten den alten Import-Pfad
# `from enesys.viz.theme import apply_mpl_theme` für Bestandskonsumenten.
# Neue Konsumenten sollen aus den Submodulen direkt importieren.


def apply_mpl_theme() -> None:
    """Re-Export aus viz.matplotlib_style (Backward-Compat)."""
    from enesys.viz.matplotlib_style import apply_mpl_theme as _impl

    _impl()


def plotly_template() -> dict[str, Any]:
    """Re-Export aus viz.plotly_style (Backward-Compat)."""
    from enesys.viz.plotly_style import plotly_template as _impl

    return _impl()


# ---------------------------------------------------------------------------
# JSON-Export für Web-Frontend (palette.json)
# ---------------------------------------------------------------------------


def to_palette_dict() -> dict[str, Any]:
    """Liefert ein JSON-serialisierbares Dict für Web-Konsumenten.

    Struktur: flach für direkten JS-Zugriff (PALETTE.lager_ee, PALETTE.pfad_ee_gas).
    Zusätzlich pfad_colors-Map mit Anzeige-Namen für PATH_COLORS-Style in app.js.
    """
    return {
        "colors": dict(COLORS),
        "pfad_colors": {path: COLORS[key] for path, key in _PFAD_COLOR_MAP.items()},
        "lager_colors": {
            camp: COLORS[key]
            for camp, key in _LAGER_COLOR_MAP.items()
            if camp in ("EE-Lager", "Neutral", "Atom-Lager", "BESTAND-Lager")
        },
        "fonts": {k: v for k, v in FONTS.items() if isinstance(v, str)},
        "sizes": {k: v for k, v in FONTS.items() if isinstance(v, int)},
    }
