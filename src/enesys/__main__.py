"""Erlaubt `python -m enesys` → druckt die Version.

Liegt bewusst in einem eigenen Modul (statt `if __name__ == "__main__"`
in version.py), weil enesys/__init__.py bereits aus enesys.version
importiert. Würde version.py selbst als `__main__` ausgeführt, käme
eine runpy-RuntimeWarning wegen Doppelimport.
"""

from enesys.version import get_version

print(get_version())
