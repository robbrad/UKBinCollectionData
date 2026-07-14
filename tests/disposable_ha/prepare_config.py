"""Create a fresh, synthetic Home Assistant config for one offline test mode."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

CONFIG = Path("/config")
COMPONENT_SOURCE = Path("/workspace/custom_components/uk_bin_collection")


def _entry(entry_id: str, title: str, data: dict, *, version: int = 4) -> dict:
    return {
        "entry_id": entry_id,
        "version": version,
        "minor_version": 1,
        "domain": "uk_bin_collection",
        "title": title,
        "data": data,
        "options": {},
        "pref_disable_new_entities": False,
        "pref_disable_polling": False,
        "source": "user",
        "unique_id": None,
        "disabled_by": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("success", "collision", "migration"), required=True
    )
    args = parser.parse_args()

    if any(CONFIG.iterdir()):
        raise RuntimeError("Refusing to populate a non-empty disposable config volume")

    component_target = CONFIG / "custom_components" / "uk_bin_collection"
    component_target.parent.mkdir(parents=True)
    shutil.copytree(COMPONENT_SOURCE, component_target)
    storage = CONFIG / ".storage"
    storage.mkdir(mode=0o700)

    common = {
        "manual_refresh_only": True,
        "update_interval": 12,
        "timeout": 75,
        "icon_color_mapping": "{}",
    }
    if args.mode == "success":
        entries = [
            _entry(
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "Offline South Kesteven",
                {
                    **common,
                    "name": "Offline South Kesteven",
                    "council": "SouthKestevenFixtureCouncil",
                    "url": "http://127.0.0.1:8081/binday",
                    "postcode": "ZZ99 9ZZ",
                    "number": "Codex Test House",
                    "web_driver": "http://127.0.0.1:4444",
                    "headless": True,
                    "skip_get_url": True,
                    "user_agent": "Mozilla/5.0 UKBCD-Disposable-Fixture",
                },
            )
        ]
    elif args.mode == "collision":
        entries = [
            _entry(
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "Offline non-Selenium control",
                {
                    **common,
                    "name": "Offline non-Selenium control",
                    "council": "FixtureCouncil",
                    "url": "http://127.0.0.1:8081/static",
                    "skip_get_url": True,
                },
            ),
            _entry(
                "cccccccccccccccccccccccccccccccc",
                "Offline dependency collision",
                {
                    **common,
                    "name": "Offline dependency collision",
                    "council": "SouthKestevenFixtureCouncil",
                    "url": "http://127.0.0.1:8081/binday",
                    "postcode": "ZZ99 9ZZ",
                    "number": "Codex Test House",
                    "web_driver": "http://127.0.0.1:4444",
                    "headless": True,
                    "skip_get_url": True,
                },
            ),
        ]
        poison = CONFIG / "websocket"
        poison.mkdir()
        (poison / "__init__.py").write_text(
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ.get('UKBCD_TEST_EVIDENCE_DIR', '/evidence'))"
            ".joinpath('ha_poison_executed').write_text('executed', encoding='utf-8')\n"
            "from ..const import DOMAIN\n",
            encoding="utf-8",
        )
    else:
        # These entries deliberately exercise every historical starting version in
        # an actual HA storage file.  FixtureCouncil never performs network I/O,
        # and every value is synthetic or loopback-only.
        migration_common = {
            "council": "FixtureCouncil",
            "url": "http://127.0.0.1:8081/static",
            "timeout": 75,
            "icon_color_mapping": "{}",
        }
        entries = [
            _entry(
                "ddddddddddddddddddddddddddddddd1",
                "Offline migration v1",
                {
                    **migration_common,
                    "name": "Offline migration v1",
                    "house_number": "Synthetic Address V1",
                    "selenium_url": " http://127.0.0.1:4444/ ",
                    "skip_get_url": "true",
                },
                version=1,
            ),
            _entry(
                "ddddddddddddddddddddddddddddddd2",
                "Offline migration v2",
                {
                    **migration_common,
                    "name": "Offline migration v2",
                    "update_interval": 6,
                    "paon": "Synthetic Address V2",
                    "webdriver": " http://127.0.0.1:4444/wd/hub/ ",
                    "headless": "false",
                    "local_browser": "yes",
                    "skip_get_url": "on",
                },
                version=2,
            ),
            _entry(
                "ddddddddddddddddddddddddddddddd3",
                "Offline migration v3",
                {
                    **migration_common,
                    "name": "Offline migration v3",
                    "update_interval": None,
                    "manual_refresh_only": "true",
                    "number": "Synthetic Address V3",
                    "house_number": "Ignored legacy house value",
                    "paon": "Ignored legacy PAON value",
                    "web_driver": " http://127.0.0.1:4444/ ",
                    "selenium_url": "http://127.0.0.1:5555/",
                    "webdriver": "http://127.0.0.1:6666/",
                    "headless": True,
                    "local_browser": "0",
                    "skip_get_url": "1",
                },
                version=3,
            ),
        ]

    store = {
        "version": 1,
        "minor_version": 1,
        "key": "core.config_entries",
        "data": {"entries": entries},
    }
    (storage / "core.config_entries").write_text(
        json.dumps(store, indent=2, sort_keys=True), encoding="utf-8"
    )
    (CONFIG / "configuration.yaml").write_text(
        """homeassistant:
  name: UKBCD Offline Test
  latitude: 0
  longitude: 0
  elevation: 0
  unit_system: metric
  time_zone: Europe/London
logger:
  default: info
  logs:
    custom_components.uk_bin_collection: debug
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
