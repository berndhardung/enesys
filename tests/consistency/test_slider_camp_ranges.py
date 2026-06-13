"""Every camp default must fall within its slider's ``[lo, hi]`` range.

Regression guard for the ``StreamlitValueBelow/AboveMinError`` crash: a
camp whose default sits outside the bound widget's range makes selecting
that camp raise at render time (observed for ``weiterso_optimistic`` /
``nep_realization_rate`` = 0.30 against a hand-set floor of 0.40).

``slider_bridge._widen_specs_to_cover_camps`` enforces the
``range ⊇ camp envelope`` invariant at import — the slider range is the
*union* of the deliberate exploration window and the camp envelope, so it
is only ever widened, never narrowed. This test pins that invariant so a
future camp/slider edit cannot silently reintroduce the crash.
"""

from enesys.ui.slider_bridge import LAGER_OPTIONS, SLIDER_SPEC, get_camp_defaults


def test_every_camp_default_within_slider_range():
    violations: list[str] = []
    for camp, *_labels in LAGER_OPTIONS:
        defaults = get_camp_defaults(camp)
        for key, spec in SLIDER_SPEC.items():
            if key not in defaults:
                continue
            value = defaults[key]
            if not (spec.lo <= value <= spec.hi):
                violations.append(f"{camp}.{key} = {value} not in [{spec.lo}, {spec.hi}]")
    assert not violations, "Camp defaults outside their slider range:\n" + "\n".join(violations)
