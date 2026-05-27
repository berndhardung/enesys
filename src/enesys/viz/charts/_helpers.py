"""Helper-Funktionen für die Chart-Bausteine in viz/charts/.

Drei Codierungs-Dimensionen pro Pfad (Graustufen-Sicherheit):
- Farbe aus PATH_COLORS
- Linien-Stil aus PATH_LINESTYLES
- Endpunkt-Marker aus PATH_END_MARKERS (`o`/`s`/`^`/`D`)

``apply_path_style`` setzt alle drei in einem Aufruf, ``add_endpoint_marker``
platziert den Marker am letzten Datenpunkt einer Trajektorie. ``dpi_for_variant``
liefert die passende DPI je nach variant. ``add_oss_footer`` schreibt eine
dezente Repo-Quellangabe (Reproduzierbarkeit).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Literal

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from enesys.viz.matplotlib_style import PRINT_DPI, WEB_DPI
from enesys.viz.theme import (
    PATH_COLORS,
    PATH_END_MARKERS,
    PATH_LINESTYLES,
    PATH_OPEN_MARKERS,
)

Variant = Literal["embedded", "epub", "standalone", "web"]

# OSS-Repo-URL: zentrale Quellangabe für die im Public-Mirror reproduzierbaren
# Charts. Wird im Footer aller viz/charts/-Bausteine gerendert.
OSS_REPO_URL = "github.com/berndhardung/enesys"


def dpi_for_variant(variant: Variant) -> int:
    """Passende Speicher-DPI je nach variant.

    ``embedded`` = 300 (Print-tauglich, BoD-Standard), ``epub``/``standalone``
    = 150 (Screen-DPI), ``web`` = irrelevant (SVG ist Vektor) — Default 150
    zurückgegeben.
    """
    if variant == "embedded":
        return PRINT_DPI
    return WEB_DPI


def apply_path_style(line: Line2D, path_id: str, *, linewidth: float = 2.5) -> None:
    """Setzt Farbe + Linien-Stil + Linienbreite auf einem matplotlib Line2D.

    Pfad-ID muss in PATH_COLORS und PATH_LINESTYLES sein. Wird typischerweise
    direkt nach ``ax.plot(...)`` aufgerufen. Endpunkt-Marker werden separat
    über ``add_endpoint_marker`` gesetzt.
    """
    line.set_color(PATH_COLORS[path_id])
    line.set_linestyle(PATH_LINESTYLES[path_id])
    line.set_linewidth(linewidth)


def add_endpoint_marker(
    ax: Axes,
    x_end: float,
    y_end: float,
    path_id: str,
    *,
    size: float = 90,
    zorder: int = 5,
) -> None:
    """Platziert den pfad-spezifischen Endpunkt-Marker am letzten Datenpunkt.

    H2-Pfade (ee_h2, kkw_h2) bekommen einen „offenen" Marker (face=white,
    Edge in Pfad-Farbe) als semantisches Pendant zum entsprechenden
    Gas-Pfad. Andere Pfade bekommen den gefüllten Marker in Pfad-Farbe.
    """
    color = PATH_COLORS[path_id]
    marker = PATH_END_MARKERS[path_id]
    if path_id in PATH_OPEN_MARKERS:
        facecolor: str = "white"
        edgecolor: str = color
    else:
        facecolor = color
        edgecolor = "white"
    ax.scatter(
        [x_end],
        [y_end],
        marker=marker,
        s=size,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.8,
        zorder=zorder,
    )


def add_inline_label(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    path_id: str,
    *,
    fontsize: int = 11,
    dx: float = 0.5,
) -> None:
    """Setzt einen Inline-Label rechts neben dem Endpunkt einer Trajektorie.

    Meyer-Stil: Bold-Label in Pfad-Farbe direkt am Ende der Kurve, statt
    separater Legende. Bei sehr nah beieinanderliegenden Endpunkten muss
    der Aufrufer ``dx``/``y`` manuell justieren (Anti-Overlap).
    """
    ax.text(
        x + dx,
        y,
        text,
        fontsize=fontsize,
        fontweight="bold",
        color=PATH_COLORS[path_id],
        family="sans-serif",
        va="center",
        ha="left",
    )


def _resolve_oss_version() -> str:
    """Bestimmt einen kurzen Versions-String für den OSS-Footer.

    Priorität:
    1. ``ENESYS_OSS_VERSION`` aus dem Environment (vom Build-Script gesetzt)
    2. ``git describe --always --dirty`` aus dem Repo (langer Tag-String wird
       auf den Hash-Teil reduziert: ``…-g<hash>[-dirty]`` → ``<hash>[-dirty]``)
    3. Fallback ``VERSION``-Datei
    4. ``unknown``, wenn alles fehlt
    """
    env = os.environ.get("ENESYS_OSS_VERSION")
    if env:
        return env

    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parents[4],
        )
        raw = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        raw = ""

    if raw:
        # Format wie ``0.1.0-pre+sep-models-254-ga09c280-dirty`` auf den
        # Hash-Teil reduzieren — kompakter, eindeutig für den Footer.
        if "-g" in raw:
            tail = raw.split("-g", 1)[1]
            return tail  # e.g. ``a09c280-dirty``
        return raw

    version_file = Path(__file__).resolve().parents[4] / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "unknown"


def add_oss_footer(
    fig: Figure,
    *,
    repo_url: str = OSS_REPO_URL,
    version: str | None = None,
    fontsize: int = 7,
) -> None:
    """Schreibt eine dezente OSS-Quellangabe unten ans Bild.

    Format: ``<repo_url> @ <version>`` (z. B. ``github.com/berndhardung/enesys @
    a09c280-dirty``). Wird in allen vier Varianten (``embedded``, ``epub``,
    ``standalone``, ``web``) gerendert, weil sie Reproduzierbarkeit trägt
    und keine Marke. Konsumenten können den Footer abschalten, indem sie
    ``add_oss_footer`` schlicht nicht aufrufen.
    """
    if version is None:
        version = _resolve_oss_version()
    fig.text(
        0.99,
        0.005,
        f"{repo_url} @ {version}",
        fontsize=fontsize,
        color="#888",
        ha="right",
        va="bottom",
        alpha=0.7,
    )


def to_grayscale_luminance(hex_color: str) -> float:
    """Konvertiert eine Hex-Farbe zu Luminanz (0.0 = schwarz, 1.0 = weiß).

    Nutzt die ITU-R BT.709-Gewichtung (Standard für sRGB → Luminanz).
    Wird vom Graustufen-Architektur-Test verwendet, um zu prüfen, dass
    die Pfade über Linien-Stil/Marker unterscheidbar bleiben, wenn die
    Farbe in Graustufen kollabiert.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
