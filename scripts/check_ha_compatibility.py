#!/usr/bin/env python3
"""
Home Assistant Compatibility Checker for UK Bin Collection Component

This script checks if the custom component is compatible with different
Home Assistant versions by testing imports and basic functionality.
"""

import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple


def check_manifest() -> Tuple[bool, str]:
    """Check if manifest.json is valid."""
    try:
        manifest_path = Path("custom_components/uk_bin_collection/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_fields = ["domain", "name", "version", "requirements"]
        missing = [field for field in required_fields if field not in manifest]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        return True, f"Version {manifest['version']}"
    except Exception as e:
        return False, f"Manifest error: {e}"


def check_component_imports() -> Tuple[bool, str]:
    """Check if component modules can be imported."""
    try:
        sys.path.insert(0, "custom_components")
        
        modules = [
            "uk_bin_collection",
            "uk_bin_collection.const",
            "uk_bin_collection.config_flow",
            "uk_bin_collection.sensor",
            "uk_bin_collection.calendar"
        ]
        
        for module in modules:
            importlib.import_module(module)
        
        return True, "All modules imported successfully"
    except Exception as e:
        return False, f"Import error: {e}"


def check_homeassistant_version() -> Tuple[bool, str]:
    """Check Home Assistant version."""
    try:
        import homeassistant
        version = homeassistant.__version__
        return True, f"Home Assistant {version}"
    except ImportError:
        return False, "Home Assistant not installed"
    except Exception as e:
        return False, f"Version check error: {e}"


def check_dependencies() -> Tuple[bool, str]:
    """Check if required dependencies are available."""
    try:
        import uk_bin_collection
        return True, "UK Bin Collection package available"
    except ImportError:
        return False, "UK Bin Collection package not installed"
    except Exception as e:
        return False, f"Dependency error: {e}"


def run_compatibility_check() -> Dict[str, Tuple[bool, str]]:
    """Run all compatibility checks."""
    checks = {
        "Manifest": check_manifest(),
        "Component Imports": check_component_imports(),
        "Home Assistant": check_homeassistant_version(),
        "Dependencies": check_dependencies(),
    }
    return checks


def main():
    """Main function."""
    print("🔍 UK Bin Collection - Home Assistant Compatibility Check")
    print("=" * 60)
    
    checks = run_compatibility_check()
    all_passed = True
    
    for check_name, (passed, message) in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {check_name}: {message}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 All compatibility checks passed!")
        print("The component should work with your Home Assistant installation.")
        sys.exit(0)
    else:
        print("⚠️  Some compatibility checks failed.")
        print("Please review the errors above before using the component.")
        sys.exit(1)


if __name__ == "__main__":
    main()