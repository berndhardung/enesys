# Versionsverwaltung

Wie die Versionsnummer im Modell aufgebaut ist und wie sie zur Laufzeit
abgefragt wird. Maintainer-Workflow (Release-Bump, Branch-Modell) liegt
separat — siehe Hinweis am Ende dieses Dokuments.

## Schema

`MAJOR.MINOR.PATCH` — Pre-1.0-Modus mit gelockertem Semver-Vertrag.

- **MAJOR** ist die Hauptlinie.
- **MINOR darf in <1.0 breaking sein.** Bewusste Abweichung von Semver.
  Begründung: ein MAJOR-Bump bei jeder methodischen Änderung würde zu
  Versionsinflation führen, ohne dass die Versionsnummer zusätzliche
  Information transportiert. Niemand außerhalb des Projekts hängt von
  der API ab.
- **PATCH** ist für reine Bugfixes in einer laufenden MINOR-Linie. Hier
  gilt strikte Rückwärtskompatibilität — eine 0.1.2 muss als
  Drop-in-Replacement für 0.1.1 dienen können.

## Aktueller Stand

Der aktuelle Versionsstand wird durch die [`VERSION`](../VERSION)-Datei und
[`CHANGELOG.md`](../CHANGELOG.md) bestimmt. Echte Releases werden zusätzlich
mit annotierten Git-Tags `vX.Y.Z` markiert.

## Build-Zeit-Versionsstring

Die finale Versionsnummer wird automatisch aus `VERSION` plus Git-Status
zusammengesetzt:

| Branch | Dirty? | Output von `get_version()` |
|---|---|---|
| `stable/0.1` | nein | `0.1.0` |
| `main` | nein | `0.1.0-gabc1234` |
| beliebig | ja | `0.1.0-gabc1234-dirty` |

`dirty` bedeutet: Änderungen an tracked files, uncommitted oder staged.
Untracked files (`__pycache__`, lokale Output-Verzeichnisse) zählen
nicht.

Die saubere "0.1.0" ohne Suffix erscheint also nur, wenn der aktuelle
Branch ein `stable/X.Y`-Branch ist UND der Working Tree clean ist.
Sonst ist immer der Git-Hash dabei, sodass jedes Build eindeutig
identifizierbar ist.

**Hinweis zur Release-Pinnung.** `stable/X.Y`-Branches sind eine
Maintainer-Workflow-Konvention für parallele Wartungslinien (0.1.x,
0.2.x, …) und tauchen in diesem Repo nicht auf. Wer einen
reproduzierbaren Release-Stand braucht, checkt den entsprechenden Tag
aus:

```bash
git checkout v0.1.0
```

In diesem Fall ist HEAD detached (kein Branch-Name), `get_version()`
hängt also weiterhin Hash + Datum an. Die kanonische Version-Information
ist dann der Tag selbst, nicht der `get_version()`-Output.

## Wo die Version sichtbar wird

Aus dem Code:

```python
from enesys import get_version
get_version()  # → "0.1.0" oder "0.1.0-gabc1234-dirty"
```

Oder aus dem Terminal:

```bash
python -m enesys
```

## Was passiert ohne Git?

Wenn jemand das Repo ohne Git-Historie in der Hand hat (etwa als
ZIP-Download oder als Wheel-Installation), liefert `get_version()`
einfach den Inhalt der `VERSION`-Datei ohne Suffix. Dann ist die
Versionsnummer "trustless" — niemand weiß, ob lokal noch dran
rumgefummelt wurde.

Das ist akzeptabel: in dieser Situation ist die Identifikation auch
nicht zentral. Die `dirty`-Markierung dient primär dazu, im laufenden
Entwicklungs-Workflow zu sehen "ich baue gerade mit lokalen Änderungen"
— sobald jemand das Artefakt frisch deployed, ist es per Definition
nicht dirty.

## FAQ

### Warum kein `setuptools-scm`?
Erwogen, aber für ein Single-Repo-Projekt overkill. Die `VERSION`-Datei
plus `version.py` kommen mit ~150 Zeilen Code aus, sind eigenständig
(keine zusätzlichen Build-Dependencies) und tun genau das Richtige.

### Wie sehe ich die aktuelle Version aus dem Terminal?
```bash
python -m enesys
```

Oder programmatisch:
```python
from enesys import get_version
print(get_version())
```

### Was wenn `git` auf dem Build-Rechner fehlt?
`get_version()` fängt das ab und liefert nur die Basis-Version aus der
`VERSION`-Datei. Build geht trotzdem durch. Das ist der
Container-Standardfall (z.B. Docker-Build).

### Wie verhindere ich versehentliches Inflationieren der Version?
Die `VERSION`-Datei ist zentral und wird nur explizit gebumpt. Es gibt
kein automatisches Bumping.

---

**Hinweis für Maintainer.** Der Release-Workflow (Stable-Branch
anlegen, MINOR-/PATCH-Bump, Tag-Pflege) wird separat dokumentiert und
ist nicht Teil dieses Public-Dokuments.
