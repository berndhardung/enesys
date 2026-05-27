"""Core: Forward-Cost-Hauptmodell.

Die volkswirtschaftliche LCOE-Bilanz mit 30-Jahres-Mittel über sechs
Pfade. Hier liegt der modellseitige Kern: Mengen-Bilanz, Sensitivität,
Lager-Bandbreiten und Quellen-Disziplin.

Module:
- path_model        Pfadmodell 2026-2055, sechs Pfade (compute_path)
- sensitivity       Baseline, Tornado, Monte Carlo, Schadens-Asymmetrie
- path_sensitivity  Snapshot-Datenstrukturen, Lager-Presets
- camp_ranges       Lager-Bandbreiten (CAMP_RANGES)
- source_trace      Validator für [SRC: TAG]-Disziplin
"""
