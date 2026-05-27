"""Visual Style Master — Single Source of Truth für Farbpalette und Themes.

Konsumiert von:
- Matplotlib-Chart-Skripten (Print + Branded-Layouts)
- Plotly-Charts (Streamlit)
- Web-Frontend (palette.json)

Architektur:
- `theme.py` — COLORS, FONTS, PATH_COLORS, PATH_LABELS, Lookups — Single Source
- `matplotlib_style.py` — apply_mpl_theme, apply_print_style, save_chart, PRINT_*-Konstanten
- `plotly_style.py` — apply_plotly_style, plotly_template
- `brand.py` — generisches Marken-Framework (BrandConfig + Helper)
"""

from enesys.viz.brand import BrandConfig
from enesys.viz.charts.build_time import (
    compute_build_time_data,
    render_build_time_empirics,
)
from enesys.viz.charts.montecarlo import (
    compute_monte_carlo_data,
    render_monte_carlo,
)
from enesys.viz.charts.rampup import (
    compute_mix_rampup_data,
    render_mix_rampup_grid,
)
from enesys.viz.charts.stress import (
    compute_stress_rampup_data,
    render_stress_rampup_grid,
)
from enesys.viz.charts.tornado import (
    compute_tornado_data,
    render_tornado_sensitivity,
)
from enesys.viz.matplotlib_style import (
    PRINT_DPI,
    PRINT_FONT_SIZE_ANNOT,
    PRINT_FONT_SIZE_BAR_LABEL,
    PRINT_FONT_SIZE_BASE,
    PRINT_FONT_SIZE_LABEL,
    PRINT_FONT_SIZE_LEGEND,
    PRINT_FONT_SIZE_SUPTITLE,
    PRINT_FONT_SIZE_TITLE,
    STD_FIGSIZE_DOUBLE,
    STD_FIGSIZE_TALL,
    STD_FIGSIZE_TRIPLE,
    STD_FIGSIZE_WIDE,
    WEB_DPI,
    apply_mpl_theme,
    apply_print_style,
    save_chart,
)
from enesys.viz.plotly_style import apply_plotly_style, plotly_template
from enesys.viz.theme import (
    COLOR_ATOM,
    COLOR_EE,
    COLOR_STATUSQUO,
    COLORS,
    FONTS,
    LAYER_COLORS,
    PATH_COLORS,
    PATH_END_MARKERS,
    PATH_LABELS,
    PATH_LINESTYLES,
    PATH_OPEN_MARKERS,
    get_camp_color,
    get_camp_marker,
    get_path_color,
    to_palette_dict,
)

__all__ = [
    # Konstanten — Farben + Schriften
    "COLORS",
    "FONTS",
    "PATH_COLORS",
    "PATH_END_MARKERS",
    "PATH_LABELS",
    "PATH_LINESTYLES",
    "PATH_OPEN_MARKERS",
    "COLOR_EE",
    "COLOR_STATUSQUO",
    "COLOR_ATOM",
    "LAYER_COLORS",
    # Print-Konstanten
    "PRINT_DPI",
    "WEB_DPI",
    "STD_FIGSIZE_WIDE",
    "STD_FIGSIZE_TALL",
    "STD_FIGSIZE_DOUBLE",
    "STD_FIGSIZE_TRIPLE",
    "PRINT_FONT_SIZE_BASE",
    "PRINT_FONT_SIZE_LABEL",
    "PRINT_FONT_SIZE_TITLE",
    "PRINT_FONT_SIZE_SUPTITLE",
    "PRINT_FONT_SIZE_LEGEND",
    "PRINT_FONT_SIZE_ANNOT",
    "PRINT_FONT_SIZE_BAR_LABEL",
    # Lookup-Funktionen
    "get_camp_color",
    "get_camp_marker",
    "get_path_color",
    # Adapter
    "apply_mpl_theme",
    "apply_print_style",
    "apply_plotly_style",
    "plotly_template",
    "save_chart",
    "to_palette_dict",
    # Marken-Framework
    "BrandConfig",
    # Chart-Renderer (compute_*/render_* je Chart-Modul)
    "compute_build_time_data",
    "render_build_time_empirics",
    "compute_monte_carlo_data",
    "render_monte_carlo",
    "compute_mix_rampup_data",
    "render_mix_rampup_grid",
    "compute_stress_rampup_data",
    "render_stress_rampup_grid",
    "compute_tornado_data",
    "render_tornado_sensitivity",
]
