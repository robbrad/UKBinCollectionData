# Home Assistant Compatibility

This document outlines the Home Assistant compatibility testing for the UK Bin Collection custom component.

## Supported Versions

The UK Bin Collection custom component is tested against the following Home Assistant versions:

- **Minimum supported**: Home Assistant 2023.10.0
- **Recommended**: Latest stable release
- **Development**: Latest dev builds (may have issues)

## Automated Testing

### GitHub Workflows

1. **Home Assistant Compatibility Test** (`.github/workflows/ha_compatibility_test.yml`)
   - Runs on every push to master/main
   - Tests against multiple HA versions
   - Validates component imports and manifest
   - Runs weekly to catch breaking changes

2. **HACS Validation** (`.github/workflows/hacs_validation.yml`)
   - Includes HassFest validation
   - HACS action validation
   - Quick compatibility check

### Manual Testing

Run the compatibility checker locally:

```bash
# From the project root directory
python scripts/check_ha_compatibility.py
```

This script will:
- ✅ Validate manifest.json structure
- ✅ Test component module imports
- ✅ Check Home Assistant version
- ✅ Verify dependencies are installed

## Compatibility Matrix

| Home Assistant Version | Status | Notes |
|------------------------|--------|-------|
| 2023.10.x | ✅ Supported | Minimum version |
| 2023.12.x | ✅ Supported | Stable |
| 2024.1.x  | ✅ Supported | Stable |
| 2024.3.x  | ✅ Supported | Stable |
| 2024.6.x  | ✅ Supported | Stable |
| 2024.9.x  | ✅ Supported | Stable |
| 2024.12.x | ✅ Supported | Latest stable |
| dev       | ⚠️ Testing | May have breaking changes |

## Breaking Changes

### Home Assistant 2023.10.0
- Minimum Python version: 3.12
- Updated async patterns required

### Future Considerations
- Monitor HA core API changes
- Update component when deprecated features are removed
- Test against beta releases before stable release

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure Home Assistant is properly installed
   - Check Python version compatibility (≥3.12)
   - Verify uk-bin-collection package is installed

2. **Manifest Validation Failures**
   - Check manifest.json syntax
   - Ensure all required fields are present
   - Verify version numbers match

3. **Component Load Failures**
   - Check Home Assistant logs
   - Verify component files are in correct location
   - Ensure dependencies are satisfied

### Getting Help

If you encounter compatibility issues:

1. Check the [GitHub Issues](https://github.com/robbrad/UKBinCollectionData/issues)
2. Run the compatibility checker: `python scripts/check_ha_compatibility.py`
3. Post in the [Home Assistant Community Thread](https://community.home-assistant.io/t/bin-waste-collection/55451)
4. Create a new issue with:
   - Home Assistant version
   - Component version
   - Error logs
   - Compatibility check output

## For Developers

### Adding New HA Version Tests

1. Update `.github/workflows/ha_compatibility_test.yml`
2. Add new version to the matrix
3. Test locally first: `python scripts/check_ha_compatibility.py`
4. Update compatibility matrix in this document

### Testing Locally

```bash
# Install specific HA version
pip install homeassistant==2024.12.0

# Install component in development mode
pip install -e .

# Run compatibility check
python scripts/check_ha_compatibility.py

# Run component tests
python -m pytest custom_components/uk_bin_collection/tests/
```