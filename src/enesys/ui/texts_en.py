"""UI text blocks (EN) — English twin of :mod:`texts_de`.

Selected via :mod:`enesys.ui.i18n` from the ``?lang=en`` query parameter.
Public-attribute set is kept in sync with :mod:`texts_de` (enforced by
test).
"""

from __future__ import annotations

# ===========================================================================
# Monte-Carlo methodology expander
# Used by: compare view, below the robustness chart
# ===========================================================================

MONTE_CARLO_METHODE_EXPANDER = (
    "**Method.** Monte-Carlo analysis with correlated sampling. "
    "For each of the 3,000 iterations a random value is drawn "
    "**simultaneously** from the plausible band of every assumption — "
    "nuclear build time, PV learning curve, gas price, hydrogen "
    "availability, and roughly 20 other parameters.\n\n"
    "**Correlated sampling** means that if, for instance, the gas "
    "price is drawn high, the CO₂-levy assumption is drawn higher "
    "too — because these quantities are not independent in reality.\n\n"
    "**Bands** come from the ``CAMP_RANGES`` data structure, which "
    "encodes for each parameter the lower bound (typically the EE-camp "
    "view) and upper bound (typically the nuclear-camp view). Sources "
    "are listed on the Sources page and in `docs/SOURCES.md`.\n\n"
    "**Methodological reference.** Robustness method documented in "
    "`docs/methodik/methodology.md`."
)


# ===========================================================================
# Legal and liability disclaimer expander
# Used by: footer on every page
# ===========================================================================

RECHTLICHES_HAFTUNG_EXPANDER = (
    "**Open-source licence.** Model and accompanying UI are released "
    "under the MIT licence. Source code, documentation, and tests are "
    "available for review, modification, and reuse — including in "
    "commercial projects — subject to the licence terms.\n\n"
    "**Liability disclaimer.** This application serves opinion "
    "formation, assumption auditing, and journalistic debate on "
    "energy-policy questions. It does **not constitute investment "
    "advice** within the meaning of the German Securities Trading Act "
    "(WpHG), **legal advice** within the meaning of the Legal Services "
    "Act (RDG), or **tax advice** within the meaning of the Tax "
    "Consultancy Act (StBerG). Results are model outputs under the "
    "selected assumptions, not forecasts. Any decision made on the "
    "basis of these results is taken at the user's own risk. The "
    "author accepts no liability for damages arising from use of "
    "this software.\n\n"
    "**Data sources.** Default values come from publicly available "
    "studies (Fraunhofer ISE, Bundesnetzagentur, BMWK/BMWE, Cour des "
    "Comptes, EWI Cologne, the European Commission, BDEW, ZIV) and "
    "commercial sources (BloombergNEF). Sources are cited, not "
    "reproduced — no tables, charts, or substantial text excerpts "
    "from the original sources are contained in this software. "
    "Citations appear in tooltips and in the Sources page.\n\n"
    "**Data protection.** This Streamlit application stores no "
    "personal data server-side. Slider inputs are processed solely in "
    "the local browser session and discarded when the tab is closed. "
    "When hosted on a public server, the data-protection policy of "
    "the respective operator applies (server logs, IP addresses).\n\n"
    "**Responsible party under §5 DDG and §18(2) MStV:** "
    "Dr. Bernd Hardung. Contact: bernd@hardung.de. "
    "Full imprint with service address: see the imprint page of the "
    "hosting provider or the relevant domain."
)


__all__ = [
    "MONTE_CARLO_METHODE_EXPANDER",
    "RECHTLICHES_HAFTUNG_EXPANDER",
]
