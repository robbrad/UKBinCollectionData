# Manual Tag Fix for Version 0.155.0

Since the tag wasn't pushed, you need to manually create and push it to trigger the release.

## Steps:

1. **Pull the latest changes:**
   ```bash
   git checkout master
   git pull
   ```

2. **Create the annotated tag:**
   ```bash
   git tag -a 0.155.0 -m "Release 0.155.0"
   ```

3. **Push the tag:**
   ```bash
   git push origin 0.155.0
   ```

4. **Verify:**
   - Check tags: https://github.com/robbrad/UKBinCollectionData/tags
   - Watch the release workflow: https://github.com/robbrad/UKBinCollectionData/actions

## What Was Fixed

1. **bump.yml** - Changed from `--follow-tags` to separate push commands
2. **pyproject.toml** - Added `annotated_tag = true` to Commitizen config

## Future Releases

The next merge will automatically:
1. Create annotated tag
2. Push commit and tag separately
3. Trigger release workflow
4. Publish to PyPI

No manual intervention needed!
