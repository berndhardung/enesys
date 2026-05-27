"""Generisches Marken-Framework für gebrandete Charts.

Liefert eine ``BrandConfig``-Dataclass und Helper-Funktionen
(``add_brand_footer``, ``add_wortmarke``), die in eigenen Generator-
Modulen genutzt werden können, um Chart-Outputs mit Wortmarke und
Domain-Footer zu versehen. Konkrete Marken-Werte (Titel, Autor, Domain)
gehören NICHT in dieses Modul — Konsumenten instanziieren ihre eigene
``BrandConfig`` und übergeben sie an die Helper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.figure import Figure


@dataclass(frozen=True)
class BrandConfig:
    """Marken-Identität für gebrandete Charts.

    Konsumenten instanziieren dies einmal pro Marke und übergeben es an
    die Branding-Helper. Beispiel:

        from enesys.viz.brand import BrandConfig

        MY_BRAND = BrandConfig(
            title="<Titel>",
            subtitle="<Untertitel>",
            author="<Autor>",
            domain="<domain.de>",
            year=2026,
        )
    """

    title: str
    subtitle: str
    author: str
    domain: str
    year: int
    primary_color: str = "#0E1B4D"
    accent_color: str = "#E5007D"
    light_color: str = "#F5C8DD"
    paper_color: str = "#F5F2EC"
    muted_color: str = "#B0B0C8"
    extras: dict[str, Any] = field(default_factory=dict)


def add_brand_footer(
    fig: Figure,
    brand: BrandConfig,
    *,
    text: str | None = None,
    alpha: float = 0.7,
    fontsize: int = 8,
    x: float = 0.98,
    y: float = 0.01,
) -> None:
    """Schreibt einen Marken-Footer rechtsbündig in den unteren Rand.

    Default-Text: ``"<domain> · <title>"``. Wird typischerweise in
    Branded-Generatoren mit ``variant="standalone"`` aufgerufen.
    """
    if text is None:
        text = f"{brand.domain} · {brand.title}"
    fig.text(
        x,
        y,
        text,
        fontsize=fontsize,
        color="#666",
        ha="right",
        va="bottom",
        alpha=alpha,
        family="sans-serif",
    )


def add_wortmarke(
    fig: Figure,
    brand: BrandConfig,
    x: float,
    y: float,
    *,
    scale: float = 1.0,
    on_dark: bool = False,
) -> None:
    """Zeichnet die Wortmarke an Position (x, y) in Figure-Koordinaten.

    Layout: Marken-Initialen (Pagella Serif kursiv, Akzentfarbe) +
    Voll-Titel (sans-serif bold) + Domain (sans-serif). Initialen kommen
    aus ``brand.extras["wortmarke_short"]`` (Default: erste Buchstaben
    der Titel-Wörter).

    on_dark: Bei dunklen Hintergründen werden Titel + Domain in
    paper_color statt text_dark gerendert.
    """
    text_color = brand.paper_color if on_dark else "#222222"
    muted_color = brand.muted_color if on_dark else "#666"

    short = brand.extras.get("wortmarke_short") or _initials(brand.title)
    wortmarke_color = brand.extras.get("wortmarke_color", brand.accent_color)

    fig.text(
        x,
        y,
        short,
        fontsize=int(22 * scale),
        fontweight="bold",
        color=wortmarke_color,
        family="serif",
        style="italic",
        ha="left",
        va="top",
        zorder=20,
    )
    fig.text(
        x,
        y - 0.035 * scale,
        brand.title,
        fontsize=max(7, int(8 * scale)),
        color=text_color,
        family="sans-serif",
        fontweight="bold",
        ha="left",
        va="top",
        zorder=20,
    )
    fig.text(
        x,
        y - 0.055 * scale,
        brand.domain,
        fontsize=max(7, int(8 * scale)),
        color=muted_color,
        family="sans-serif",
        ha="left",
        va="top",
        zorder=20,
    )


def _initials(title: str) -> str:
    """Bildet eine Kurz-Initialen-Wortmarke aus dem Buchtitel.

    Nimmt den ersten Buchstaben jedes Worts (außer Artikel/Präpositionen),
    bis maximal vier Zeichen.
    """
    stopwords = {"der", "die", "das", "den", "dem", "des", "und", "oder", "von", "zu", "im", "in"}
    letters = [word[0].upper() for word in title.split() if word.lower() not in stopwords and word]
    return "".join(letters[:4])
