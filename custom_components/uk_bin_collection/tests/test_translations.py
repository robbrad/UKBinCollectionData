"""Regression tests for the config-flow translation strings.

These guard against the `manual_refresh_only` label inversion (issue #2193):
the field stores "manual refresh only" semantics, but the UI used to label it
"Automatically refresh the sensor" — the exact inverse — so ticking the box
silently disabled automatic refresh.

Dependency-free on purpose: json + pathlib only.
"""

import json
from pathlib import Path

# custom_components/uk_bin_collection/
INTEGRATION_DIR = Path(__file__).resolve().parent.parent
STRINGS_JSON = INTEGRATION_DIR / "strings.json"
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"

KEY = "manual_refresh_only"
OLD_INVERTED_LABEL = "Automatically refresh the sensor"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _all_translation_files() -> list[Path]:
    return sorted(TRANSLATIONS_DIR.glob("*.json"))


def _steps_with_key(data: dict) -> dict:
    """Return {step_name: label} for every config.step.*.data carrying KEY."""
    found = {}
    steps = data.get("config", {}).get("step", {})
    for step_name, step in steps.items():
        step_data = step.get("data", {})
        if KEY in step_data:
            found[step_name] = step_data[KEY]
    return found


def test_all_json_files_are_valid():
    """Every strings/translation file must parse as JSON."""
    _load(STRINGS_JSON)
    for path in _all_translation_files():
        _load(path)


def test_manual_refresh_label_not_inverted():
    """No label may claim the field enables automatic refresh."""
    files = [STRINGS_JSON, *_all_translation_files()]
    for path in files:
        labels = _steps_with_key(_load(path))
        assert labels, f"{path.name}: expected at least one '{KEY}' label"
        for step_name, label in labels.items():
            where = f"{path.name} :: config.step.{step_name}.data.{KEY}"

            # The exact old inverted English string must be gone everywhere.
            assert label != OLD_INVERTED_LABEL, (
                f"{where}: still uses the inverted label {OLD_INVERTED_LABEL!r}"
            )

            # If the label mentions "automatic(ally)", it must be a negation
            # (e.g. "disable automatic updates"), never a promise to refresh.
            lowered = label.lower()
            if "automatic" in lowered:
                assert "manual" in lowered or "disable" in lowered, (
                    f"{where}: label {label!r} mentions 'automatic' without a "
                    "negating 'manual'/'disable' — likely still inverted"
                )


def test_strings_and_en_translation_stay_in_sync():
    """strings.json and en.json must carry KEY in the same steps."""
    strings_steps = set(_steps_with_key(_load(STRINGS_JSON)))
    en_steps = set(_steps_with_key(_load(TRANSLATIONS_DIR / "en.json")))
    assert strings_steps == en_steps, (
        f"strings.json steps {sorted(strings_steps)} != "
        f"en.json steps {sorted(en_steps)}"
    )
    # Guard against the key silently disappearing from both.
    assert strings_steps, "manual_refresh_only missing from strings.json steps"
