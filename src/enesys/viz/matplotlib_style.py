"""Matplotlib-Adapter für die Visual-Style-Single-Source.

Setzt `plt.rcParams` konsistent zu COLORS und FONTS aus `viz.theme`. Wird
einmal pro Plot-Skript aufgerufen, vor dem ersten `figure()`. Standard-
Hintergrund ist weiß (Print-/Web-tauglich). Wer einen Pauspapier-Look
braucht, nutzt `COLORS["bg_paper"]` explizit.

Zwei Stil-Varianten:

- ``apply_mpl_theme()`` — Standard-Schriftgrößen aus FONTS, Web/Bildschirm-DPI
- ``apply_print_style()`` — größere Schriften für Print-Druck, ``PRINT_DPI``
  als Speicher-DPI

Print-DPI ist 300 (Print-on-Demand-Standard für Foto-Qualität), Web-DPI ist
150 (schneller Download).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from enesys.viz.theme import COLORS, FONTS

# ---------------------------------------------------------------------------
# Print-Konstanten — orientiert am strengsten Standard (Print-on-Demand 300 DPI)
# ---------------------------------------------------------------------------
#
# Schriftgrößen sind so kalibriert, dass nach Skalierung auf ~16 cm
# Breitsatz ein gut lesbarer Druck herauskommt. Wer das Diagramm separat
# am Bildschirm anschaut, sieht eine etwas größere Schrift als gewohnt —
# beabsichtigt.

PRINT_FONT_SIZE_BASE = 12
PRINT_FONT_SIZE_LABEL = 13
PRINT_FONT_SIZE_TITLE = 15
PRINT_FONT_SIZE_SUPTITLE = 16
PRINT_FONT_SIZE_LEGEND = 11
PRINT_FONT_SIZE_ANNOT = 11
PRINT_FONT_SIZE_BAR_LABEL = 11

# Figure-Dimensionen für Print-Druck (16 cm Breitsatz im Zielmedium).
STD_FIGSIZE_WIDE = (12, 7.0)
STD_FIGSIZE_TALL = (10, 7.5)
STD_FIGSIZE_DOUBLE = (16, 7.0)
STD_FIGSIZE_TRIPLE = (18, 7.0)

# DPI-Stufen — Print orientiert sich am strengsten Standard (BoD).
PRINT_DPI = 300  # Print-on-Demand-Standard, Foto-Qualität
WEB_DPI = 150  # für Web/Standalone, schneller Download


def apply_mpl_theme() -> None:
    """Setzt Matplotlib-rcParams konsistent zur Palette.

    Aufruf einmal pro Plot-Skript, vor dem ersten figure(). Setzt:
    - Hintergrund (Figure + Axes) auf weiß
    - Grid in hell-grau
    - Text in dark-gray
    - Schriftgrößen aus FONTS (Web/Bildschirm-Defaults)
    """
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["bg"],
            "axes.facecolor": COLORS["bg"],
            "axes.edgecolor": COLORS["text_muted"],
            "axes.labelcolor": COLORS["text_dark"],
            "axes.titlecolor": COLORS["text_dark"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.6,
            "xtick.color": COLORS["text_muted"],
            "ytick.color": COLORS["text_muted"],
            "xtick.labelsize": FONTS["size_tick"],
            "ytick.labelsize": FONTS["size_tick"],
            "axes.titlesize": FONTS["size_title"],
            "axes.labelsize": FONTS["size_axis_label"],
            "legend.fontsize": FONTS["size_legend"],
            "legend.frameon": False,
            "font.family": "sans-serif",
            "font.sans-serif": [
                FONTS["main_sans"],
                "IBM Plex Sans",
                "Source Sans 3",
                "Fira Sans",
                "Inter",
                "Helvetica",
                "Arial",
                "DejaVu Sans",
                "sans-serif",
            ],
            "savefig.facecolor": COLORS["bg"],
            "savefig.edgecolor": "none",
            "savefig.bbox": "tight",
            "savefig.dpi": WEB_DPI,
        }
    )


def apply_print_style() -> None:
    """Print-Variante mit größeren Schriften und Print-DPI.

    Sollte einmalig am Anfang eines Print-Chart-Skripts aufgerufen werden,
    bevor `plt.subplots`. Setzt Schriftgrößen aus den PRINT_FONT_SIZE_*-
    Konstanten und Standard-Speicher-DPI auf PRINT_DPI. Hintergrund ist
    weiß (analytischer Default).
    """
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["bg"],
            "axes.facecolor": COLORS["bg"],
            "font.size": PRINT_FONT_SIZE_BASE,
            "axes.titlesize": PRINT_FONT_SIZE_TITLE,
            "axes.labelsize": PRINT_FONT_SIZE_LABEL,
            "xtick.labelsize": PRINT_FONT_SIZE_BASE,
            "ytick.labelsize": PRINT_FONT_SIZE_BASE,
            "legend.fontsize": PRINT_FONT_SIZE_LEGEND,
            "figure.titlesize": PRINT_FONT_SIZE_SUPTITLE,
            # Linien-Stil
            "axes.linewidth": 0.8,
            "grid.linewidth": 0.5,
            "lines.linewidth": 2.0,
            "patch.linewidth": 0.5,
            # Achsen / Ticks
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.major.size": 4,
            "ytick.major.size": 4,
            # Grid
            "axes.grid": True,
            "grid.linestyle": ":",
            "grid.alpha": 0.5,
            "axes.axisbelow": True,
            # Speicher-Defaults
            "savefig.dpi": PRINT_DPI,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.15,
            "savefig.facecolor": COLORS["bg"],
        }
    )


def save_chart(fig: Any, output_path: Path | str, *, dpi: int = PRINT_DPI, **kwargs: Any) -> None:
    """Speichert ein Diagramm mit konfigurierbarer DPI und sauberem Padding.

    Parameter
    ---------
    fig : matplotlib.figure.Figure
    output_path : str | Path
    dpi : int, default PRINT_DPI (300)
        Speicher-DPI. ``PRINT_DPI`` für Print-Output, ``WEB_DPI`` für
        Web/Standalone-Varianten.
    **kwargs : an `plt.savefig` durchgereicht.
    """
    output_path = Path(output_path)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", **kwargs)
