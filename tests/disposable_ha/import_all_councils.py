"""Import every shipped council module without performing network activity."""

from __future__ import annotations

import json

from uk_bin_collection.uk_bin_collection.collect_data import (
    import_council_module,
    registered_council_modules,
)


def main() -> None:
    failures: dict[str, str] = {}
    modules = sorted(registered_council_modules())
    for module_name in modules:
        try:
            import_council_module(module_name)
        except Exception as exc:  # Report the complete deterministic import inventory.
            missing_name = getattr(exc, "name", None)
            failures[module_name] = (
                f"{type(exc).__name__}:{missing_name}"
                if missing_name
                else type(exc).__name__
            )

    report = {
        "registered_council_count": len(modules),
        "imported_council_count": len(modules) - len(failures),
        "failure_count": len(failures),
        "failures": failures,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
