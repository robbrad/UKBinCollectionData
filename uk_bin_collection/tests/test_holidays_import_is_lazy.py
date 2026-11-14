"""A broken `holidays` package must only affect the one scraper that uses it (#2335).

Every scraper imports `common`, so an import-time failure there takes the whole
integration down. Run in a subprocess so the deliberately broken package can't leak
into other tests.
"""

import subprocess
import sys
import textwrap

BROKEN_HOLIDAYS = (
    "raise ModuleNotFoundError(\"No module named 'holidays.calendars.hebrew'\")\n"
)

CHECK = textwrap.dedent("""
    import datetime
    from uk_bin_collection.uk_bin_collection import common   # must not need holidays
    from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp
    print("common imports without holidays")
    try:
        common.is_holiday(datetime.datetime(2026, 12, 25))
    except ModuleNotFoundError as exc:
        print("is_holiday fails with:", exc)
    """)


def test_common_imports_even_when_the_holidays_package_is_broken(tmp_path):
    package = tmp_path / "holidays"
    package.mkdir()
    (package / "__init__.py").write_text(BROKEN_HOLIDAYS)

    result = subprocess.run(
        [sys.executable, "-c", CHECK],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(tmp_path), "PATH": ""},
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "common imports without holidays" in result.stdout
    assert "No module named 'holidays.calendars.hebrew'" in result.stdout
