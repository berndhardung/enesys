"""ParamSet-Basisklasse für externe Annahmen-Sätze.

Ein ``ParamSet`` bündelt das Annahmen-Substrat einer externen Quelle
(PyPSA-Tech-Data, NEA-IEA PCGE, BNEF, Fraunhofer-ISE, …) als
reproduzierbares ``param_overrides``-Dict für ``compute_path``.

Abgrenzung zu CAMP_RANGES
-------------------------
``CAMP_RANGES`` modelliert die methodische Lager-Symmetrie: vier politische
Positionen (EE-/Atom-/Bestand-optimistisch + Neutral-Default) mit unteren
und oberen Bandbreiten. Das ist ein politisches Argument: »Was würde dieses
Lager als Bandbreite akzeptieren?«

``ParamSet`` modelliert externe Annahmen-Vergleichspunkte: konkrete
Default-Werte einer fremden Modellfamilie, übersetzt auf enesys-Tech-IDs.
Das ist ein methodisches Argument: »Bleibt unser Befund unter dem
Annahmen-Substrat eines anderen Modells erhalten?«

Beide Strukturen schreiben in denselben ``param_overrides``-Mechanismus
und sind damit kompatibel zur bestehenden Tornado-/Monte-Carlo-Infrastruktur.

Trajektorien statt Snapshots
----------------------------
Externe Datenquellen liefern in der Regel keine drei unabhängigen Snapshots,
sondern eine zusammenhängende Trajektorie (»Hochlauf« mit Lerneffekten).
Ein ``ParamSet`` bündelt diese Trajektorie als Stützstellen-Dict:

    {
        "pv.capex_eur_kw": {2030: 482.48, 2040: 403.38, 2050: 367.87},
        "kkw_neubau_epr.capex_eur_kw": 10805.70,  # zeitkonstant
        ...
    }

``overrides(year)`` löst Stützstellen-Dicts via linearer Interpolation auf;
Floats werden als zeitkonstante Werte 1:1 durchgereicht. Außerhalb des
Stützstellen-Bereichs wird konstant fortgesetzt (keine Trend-Extrapolation
jenseits der Quell-Horizonte).

``overrides_yearly(years)`` liefert das jahres-aufgelöste Dict für
mehrjährige Läufe von ``compute_path``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

TrajectoryValue = float | dict[int, float]


@dataclass(frozen=True)
class ParamSet:
    """Reproduzierbares Parameter-Substrat einer externen Quelle.

    Felder
    ------
    name
        Eindeutiger Identifier, Snake-Case ohne Jahres-Suffix
        (z.B. ``"ariadne_pypsa"``). Wird als ``param_set=``-Argument
        von ``compute_path`` verwendet.
    description
        Ein-Satz-Beschreibung der Quelle und ihres Zwecks.
    source
        Vollzitat der primären Quelle mit Datum/Commit/Tabelle. Muss
        ausreichen, um die Werte später nachzuvollziehen.
    reference_years
        Stützstellen-Jahre der Trajektorie (z.B. ``(2030, 2040, 2050)``).
        Außerhalb wird konstant fortgesetzt.
    currency_year
        Preisbasis der Werte (EUR_yyyy).
    trajectories_factory
        Argumentlose Funktion, die das Trajektorien-Dict liefert.
        Per Konvention im selben Modul als ``build_trajectories()``
        definiert.
    caveats
        Methodische Differenzen zur enesys-Modellierung als Tupel von
        Klartext-Sätzen.
    """

    name: str
    description: str
    source: str
    reference_years: tuple[int, ...]
    currency_year: int
    trajectories_factory: Callable[[], dict[str, TrajectoryValue]]
    caveats: tuple[str, ...] = field(default_factory=tuple)

    def overrides(self, year: int) -> dict[str, float]:
        """Liefert das ``param_overrides``-Dict für ein konkretes Jahr.

        Floats werden 1:1 durchgereicht (zeitkonstant). Stützstellen-Dicts
        werden via linearer Interpolation aufgelöst. Außerhalb des
        Stützstellen-Bereichs wird der nächstgelegene Rand-Wert konstant
        fortgesetzt.
        """
        trajectories = self.trajectories_factory()
        return {key: _resolve_at(value, year) for key, value in trajectories.items()}

    def overrides_yearly(self, years: Iterable[int]) -> dict[int, dict[str, float]]:
        """Liefert jahres-aufgelöste Overrides für mehrjährige Läufe.

        Wird von ``compute_path(years=[...], param_set=...)`` konsumiert,
        damit die Trajektorie über die Jahre korrekt wirkt statt einem
        Bezugsjahr-Mittel. Erspart Aufrufern die Schleife.
        """
        trajectories = self.trajectories_factory()
        return {
            year: {key: _resolve_at(value, year) for key, value in trajectories.items()}
            for year in years
        }

    def summary(self) -> str:
        """Mehrzeiliger Klartext-Block für CLI und Test-Diagnose."""
        years_str = ", ".join(str(y) for y in self.reference_years)
        lines = [
            f"ParamSet: {self.name}",
            f"  {self.description}",
            f"  Stützstellen: [{years_str}] | Preisbasis: EUR_{self.currency_year}",
            f"  Quelle: {self.source}",
        ]
        if self.caveats:
            lines.append("  Caveats:")
            lines.extend(f"    - {c}" for c in self.caveats)
        return "\n".join(lines)

    def __repr__(self) -> str:
        years_str = "/".join(str(y) for y in self.reference_years)
        return f"ParamSet(name={self.name!r}, years={years_str}, currency={self.currency_year})"


def _resolve_at(value: TrajectoryValue, year: int) -> float:
    """Löst einen Trajektorien-Wert für ein konkretes Jahr auf.

    Lineare Interpolation zwischen benachbarten Stützstellen. Außerhalb
    des Stützstellen-Bereichs wird der nächste Rand-Wert konstant
    fortgesetzt (keine Trend-Extrapolation, weil Lerneffekte jenseits
    der Quell-Horizonte spekulativ sind).
    """
    if isinstance(value, (int, float)):
        return float(value)

    if not value:
        raise ValueError("leere Stützstellen-Liste in ParamSet-Trajektorie")

    years_sorted = sorted(value)

    if year <= years_sorted[0]:
        return float(value[years_sorted[0]])
    if year >= years_sorted[-1]:
        return float(value[years_sorted[-1]])

    for i in range(len(years_sorted) - 1):
        y_lo, y_hi = years_sorted[i], years_sorted[i + 1]
        if y_lo <= year <= y_hi:
            v_lo = float(value[y_lo])
            v_hi = float(value[y_hi])
            ratio = (year - y_lo) / (y_hi - y_lo)
            return v_lo + ratio * (v_hi - v_lo)

    raise RuntimeError(f"unerreichbar: year={year} nicht aufgelöst")


def assert_known_keys(
    overrides: dict[str, float],
    *,
    known_tech_ids: set[str],
    known_fuel_ids: set[str],
) -> list[str]:
    """Prüft, dass alle Override-Keys auf bekannte Tech-/Fuel-IDs zeigen.

    Gibt Liste unbekannter Keys zurück (leer = alles okay). Wird vom
    Convergence-Test verwendet, um stille Tippfehler in Mappings oder
    Inventar-Umbenennungen sofort sichtbar zu machen.

    Erlaubte Key-Formate
    --------------------
    - ``"<tech_id>.<field>"`` — TechEntry-Override
    - ``"<fuel_id>.preis_eur_mwh"`` — Fuel-Preis-Override
    - ``"co2_price_eur_t"`` — globaler CO2-Preis
    """
    unknown: list[str] = []
    for key in overrides:
        if key == "co2_price_eur_t":
            continue
        if "." not in key:
            unknown.append(key)
            continue
        head, _ = key.split(".", 1)
        if head not in known_tech_ids and head not in known_fuel_ids:
            unknown.append(key)
    return unknown


__all__ = ["ParamSet", "TrajectoryValue", "assert_known_keys"]
