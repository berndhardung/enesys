"""KKW-Bauzeit-Empirie-Chart — westliche First-of-a-Kind-Reaktoren 2002-2030.

Bar-Chart: pro Project zwei gestapelte Balken (geplante vs. realisierte
Frist). Jeder Balken besteht aus zwei Segmenten — FID-Vorlauf
(Politik-Beschluss → Spatenstich) plus Bauzeit (Spatenstich → IBN). Plus
ein Empirie-Korridor-Band für die Gesamt-Frist (16-22 Jahre). Macht
sichtbar, dass westliche EPR/AP1000-Projekte real 16-22 Jahre Frist
brauchen — 3-8 Jahre FID-Vorlauf plus 13-17 Jahre Bauzeit.

Daten sind als ``BuildTimeData`` ausgelagert; Quellen stehen im Modul-
Docstring und bei ``DEFAULT_PROJECTS``: Cour-des-Comptes-Audit (FR),
UK NAO Hinkley-Report, UK NPS EN-6 (2011), EDF-Reports, IAEA-PRIS-
Datenbank, TVO-Pressemitteilungen, US Energy Policy Act 2005,
Georgia-Power Vogtle-Reports.

Branding:
- ``variant="embedded"`` — kein Titel im Bild (umgebende Caption übernimmt)
- ``variant="epub"`` — wie standalone, niedrigere DPI
- ``variant="standalone"`` — Titel + Untertitel + optionaler Brand-Footer
- ``variant="web"`` — SVG-Output
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from enesys.viz.charts._helpers import Variant, add_oss_footer, dpi_for_variant
from enesys.viz.matplotlib_style import (
    PRINT_FONT_SIZE_BAR_LABEL,
    PRINT_FONT_SIZE_BASE,
    PRINT_FONT_SIZE_LABEL,
    PRINT_FONT_SIZE_LEGEND,
    STD_FIGSIZE_WIDE,
    apply_print_style,
)

if TYPE_CHECKING:
    from enesys.viz.brand import BrandConfig


@dataclass(frozen=True)
class Project:
    """Ein FOAK-Reaktorprojekt: Name, Land, Politik-Beschluss, FID-Vorlauf,
    Baubeginn, Plan- und Real-IBN.

    ``politik_jahr`` ist der nationale Politik-Beschluss (NPS EN-6 UK,
    finnisches Parlament FI, EDF-Programm FR, US Energy Policy Act). Die
    Differenz ``baubeginn - politik_jahr`` ist der FID-Vorlauf, der im
    Modell auf 3 a (Mittelwert FOAK) gesetzt wird.
    """

    name: str
    land: str
    politik_jahr: int
    baubeginn: int
    plan_ibn: int
    real_ibn: int
    realisiert: bool  # False für Projekte, die noch nicht in Betrieb sind


# Empirie-Korridor in Jahren für die Gesamt-Frist Politik-Beschluss → IBN
# (FID-Vorlauf 3-8 a plus Bauzeit 13-17 a → 16-22 a Gesamt-Frist).
EMPIRIE_KORRIDOR: tuple[int, int] = (16, 22)


# Default-Project-Auswahl: westliche FOAK-EPR/AP1000-Projekte 2002-2030.
# Quellen siehe Modul-Docstring.
DEFAULT_PROJECTS: tuple[Project, ...] = (
    Project("Olkiluoto-3", "FI", 2002, 2005, 2010, 2023, realisiert=True),
    Project("Flamanville-3", "FR", 2004, 2007, 2012, 2024, realisiert=True),
    # Vogtle-3/4: Politik-Beschluss US Energy Policy Act 2005; COL 2012,
    # Spatenstich März 2013; Unit-4-Mittelwert für IBN.
    Project("Vogtle-3/4", "US", 2005, 2013, 2017, 2024, realisiert=True),
    Project("Hinkley Point C", "UK", 2010, 2018, 2027, 2030, realisiert=False),
    # Penly-EPR2: EDF-Programm 2022, FID erwartet ~2027, Spatenstich 2027.
    Project("Penly (EPR2)", "FR", 2022, 2027, 2035, 2038, realisiert=False),
)


@dataclass(frozen=True)
class BuildTimeData:
    """Bauzeit-Daten für die FOAK-Empirie-Visualisierung."""

    projekte: tuple[Project, ...]
    korridor: tuple[int, int]


def compute_build_time_data(
    *,
    projekte: tuple[Project, ...] = DEFAULT_PROJECTS,
    korridor: tuple[int, int] = EMPIRIE_KORRIDOR,
) -> BuildTimeData:
    """Bündelt Project-Daten plus Empirie-Korridor in eine Dataclass.

    Default sind die fünf westlichen FOAK-Projekte 2005-2030. Konsumenten
    können eigene Project-Auswahl injizieren (für Sensitivitäts-Plots oder
    erweiterte Datenstände).
    """
    return BuildTimeData(projekte=projekte, korridor=korridor)


def _plan_build_time(p: Project) -> int:
    return p.plan_ibn - p.baubeginn


def _real_build_time(p: Project) -> int:
    return p.real_ibn - p.baubeginn


def _fid_vorlauf(p: Project) -> int:
    """Jahre Politik-Beschluss → Spatenstich (FID-Vorlauf)."""
    return p.baubeginn - p.politik_jahr


def render_build_time_empirics(
    data: BuildTimeData,
    out_path: Path | str,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
) -> None:
    """Rendert das KKW-Frist-Empirie-Chart.

    Pro Project zwei gestapelte Balken (Plan + Real). Jeder Balken
    besteht aus zwei Segmenten: FID-Vorlauf (Politik → Spatenstich,
    unten, orange) plus Bauzeit (Spatenstich → IBN, oben, blau). Der
    Empirie-Korridor 16-22 J Gesamt-Frist wird als Hintergrund-Band
    sichtbar. Werte über den Balken annotiert; nicht abgeschlossene
    Projekte tragen einen ``*``-Marker.
    """
    apply_print_style()

    fig, ax = plt.subplots(figsize=STD_FIGSIZE_WIDE)

    projekte = data.projekte
    n = len(projekte)
    x = np.arange(n)
    width = 0.38

    fid_years = [_fid_vorlauf(p) for p in projekte]
    plan_years = [_plan_build_time(p) for p in projekte]
    real_years = [_real_build_time(p) for p in projekte]
    plan_total = [fid + plan for fid, plan in zip(fid_years, plan_years, strict=False)]
    real_total = [fid + real for fid, real in zip(fid_years, real_years, strict=False)]

    # FID lead-time segments (bottom of both bars)
    ax.bar(
        x - width / 2,
        fid_years,
        width,
        color="#F4C46A",
        edgecolor="#A8741A",
        linewidth=1.0,
        label="FID lead time (decision → groundbreaking)",
    )
    ax.bar(
        x + width / 2,
        fid_years,
        width,
        color="#F4C46A",
        edgecolor="#A8741A",
        linewidth=1.0,
    )

    # Construction segments (top, stacked on FID lead time)
    bars_plan = ax.bar(
        x - width / 2,
        plan_years,
        width,
        bottom=fid_years,
        color="#9BBED4",
        edgecolor="#6090B0",
        linewidth=1.0,
        label="Planned construction time",
    )
    bars_real = ax.bar(
        x + width / 2,
        real_years,
        width,
        bottom=fid_years,
        color="#1F4E8C",
        edgecolor="#0A2A50",
        linewidth=1.0,
        label="Realised / current construction time",
    )

    for bar, val_total, val_bauzeit in zip(bars_plan, plan_total, plan_years, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val_total + 0.3,
            f"{val_total} y\n({val_bauzeit} c)",
            ha="center",
            va="bottom",
            fontsize=PRINT_FONT_SIZE_BAR_LABEL,
            color="#445",
        )
    for idx, (bar, val_total, val_bauzeit) in enumerate(
        zip(bars_real, real_total, real_years, strict=False)
    ):
        marker = "" if projekte[idx].realisiert else "*"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val_total + 0.3,
            f"{val_total} y{marker}\n({val_bauzeit} c)",
            ha="center",
            va="bottom",
            fontsize=PRINT_FONT_SIZE_BAR_LABEL,
            color="#0A2A50",
            fontweight="bold",
        )

    # Empirie-Korridor als Hintergrund-Band (Gesamt-Frist Politik → IBN).
    # Wird als Legend-Eintrag (Patch) ausgewiesen, damit kein In-Plot-
    # Text mit den Bar-Labels kollidiert.
    k_low, k_high = data.korridor
    korridor_patch = ax.axhspan(k_low, k_high, color="#FFE8C8", alpha=0.4, zorder=0)
    korridor_patch.set_label(f"Empirical corridor (total lead time {k_low}–{k_high} years)")

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{p.name}\n({p.land}, {p.politik_jahr}–{p.real_ibn})" for p in projekte],
        fontsize=PRINT_FONT_SIZE_BASE,
    )
    ax.tick_params(axis="y", labelsize=PRINT_FONT_SIZE_BASE)
    ax.set_ylabel("Years from political decision to IBN", fontsize=PRINT_FONT_SIZE_LABEL)
    ax.set_ylim(0, 32)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=PRINT_FONT_SIZE_LEGEND + 1, frameon=False)

    if variant == "standalone" and title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.99)
        if subtitle:
            fig.text(0.5, 0.94, subtitle, fontsize=11, color="#444", ha="center", style="italic")

    if variant == "standalone" and brand is not None:
        from enesys.viz.brand import add_brand_footer

        add_brand_footer(fig, brand)

    plt.tight_layout()
    if variant == "standalone" and title:
        plt.subplots_adjust(top=0.90)
    plt.subplots_adjust(bottom=0.18)
    add_oss_footer(fig)

    out_path = Path(out_path)
    dpi = dpi_for_variant(variant)
    if variant == "web":
        if out_path.suffix.lower() != ".svg":
            out_path = out_path.with_suffix(".svg")
        fig.savefig(out_path, bbox_inches="tight")
    else:
        if out_path.suffix.lower() != ".png":
            out_path = out_path.with_suffix(".png")
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
