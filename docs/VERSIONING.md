# Versioning

How the version number is structured in the model and how it is
queried at runtime. The maintainer workflow (release bump, branch
model) lives separately — see the note at the end.

## Scheme

`MAJOR.MINOR.PATCH` — pre-1.0 mode with a loosened SemVer contract.

- **MAJOR** is the main line.
- **MINOR may be breaking in <1.0.** Deliberate deviation from SemVer.
  Reason: a MAJOR bump on every methodological change would inflate
  the version number without carrying extra information. Nobody
  outside the project depends on the API.
- **PATCH** is for pure bug fixes within a running MINOR line. Strict
  backward compatibility applies here — a 0.1.2 must serve as a
  drop-in replacement for 0.1.1.

## Current state

The current version state is determined by the
[`VERSION`](../VERSION) file and [`CHANGELOG.md`](../CHANGELOG.md).
Real releases are additionally marked with annotated git tags
`vX.Y.Z`.

## Build-time version string

The final version number is automatically assembled from `VERSION`
plus git status:

| Branch | Dirty? | Output of `get_version()` |
|---|---|---|
| `stable/0.1` | no | `0.1.0` |
| `main` | no | `0.1.0-gabc1234` |
| any | yes | `0.1.0-gabc1234-dirty` |

`dirty` means: changes to tracked files, uncommitted or staged.
Untracked files (`__pycache__`, local output directories) do not
count.

So the clean `0.1.0` without suffix only appears when the current
branch is a `stable/X.Y` branch AND the working tree is clean.
Otherwise the git hash is always attached, so every build is uniquely
identifiable.

**Note on release pinning.** `stable/X.Y` branches are a maintainer-
workflow convention for parallel maintenance lines (0.1.x, 0.2.x, …)
and do not appear in this repo. Anyone who needs a reproducible
release state should check out the corresponding tag:

```bash
git checkout v0.1.0
```

In that case HEAD is detached (no branch name), so `get_version()`
still appends hash + date. The canonical version information is then
the tag itself, not the `get_version()` output.

## Where the version is surfaced

From code:

```python
from enesys import get_version
get_version()  # → "0.1.0" or "0.1.0-gabc1234-dirty"
```

Or from the terminal:

```bash
python -m enesys
```

## What happens without git?

If someone has the repo without git history (e.g. as a ZIP download or
a wheel install), `get_version()` simply returns the contents of the
`VERSION` file without a suffix. The version number is then "trustless"
— no one knows whether local changes were made.

That is acceptable: in that situation identification is not central
either. The `dirty` marker exists primarily so that, during active
development, one can see "I'm currently building with local changes" —
as soon as the artifact is freshly deployed it is by definition not
dirty.

## FAQ

### Why not `setuptools-scm`?
Considered, but overkill for a single-repo project. The `VERSION` file
plus `version.py` come to ~150 lines of code, are self-contained (no
additional build dependencies), and do exactly the right thing.

### How do I see the current version from the terminal?
```bash
python -m enesys
```

Or programmatically:
```python
from enesys import get_version
print(get_version())
```

### What if `git` is missing on the build machine?
`get_version()` catches that and returns only the base version from
the `VERSION` file. The build still goes through. This is the
standard container case (e.g. Docker build).

### How do I prevent accidentally inflating the version?
The `VERSION` file is central and is bumped only explicitly. There is
no automatic bumping.

### What about the version in `pyproject.toml`?
`pyproject.toml` carries a static `version = "X.Y.Z"` field that must
be bumped in lock-step with `VERSION` at release time. The static
declaration exists because `uv lock` cannot represent a dynamic
version in its lockfile (the resulting `[[package]] name = "enesys"`
entry has no `version =` field, which downstream uv consumers — e.g.
Streamlit Community Cloud's deploy installer — reject). Runtime
version lookup (`get_version()` / `enesys.__version__`) continues to
read the `VERSION` file directly via `version.py`, so it stays the
source of truth for the build-time-stamped string with git hash and
date. Release-time bump touches three places together:
`pyproject.toml` (static), `VERSION` (file), and `CITATION.cff`
(`version` + `date-released`).

---

**Note for maintainers.** The release workflow (creating a stable
branch, MINOR/PATCH bump, tag maintenance) is documented separately
and is not part of this public document.
