"""Wiederverwendbare Chart-Bausteine — Core-Visuals.

Jedes Modul exportiert eine ``render_*``-Funktion mit einheitlicher
Signatur:

    render_X(data, out_path, *, variant="embedded", **kwargs) -> None

Variants:
- ``embedded``: Bild zum Einbetten in andere Layouts (LaTeX, Print, HTML),
  DPI 300, kein Titel-Block (umgebende Caption übernimmt)
- ``epub``: E-Reader, DPI 150, gleiches Layout wie embedded
- ``standalone``: ein-Datei-Bild für eigenständige Veröffentlichung,
  DPI 150, Titel im Bild + optionaler Brand-Footer über BrandConfig
- ``web``: SVG für interaktive Frames (Dashboards, Notebooks), kein Titel
"""
